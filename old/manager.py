class ibridges():
    """
    Implements further policies and specific behaviour on the irodsConnector.
    """

    def __init__(self, ibridges_conf: utils.path.LocalPath, 
                 irods_conf: utils.path.LocalPath):
        """
        Read in configuration and make parameters accessible, 
        Read in irods_conf as dictionary
        """

    def __del__(self):
        """
        Cleanup irods connection and itself
        """
    
    @property
    def ibridges_config(self):
        """
        Return current configuration as dictionary
        """

    @property
    def davrods(self):
        """
        Return davrods server from configuration file
        """
    
    @davrods.setter
    def davrods(self, davrods_server: str):
        """
        Overwrite current davrods in configuration dictionary
        """

    @property
    def check_free_space(self):
        """
        Return check_free_space from configration file
        """

    @check_free_space.setter
    def check_free_space(self, check: bool):
        """
        Overwrite current check_free_space in configuration dictionary
        """

    @property
    def force_transfers(self):
        """
        Return force_transfers from configration file
        """

    @force_transfers.setter
    def force_transfers(self, force: bool):
        """
        Overwrite current force_transfers in configuration dictionary
        """

    @property
    def irods_conf(self):
        """
        Returns irods_conf dictionary 
        """

    @irods_conf.setter
    def irods_conf(self, irods_conf_path: utils.path.LocalPath):
        """
        Loads a new irods environment, deletes a current existing irods connection.
        """

    def connect(self):
        """
        Creates an irodsConnector from the irods_conf, ensures that the connection is active
        """
        # read cached password
        # try to instantiate irodsConnector from irods_env_file and cached password
        # if fail on Authentication or no cached passowrd, ask for password and instantiate
    
    def disconnect(self):
        """
        Diconnects (deletes) current irods session
        """
        # remove irodsConnector.session and make invalid


    def authenticate(self, password):
        cached_password = get_cached_password()

        # if password equals cached password --> login with irods env file only
        if cached_password == password:
            sess = Session(irods_conf_path)
            result = sess.connect()
        # if password differs from cached password --> login with env + password
        else:
            sess = Session(irods_conf, password=password)
            result = sess.connect()
        return result


    def get_cached_password(self) -> str:
        """Scrape the cached password from the iRODS authentication file,
        if it exists.

        Returns
        -------
        str
            Cached password or null string.

        """
        irods_auth_file = os.environ.get('IRODS_AUTHENTICATION_FILE', None)
        if irods_auth_file is None:
            irods_auth_file = context.irods_env_file.path.parent.joinpath(".irodsA")
        if utils.path.LocalPath(irods_auth_file).exists():
            with open(irods_auth_file, encoding='utf-8') as authfd:
                return irods.password_obfuscation.decode(authfd.read())
        return ''

    def write_password(self):
        """Store the password in the iRODS
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

    def diff_irods_local(self, local_paths: list, irods_paths: list) -> list:
        """Given a list of file paths and object paths, return those with a different checksum,
        or are not present locally
        """

    def diff_local_irods(self, irods_paths: list, local_paths: list) -> list:
        """ given a list of objects and files, return those with a different checksum, or are not
        present on iRODS
        """

    def writeable_resources(self, size: int = 0):
        """Return only writeable resources.
        size: Required space in bytes
        """
        # Get all root resources
        # If ibridges config is set to force_transfers = False, only return root resources
        # which have free_space > size

    def search_data(self, key_vals: dict = None) -> list:
        """Given a dictionary with metadata attribute names as keys and
        associated values, query for collections and data objects that
        fullfill the criteria.
        """

### link all functions from irodsConnector here

