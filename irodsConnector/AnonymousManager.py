"""IrodsConnector for anonymous users
"""
import hashlib
import logging
import os
import uuid
from base64 import b64decode
from shutil import disk_usage
from subprocess import Popen, PIPE
import irods.collection
from irods.exception import CAT_SQL_ERR
from irods.session import iRODSSession
from irods.ticket import Ticket
from irodsConnector.Icommands import IrodsConnectorIcommands
import irodsConnector.keywords as kw

import utils

context = utils.context.Context()


# TODO
# When the manager is done, a lot of functions can be rewriten and mapped in the same way.
# The result is an manager class and an annonomous manager class
class IrodsConnectorAnonymous:
    """Anonomous irods user

    """
    def __init__(self, host, ticket, path):
        """iRODS anonymous login.

        Parameters
        ----------
            server: iRODS server
            ticket: string
            path: iRODS path the ticket grants access to

        """
        self.__name__ = "IrodsConnectorAnonymous"
        if path.endswith('/'):
            path = path[:-1]
        if not path.startswith("/"):
            raise Exception("Not a valid iRODS path.")

        self.temp_env = None
        self.temp_irods_a = None

        zone = path.split('/')[1]
        self.session = iRODSSession(user='anonymous',
                                    password='',
                                    zone=zone,
                                    port=1247,
                                    host=host)
        self.token = ticket
        self.path = path

        if IrodsConnectorIcommands.icommands():
            utils.utils.ensure_dir(os.path.expanduser('~'+os.sep+'.irods'))
            # move previous iRODS sessions to tmp file (envFile and .irodsA file)
            self._move_prev_session_configs(False)
            env = {"irods_host": self.session.host,
                   "irods_port": 1247,
                   "irods_user_name": "anonymous",
                   "irods_zone_name": self.session.zone}
            context.irods.update(env)
            context.save_irods()
            logging.info('Anonymous Login: '+self.session.host+', '+self.session.zone)
            pros = Popen(['iinit'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            _, err_login = pros.communicate()
            if err_login != b'':
                logging.info('AUTHENTICATION ERROR: Anonymous login failed.')
                self.icommands = False

    def close_session(self):
        """Clean up after anonomous irods session

        """
        self._move_prev_session_configs(True)

    def _move_prev_session_configs(self, restore: bool):
        """Move preivious irods session to prevent overwrites

        Parameters
        ----------
        restore : bool
            Restore environment after anonomous session or prepare for one
        """
        if restore:
            if self.temp_env:
                os.rename(self.temp_env, os.path.expanduser('~'+os.sep+'.irods'+os.sep+'irods_environment.json'))
            if self.temp_irods_a:
                os.rename(self.temp_irods_a, os.path.expanduser('~'+os.sep+'.irods'+os.sep+'.irodsA'))
        else:
            uid = str(uuid.uuid1())
            env_path = os.path.expanduser('~'+os.sep+'.irods'+os.sep+'irods_environment.json')
            irodsa_path = os.path.expanduser('~'+os.sep+'.irods'+os.sep+'.irodsA')
            if os.path.exists(env_path):
                os.rename(env_path, env_path+uid)
                self.temp_env = env_path+uid
            if os.path.exists(irodsa_path):
                os.rename(irodsa_path, irodsa_path+uid)
                self.temp_irods_a = irodsa_path+uid

    def get_data(self) -> irods.collection.Collection:
        """Get the irods collection shared through the ticket

        Returns
        -------
        irods collection
        """
        ticket = Ticket(self.session, self.token)
        ticket.supply()
        item = self.session.collections.get(self.path)
        return item

    def get_resource(self, resource):
        '''Instantiate an iRODS resource.

        Parameters
        ----------
        resource : str
            Name of the iRODS resource.

        Returns
        -------
        iRODSResource
            Instance of the resource with `resource`.
        Raises:
            irods.exception.ResourceDoesNotExist
        '''
        return self.session.resources.get(resource)

    def download_icommands(self, source, destination):
        '''Icommands download

        Parameters
        ----------
        source
        '''
        if isinstance(source, irods.data_object.iRODSDataObject):
            # -f overwrite, -K control checksum, -r recursive (collections)
            cmd = 'iget -Kft ' + self.token + ' ' + \
                    source.path+' '+destination+os.sep+os.path.basename(source.path)
        elif self.session.collections.exists(source.path):
            cmd = 'iget -Kfrt ' + self.token + ' ' + \
                    source.path+' '+destination+os.sep+os.path.basename(source.path)
        else:
            raise FileNotFoundError("IRODS download: not a valid source.")

        logging.info("IRODS DOWNLOAD: %s", cmd)
        pros = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = pros.communicate()
        logging.info('IRODS DOWNLOAD INFO: out: %s\nerr: %s', str(out), str(err))

    def download(self, source, destination, diffs):
        '''Download object or collection.
        Since the data_object.get function does not work for anonymous sessions, we need to stream

        Parameters
        ----------
        source : iRODSCollection, iRODSDataObject
            The iRODS collection or data object from where the data will be downloaded.
        destination : str
            Absolute path to local folder/directory.
        diffs : tuple
            Output of diff functions.

        '''
        (difs, _, onlyirods, _) = diffs
        if isinstance(source, irods.data_object.iRODSDataObject) and len(difs+onlyirods) > 0:
            try:
                logging.info("IRODS DOWNLOADING object: %s to %s", source.path, destination)
                self.__get(source, os.path.join(destination, source.name))
                return
            except Exception:
                logging.info("DOWNLOAD ERROR: %s --> %s", source.path, destination, exc_info=True)
                raise

        try:  # collections/folders
            subdir = os.path.join(destination, source.name)
            logging.info("IRODS DOWNLOAD started:")
            for diff in difs:
                # upload files to distinct data objects
                logging.info("REPLACE: %s with %s", diff[1], diff[0])
                _subcoll = self.session.collections.get(os.path.dirname(diff[0]))
                obj = [o for o in _subcoll.data_objects if o.path == diff[0]][0]
                self.__get(obj, diff[1])
                # self.session.data_objects.get(d[0], local_path=d[1], **options)

            for oi in onlyirods:  # can contain files and folders
                # Create subcollections and upload
                source_path = source.path + "/" + oi
                loc_o = oi.replace("/", os.sep)
                dest_path = os.path.join(subdir, loc_o)
                if not os.path.isdir(os.path.dirname(dest_path)):
                    os.makedirs(os.path.dirname(dest_path))
                logging.info('INFO: Downloading '+source_path+" to "+dest_path)
                _subcoll = self.session.collections.get(os.path.dirname(source_path))
                obj = [o for o in _subcoll.data_objects if o.path == source_path][0]
                self.__get(obj, dest_path)
                # self.session.data_objects.get(source_path, local_path=dest_path, **options)
        except Exception:
            logging.info('DOWNLOAD ERROR', exc_info=True)
            raise

    def download_data(self, source: None, destination: str, size: int, buff: int = kw.BUFF_SIZE,
                      force: bool = False, diffs: tuple = None):
        '''Download object or collection.
        Since the data_object.get function does not work for anonymous sessions, we need to stream

        Parameters
        ----------
        source : iRODSCollection, iRODSDataObject
            The iRODS collection or data object from where the data will be downloaded.
        destination : str
            Absolute path to local folder/directory.
        size : int
            Size of data to be uploaded in bytes.
        buff : int
            Buffer size on local storage that should remain after
            download in bytes.
        force : bool
            Ignore storage capacity on the storage system of `destination`.
        diffs : tuple
            Output of diff functions.

        '''
        logging.info('iRODS DOWNLOAD: %s --> %s', str(source), destination)
        # options = {kw.FORCE_FLAG_KW: '', kw.REG_CHKSUM_KW: ''}

        if destination.endswith(os.sep):
            destination = destination[:len(destination)-1]
        if not os.path.isdir(destination):
            logging.info('DOWNLOAD ERROR: destination path does not exist or is not directory', exc_info=True)
            raise FileNotFoundError(
                "ERROR iRODS download: destination path does not exist or is not directory")
        if not os.access(destination, os.W_OK):
            logging.info('DOWNLOAD ERROR: No rights to write to destination.', exc_info=True)
            raise PermissionError("ERROR iRODS download: No rights to write to destination.")

        if diffs is None:  # Only download if not present or diffserence in files
            if self.session.collections.exists(source.path):
                subdir = os.path.join(destination, source.name)
                if not os.path.isdir(os.path.join(destination, source.name)):
                    os.mkdir(os.path.join(destination, source.name))
                diffs = self.diffsIrodsLocalfs(source, subdir, scope="checksum")
            elif isinstance(source, irods.data_object.iRODSDataObject):
                _subcoll = self.session.collections.get(os.path.dirname(source.path))
                val_objs = [o for o in _subcoll.data_objects if o.path == source.path]
                if len(val_objs) > 0:
                    diffs = self.diffs_obj_file(source.path,
                                                os.path.join(destination,
                                                             os.path.basename(source.path)),
                                                scope="checksum")
            else:
                raise FileNotFoundError("ERROR iRODS upload: not a valid source path")

        if not force:  # Check space on destination
            try:
                space = disk_usage(destination).free
                if int(size) > (int(space)-buff):
                    logging.info('DOWNLOAD ERROR: Not enough space on disk.', exc_info=True)
                    raise ValueError('ERROR iRODS download: Not enough space on disk.')
                if buff < 0:
                    logging.info('DOWNLOAD ERROR: Negative disk buffer.', exc_info=True)
                    raise BufferError('ERROR iRODS download: Negative disk buffer.')
            except Exception as error:
                logging.info('DOWNLOAD ERROR', exc_info=True)
                raise error

        if self.icommands:
            self.download_icommands(source, destination)
        else:
            self.download(source, destination, diffs)

    def __get(self, obj, filename):
        """ Download a dataobject
        Workaround for bug in the irods_data_objects get function:
        https://github.com/irods/python-irodsclient/issues/294

        Parameters
        ----------
        obj: irods dataobject
            irods collection or dataobject
        filename: str
            Local file
        """
        options = {kw.FORCE_FLAG_KW: '', kw.REG_CHKSUM_KW: '', kw.TICKET_KW: self.token}
        try:
            self.session.data_objects.get(obj.path, local_path=filename, **options)
        except CAT_SQL_ERR:
            pass
        except Exception as exp:
            raise exp

    def diffs_obj_file(self, objpath: str, dirpath: str, scope: str = "size") -> tuple:
        """
        Compares and iRODS object to a file system file.
        There is no session.data_objects.exists or .get for anonymous users
        Implements workaround to: https://github.com/irods/python-irodsclient/issues/294

        Parameters
        ----------
        objpath: str
            irods collection or dataobject
        dirpath: str
            Local file or directory
        scope: str
            Syncing scope can be 'size' or 'checksum'
        Returns
        ----------
        tuple
            ([diff], [only_irods], [only_fs], [same])
        """
        if os.path.isdir(dirpath) and not os.path.isfile(dirpath):
            raise IsADirectoryError("IRODS FS diffs: file is a directory.")
        if self.session.collections.exists(objpath):
            raise IsADirectoryError("IRODS FS diffs: object exists already as collection. "+objpath)

        coll = self.session.collections.get(os.path.dirname(objpath))
        obj = [o for o in coll.data_objects if o.path == objpath][0]
        if not os.path.isfile(dirpath) and obj:
            return ([], [], [obj.path], [])

        elif not obj and os.path.isfile(dirpath):
            return ([], [dirpath], [], [])

        # both, file and object exist
        if scope == "size":
            obj_size = obj.size
            f_size = os.path.getsize(dirpath)
            if obj_size != f_size:
                return ([(objpath, dirpath)], [], [], [])
            else:
                return ([], [], [], [(objpath, dirpath)])
        elif scope == "checksum":
            obj_check = obj.checksum
            if obj_check is None:
                logging.info('No checksum available: %s', obj.path)
                return ([(objpath, dirpath)], [], [], [])
            if obj_check.startswith("sha2"):
                sha2_obj = b64decode(obj_check.split('sha2:')[1])
                with open(dirpath, "rb") as file:
                    stream = file.read()
                    sha2 = hashlib.sha256(stream).digest()
                if sha2_obj != sha2:
                    return ([(objpath, dirpath)], [], [], [])
                else:
                    return ([], [], [], [(objpath, dirpath)])
            elif obj_check:
                # md5
                with open(dirpath, "rb") as file:
                    stream = file.read()
                    md5 = hashlib.md5(stream).hexdigest()
                if obj_check != md5:
                    return ([(objpath, dirpath)], [], [], [])
                else:
                    return ([], [], [], [(objpath, dirpath)])
