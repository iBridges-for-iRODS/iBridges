""" session operations
"""
import logging
import os
import ssl

import irods.connection
import irods.exception
import irods.password_obfuscation
import irods.session

from . import keywords as kw
import utils


class Session(object):
    """Irods session operations """
    _session = None
    context = utils.context.Context()

    def __init__(self, password=''):
        """ iRODS authentication with Python client.

        Parameters
        ----------
        password : str
            Plain text password.

        The 'password' property can autoload from its cache, but can be
        overridden by `password` argument.  The iRODS authentication
        file is expected in the standard location (~/.irods/.irodsA) or
        to be specified in the local environment with the
        IRODS_AUTHENTICATION_FILE variable.

        """
        self._password = password

    def __del__(self):
        del self.session

    @property
    def conf(self) -> dict:
        """iBridges configuration dictionary.

        Returns
        -------
        dict
            Configuration from JSON serialized string.

        """
        if self.context.ibridges_configuration:
            return self.context.ibridges_configuration.config
        return {}

    @property
    def davrods(self) -> str:
        """DavRODS server URL.

        Returns
        -------
        str
            URL of the configured DavRODS server.

        """
        return self.conf.get('davrods_server', '')

    @property
    def default_resc(self) -> str:
        """Default resource name from iRODS environment.

        Returns
        -------
        str
            Resource name.

        """
        return self.ienv.get('irods_default_resource', '')

    @property
    def host(self) -> str:
        """Retrieve hostname of the iRODS server

        Returns
        -------
        str
            Hostname.

        """
        if self.session:
            return self.session.host
        return ''

    @property
    def ienv(self) -> dict:
        """iRODS environment dictionary.

        Returns
        -------
        dict
            Environment from JSON serialized string.
        """
        if self.context.irods_environment:
            return self.context.irods_environment.config
        return {}

    @property
    def port(self) -> str:
        """Retrieve port of the iRODS server

        Returns
        -------
        str
            Port.

        """
        if self.session:
            return str(self.session.port)
        return ''

    @property
    def username(self) -> str:
        """Retrieve username

        Returns
        -------
        str
            Username.

        """
        if self.session:
            return self.session.username
        return ''

    @property
    def server_version(self) -> tuple:
        """Retrieve version of the iRODS server

        Returns
        -------
        tuple
            Server version: (major, minor, patch).

        """
        if self.session:
            return self.session.server_version
        return ()

    @property
    def zone(self) -> str:
        """Retrieve the zone name

        Returns
        -------
        str
            Zone.

        """
        if self.session:
            return self.session.zone
        return ''

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
            irods_auth_file = os.environ.get(
                'IRODS_AUTHENTICATION_FILE', None)
            if irods_auth_file is None:
                irods_auth_file = utils.path.LocalPath(
                    '~/.irods/.irodsA').expanduser()
            if irods_auth_file.exists():
                with open(irods_auth_file, encoding='utf-8') as authfd:
                    self._password = irods.password_obfuscation.decode(
                        authfd.read())
        return self._password

    @password.setter
    def password(self, password: str):
        """iRODS password setter method.

        Pararmeters
        -----------
        password: str
            Unencrypted iRODS password.

        """
        self._password = password

    @password.deleter
    def password(self):
        """iRODS password deleter method.

        """
        self._password = ''

    @property
    def session(self) -> irods.session.iRODSSession:
        """iRODS session creation.

        Returns
        -------
        iRODSSession
            iRODS connection based on given environment and password.

        """
        if self._session is None:
            options = {
                'irods_env_file': str(self.context.irods_env_file),
            }
            if self.ienv is not None:
                options.update(self.ienv)
            given_pass = self.password
            del self.password
            # Accessing reset password property scrapes cached password.
            cached_pass = self.password
            del self.password
            if given_pass != cached_pass:
                options['password'] = given_pass
            self._session = self._get_irods_session(options)
            # If session exists, it is validated.
            if self._session:
                self._write_pam_password()
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

    @session.deleter
    def session(self):
        """Properly delete irods session.
        """
        if self._session is not None:
            self._session.cleanup()
            del self._session
            self._session = None

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
        irods_env_file = options.pop('irods_env_file')
        if 'password' not in options:
            try:
                print('AUTH FILE SESSION')
                session = irods.session.iRODSSession(
                    irods_env_file=irods_env_file)
                _ = session.server_version
                return session
            except Exception as error:
                print(f'{kw.RED}AUTH FILE LOGIN FAILED: {error!r}{kw.DEFAULT}')
                raise error
        else:
            password = options.pop('password')
            try:
                print('FULL ENVIRONMENT SESSION')
                session = irods.session.iRODSSession(password=password, **options)
                _ = session.server_version
                return session
            except irods.connection.PlainTextPAMPasswordError as ptppe:
                print(f'{kw.RED}SOMETHING WRONG WITH THE ENVIRONMENT JSON? {ptppe!r}{kw.DEFAULT}')
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
                    print('RETRY WITH DEFAULT SSL SETTINGS')
                    session = irods.session.iRODSSession(password=password, **options)
                    _ = session.server_version
                    return session
                except Exception as error:
                    print(f'{kw.RED}RETRY FAILED: {error!r}{kw.DEFAULT}')
                    raise error
            except Exception as autherror:
                logging.info('AUTHENTICATION ERROR')
                print(f'{kw.RED}AUTHENTICATION ERROR: {autherror!r}{kw.DEFAULT}')
                raise autherror

    def _write_pam_password(self):
        """Store the returned PAM/LDAP password in the iRODS
        authentication file in obfuscated form.

        """
        connection = self._session.pool.get_connection()
        pam_passwords = self._session.pam_pw_negotiated
        if len(pam_passwords):
            irods_auth_file = self._session.get_irods_password_file()
            with open(irods_auth_file, 'w', encoding='utf-8') as authfd:
                authfd.write(
                    irods.password_obfuscation.encode(pam_passwords[0]))
        else:
            logging.info('WARNING -- unable to cache obfuscated password locally')
        connection.release()
