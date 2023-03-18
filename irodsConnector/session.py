""" session operations
"""
from json import load
from os import environ
import logging
import ssl
import irods.exception
import irods.password_obfuscation
import irods.session
import irodsConnector.keywords as kw
from utils import utils


class Session(object):
    """Irods session operations """
    _irods_env_file = ''
    _ienv = {}
    _password = ''
    _session = None

    def __init__(self, irods_env_file='', password=''):
        """ iRODS authentication with Python client.

        Parameters
        ----------
        irods_env_file : str
            JSON document with iRODS connection parameters.
        password : str
            Plain text password.

        The 'ienv' and 'password' properties can autoload from their
        respective caches, but can be overridden by the `ienv` and
        `password` arguments, respectively.  The iRODS environment file
        is expected in the standard location
        (~/.irods/irods_environment.json) or to be specified in the
        local environment with the IRODS_ENVIRONMENT_FILE variable, and
        the iRODS authentication file is expected in the standard
        location (~/.irods/.irodsA) or to be specified in the local
        environment with the IRODS_AUTHENTICATION_FILE variable.
        """
        self._irods_env_file = irods_env_file
        if password:
            self._password = password

    @property
    def irods_env_file(self) -> str:
        """iRODS environment filename

        Returns
        -------
        str
            the path to the iRODS environment file.

        """
        return self._irods_env_file

    @property
    def ienv(self) -> dict:
        """iRODS environment dictionary.

        Returns
        -------
        dict
            iRODS environment dictionary obtained from its JSON file.

        """
        if not self._ienv:
            irods_env_file = utils.LocalPath(self._irods_env_file)
            if irods_env_file.is_file():
                with open(irods_env_file, encoding='utf-8') as envfd:
                    self._ienv = load(envfd)
        return self._ienv

    @property
    def davrods(self) -> str:
        """DavRODS server URL.

        Returns
        -------
        str
            URL of the configured DavRODS server.

        """
        # FIXME move iBridges parameters to iBridges configuration
        return self._ienv.get('davrods_server', None)

    @property
    def default_resc(self) -> str:
        """Default resource name from iRODS environment.

        Returns
        -------
        str
            Resource name.

        """
        return self._ienv.get('irods_default_resource', None)

    @property
    def get_host(self) -> str:
        """Retreive hostname of the iRODS server

        Returns
        -------
        str
            Hostname.

        """
        return self._session.host

    @property
    def get_port(self) -> str:
        """Retreive port of the iRODS server

        Returns
        -------
        str
            Port.

        """
        return self._session.port

    @property
    def get_username(self) -> str:
        """Retreive username

        Returns
        -------
        str
            Username.

        """
        return self._session.username

    @property
    def get_server_version(self) -> str:
        """Retreive version of the iRODS server

        Returns
        -------
        str
            Server version.

        """
        return self._session.server_version

    @property            
    def get_zone(self) -> str:
        """Retreive the zone name

        Returns
        -------
        str
            Zone.

        """
        return self._session.zone

    @property
    def password(self) -> str:
        """iRODS password.

        Returns
        -------
        str
            iRODS password pre-set or decoded from iRODS authentication
            file. Can be a PAM negotiated password.

        """
        if not self._password:
            irods_auth_file = environ.get(
                'IRODS_AUTHENTICATION_FILE', None)
            if irods_auth_file is None:
                irods_auth_file = utils.LocalPath(
                    '~/.irods/.irodsA').expanduser()
            if irods_auth_file.exists():
                with open(irods_auth_file, encoding='utf-8') as authfd:
                    self._password = irods.password_obfuscation.decode(
                        authfd.read())
        return self._password

    @password.setter
    def password(self, password):
        """iRODS password setter method.

        Pararmeters
        -----------
        password: str
            Unencrypted iRODS password.

        """
        if password:
            self._password = password

    @password.deleter
    def password(self):
        """iRODS password deleter method.

        """
        self._password = ''

    @property
    def session(self) -> irods.session.iRODSSession:
        """iRODS session.

        Returns
        -------
        iRODSSession
            iRODS connection based on given environment and password.

        """
        return self._session

    def cleanup(self):
        """ cleanup irods session.
        """
        return self._session.cleanup()

    def connect(self, application_name: str) -> irods.session.iRODSSession:
        """iRODS session creation.

        Pararmeters
        -----------
        application_name: str
            Name of the python application

        Returns
        -------
        iRODSSession
            iRODS connection based on given environment and password.

        """
        if self._session is None:
            options = {
                'irods_env_file': self._irods_env_file,
                'application_name': application_name,
            }
            if self.ienv is not None:
                options.update(self.ienv.copy())
            # Compare given password with potentially cached password.
            given_pass = self.password
            del self.password
            cached_pass = self.password
            if given_pass != cached_pass:
                options['password'] = given_pass
            self._session = self._get_irods_session(options)
            try:
                # Check for good authentication and cache PAM password
                if 'password' in options:
                    self._session.pool.get_connection()
                    self._write_pam_password()
            except (irods.exception.CAT_INVALID_AUTHENTICATION, KeyError) as error:
                raise error
            print('Welcome to iRODS:')
            print(f'iRODS Zone: {self._session.zone}')
            print(f'You are: {self._session.username}')
            print(f'Default resource: {self.default_resc}')
            print('You have access to: \n')
            home_path = f'/{self._session.zone}/home'
            if self._session.collections.exists(home_path):
                colls = self._session.collections.get(home_path).subcollections
                print('\n'.join([coll.path for coll in colls]))
            logging.info(
                'IRODS LOGIN SUCCESS: %s, %s, %s', self._session.username,
                self._session.zone, self._session.host)
            return self._session

    @staticmethod
    def _get_irods_session(options):
        """Run through different types of authentication methods and
        instantiate an iRODS session.

        Parameters
        ----------
        options : dict
            Initial iRODS settings for the session.

        Returns
        -------
        iRODSSession
            iRODS connection based on given environment and password.

        """
        if 'password' not in options:
            try:
                print('AUTH FILE SESSION')
                return irods.session.iRODSSession(
                    irods_env_file=options['irods_env_file'])
            except Exception as error:
                print(f'{kw.RED}AUTH FILE LOGIN FAILED: {error!r}{kw.DEFAULT}')
        else:
            try:
                print('FULL ENVIRONMENT SESSION')
                return irods.session.iRODSSession(**options)
            except irods.connection.PlainTextPAMPasswordError as ptppe:
                print(f'{kw.RED}ENVIRONMENT INCOMPLETE? {ptppe!r}{kw.DEFAULT}')
                try:
                    ssl_context = ssl.create_default_context(
                        purpose=ssl.Purpose.SERVER_AUTH,
                        cafile=None, capath=None, cadata=None)
                    ssl_settings = {
                        'client_server_negotiation':
                            'request_server_negotiation',
                        'client_server_policy': 'CS_NEG_REQUIRE',
                        'encryption_algorithm': 'AES-256-CBC',
                        'encryption_key_size': 32,
                        'encryption_num_hash_rounds': 16,
                        'encryption_salt_size': 8,
                        'ssl_context': ssl_context,
                    }
                    options.update(ssl_settings)
                    print('PARTIAL ENVIRONMENT SESSION')
                    return irods.session.iRODSSession(**options)
                except Exception as error:
                    print(f'{kw.RED}PARTIAL ENVIRONMENT LOGIN FAILED: {error!r}{kw.DEFAULT}')
                    raise error
            except Exception as autherror:
                logging.info('AUTHENTICATION ERROR', exc_info=True)
                print(f'{kw.RED}AUTHENTICATION ERROR: {autherror!r}{kw.DEFAULT}')
                raise autherror

    def _write_pam_password(self):
        """Store the returned PAM/LDAP password in the iRODS
        authentication file in obfuscated form.

        """
        pam_passwords = self._session.pam_pw_negotiated
        if len(pam_passwords):
            irods_auth_file = self._session.get_irods_password_file()
            with open(irods_auth_file, 'w', encoding='utf-8') as authfd:
                authfd.write(
                    irods.password_obfuscation.encode(pam_passwords[0]))
