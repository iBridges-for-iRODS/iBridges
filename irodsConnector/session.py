""" session operations
"""
import logging
import os

import irods.connection
import irods.exception
import irods.password_obfuscation
import irods.session

import utils


class Session(object):
    """Irods session operations """
    _irods_session = None
    ibridges_configuration = None
    irods_env_file = ''
    irods_environment = None

    def __init__(self, irods_env_file, password=''):
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
        self.irods_envFile = irods_env_file

    def __del__(self):
        del self.irods_session

    # Configuration properties
    #
    @property
    def conf(self) -> dict:
        """iBridges configuration dictionary.

        Returns
        -------
        dict
            Configuration from JSON serialized string.

        """
        logging.debug('getting: self.ibridges_configuration')
        if self.ibridges_configuration:
            return self.ibridges_configuration.config
        return {}

    @property
    def ienv(self) -> dict:
        """iRODS environment dictionary.

        Returns
        -------
        dict
            Environment from JSON serialized string.
        """
        logging.debug('getting: self.irods_environment')
        if self.irods_environment:
            return self.irods_environment.config
        return {}

    # Authentication workflow properties
    #
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
    def irods_session(self) -> irods.session.iRODSSession:
        """iRODS session creation.

        Returns
        -------
        iRODSSession
            iRODS connection based on the current environment and password.

        """
        if self.has_valid_irods_session():
            return self._irods_session

    @irods_session.deleter
    def irods_session(self):
        """Properly delete iRODS session.
        """
        if self._irods_session is not None:
            # In case the iRODS session is not fully there.
            try:
                self._irods_session.cleanup()
            except NameError:
                pass
            del self._irods_session
            self._irods_session = None

    # Authentication workflow methods
    #
    def has_irods_session(self) -> bool:
        """Check if an iRODS session has been assigned to its shadow
        variable.

        Returns
        -------
        bool
            Has a session been set?

        """
        return isinstance(self._irods_session, irods.session.iRODSSession)

    def has_valid_irods_session(self) -> bool:
        """Check if the iRODS session is valid.

        Returns
        -------
        bool
            Is the session valid?

        """
        return self.has_irods_session() and self._irods_session.server_version != ()

    def connect(self):
        """Establish an iRODS session.

        """
        if not self.irods_env_file:
            if 'last_ienv' in self.conf:
                logging.warning('"irods_env_file" not set.  Using "last_ienv" value.')
                irods_path = utils.path.LocalPath(utils.context.IRODS_DIR).expanduser()
                self.irods_env_file = irods_path.joinpath(self.conf['last_ienv'])
            else:
                logging.error('No iRODS session: "irods_env_file" not set!')
                return
        options = {
            'irods_env_file': str(self.irods_env_file),
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
        self._irods_session = self._get_irods_session(options)
        # If session exists, it is validated.
        if self._irods_session:
            if given_pass != cached_pass:
                self._write_pam_password()
            logging.info(
                'IRODS LOGIN SUCCESS: %s:%s', self._irods_session.host,
                self._irods_session.port)

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
                logging.info('AUTH FILE SESSION')
                session = irods.session.iRODSSession(
                    irods_env_file=irods_env_file)
                _ = session.server_version
                return session
            except TypeError as error:
                logging.error('AUTH FILE LOGIN FAILED')
                logging.error('Have you set the iRODS environment file correctly?')
                raise error
            except Exception as error:
                logging.error('AUTH FILE LOGIN FAILED: %r', error)
                raise error
        else:
            password = options.pop('password')
            try:
                logging.info('FULL ENVIRONMENT SESSION')
                session = irods.session.iRODSSession(password=password, **options)
                _ = session.server_version
                return session
            except Exception as error:
                logging.error('FULL ENVIRONMENT LOGIN FAILED: %r', error)
                raise error

    def _write_pam_password(self):
        """Store the returned PAM/LDAP password in the iRODS
        authentication file in obfuscated form.

        """
        connection = self._irods_session.pool.get_connection()
        pam_passwords = self._irods_session.pam_pw_negotiated
        if len(pam_passwords):
            irods_auth_file = self._irods_session.get_irods_password_file()
            with open(irods_auth_file, 'w', encoding='utf-8') as authfd:
                authfd.write(
                    irods.password_obfuscation.encode(pam_passwords[0]))
        else:
            logging.info('WARNING -- unable to cache obfuscated password locally')
        connection.release()

    # Introspection properties
    #
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
        """Retrieve hostname of the iRODS server.

        Returns
        -------
        str
            Hostname.

        """
        return self.ienv.get('irods_host', '')

    @property
    def port(self) -> str:
        """Retrieve port of the iRODS server.

        Returns
        -------
        str
            Port.

        """
        return str(self.ienv.get('irods_port', ''))

    @property
    def server_version(self) -> tuple:
        """Retrieve version of the iRODS server

        Returns
        -------
        tuple
            Server version: (major, minor, patch).

        """
        if self.has_irods_session():
            return self.irods_session.server_version
        return ()

    @property
    def username(self) -> str:
        """Retrieve username.

        Returns
        -------
        str
            Username.

        """
        return self.ienv.get('irods_user_name', '')

    @property
    def zone(self) -> str:
        """Retrieve the zone name.

        Returns
        -------
        str
            Zone.

        """
        return self.ienv.get('irods_zone_name', '')
