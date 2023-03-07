

class DataOperation(object):
    def ensure_coll(self, coll_name):
        """Optimally create a collection with `coll_name` if one does
        not exist.

        Parameters
        ----------
        coll_name : str
            Name of the collection to check/create.

        Returns
        -------
        iRODSCollection
            Existing or new iRODS collection.

        Raises:
            irods.exception.CAT_NO_ACCESS_PERMISSION

        """
        try:
            if self.session.collections.exists(coll_name):
                return self.session.collections.get(coll_name)
            return self.session.collections.create(coll_name)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
            logging.info('ENSURE COLLECTION', exc_info=True)
            raise cnap

    def get_dataobject(self, path):
        """Instantiate an iRODS data object.

        Parameters
        ----------
        path : str
            Name of an iRODS data object.

        Returns
        -------
        iRODSDataObject
            Instance of the data object with `path`.

        """
        if self.dataobject_exists(path):
            return self.session.data_objects.get(path)
        raise irods.exception.DataObjectDoesNotExist(path)

    def get_collection(self, path):
        """Instantiate an iRODS collection.

        Parameters
        ----------
        path : str
            Name of an iRODS collection.

        Returns
        -------
        iRODSCollection
            Instance of the collection with `path`.

        """
        if self.collection_exists(path):
            return self.session.collections.get(path)
        raise irods.exception.CollectionDoesNotExist(path)

    def irods_put(self, local_path: str, irods_path: str, resc_name: str = ''):
        """Upload `local_path` to `irods_path` following iRODS
        `options`.

        Parameters
        ----------
        local_path : str
            Path of local file or directory/folder.
        irods_path : str
            Path of iRODS data object or collection.
        resc_name : str
            Optional resource name.

        """
        if not self.icommands:
            options = {
                ALL_KW: '',
                NUM_THREADS_KW: NUM_THREADS,
                REG_CHKSUM_KW: '',
                VERIFY_CHKSUM_KW: ''
            }
            if resc_name not in ['', None]:
                 options[RESC_NAME_KW] = resc_name
            self.session.data_objects.put(local_path, irods_path, **options)
        else:
            commands = [f'iput -aK -N {NUM_THREADS}']
            if resc_name:
                commands.append(f'-R {resc_name}')
            commands.append(f'{local_path} {irods_path}')
            subprocess.call(' '.join(commands), shell=True)

    def irods_get(self, irods_path, local_path, options=None):
        """Download `irods_path` to `local_path` following iRODS
        `options`.

        Parameters
        ----------
        irods_path : str
            Path of iRODS data object or collection.
        local_path : str
            Path of local file or directory/folder.
        options : dict
            iRODS transfer options.

        """
        if options is None:
            options = {}
        if not self.icommands:
            options.update({
                NUM_THREADS_KW: NUM_THREADS,
                VERIFY_CHKSUM_KW: '',
                })
            self.session.data_objects.get(irods_path, local_path, **options)
        else:
            commands = [f'iget -K -N {NUM_THREADS} {irods_path} {local_path}']
            subprocess.call(' '.join(commands), shell=True)

    @staticmethod
    def is_dataobject(obj):
        """Check if `obj` is an iRODS data object.

        Parameters
        ----------
        obj : iRODS object instance
            iRODS instance to check.

        Returns
        -------
        bool
            If `obj` is an iRODS data object.

        """
        return isinstance(obj, irods.data_object.iRODSDataObject)

    @staticmethod
    def is_collection(obj):
        """Check if `obj` is an iRODS collection.

        Parameters
        ----------
        obj : iRODS object instance
            iRODS instance to check.

        Returns
        -------
        bool
            If `obj` is an iRODS collection.

        """
        return isinstance(obj, irods.collection.iRODSCollection)



    def upload_data(self, src_path, dst_coll, resc_name, size, buff=BUFF_SIZE,
                    force=False, diffs=None):
        """Upload data from the local `src_path` to the iRODS
        `dst_coll`.

        When `src_path` is a folder/directory, upload its contents
        recursively to the iRODS collection `dst_coll`.  If `src_path`
        is the path to a file, upload the file.

        Parameters
        ----------
        src_path : str
            Absolute path to local file or folder.
        dst_coll : iRODSCollection
            The iRODS collection to where the data will be uploaded.
        resc_name : str
            Name of the top-level iRODS resource.
        size : int
            Size of data to be uploaded in bytes.
        buff : int
            Buffer size on resource that should remain after upload in
            bytes.
        force : bool
            Ignore storage capacity on resource associated with
            `resc_name`.
        diffs : list
            Output of diff functions.

        """
        logging.info(
            'iRODS UPLOAD: %s-->%s %s', src_path, dst_coll.path,
            resc_name or '')
        src_path = utils.utils.LocalPath(src_path)
        if src_path.is_file() or src_path.is_dir():
            if self.is_collection(dst_coll):
                cmp_path = utils.utils.IrodsPath(dst_coll.path, src_path.name)
            else:
                raise irods.exception.CollectionDoesNotExist(dst_coll)
        else:
            raise FileNotFoundError(
                'ERROR iRODS upload: not a valid source path')
        if resc_name in [None, '']:
            resc_name = self.default_resc
        if diffs is None:
            if src_path.is_file():
                diff, only_fs, _, _ = self.diffObjFile(
                    cmp_path, src_path, scope='checksum')
            else:
                cmp_coll = self.ensure_coll(cmp_path)
                diff, only_fs, _, _ = self.diffIrodsLocalfs(
                    cmp_coll, src_path)
        else:
            diff, only_fs, _, _ = diffs
        if not force:
            space = self.resource_space(resc_name)
            if size > (space - buff):
                logging.info(
                    'ERROR iRODS upload: Not enough free space on resource.',
                    exc_info=True)
                raise NotEnoughFreeSpace(
                    'ERROR iRODS upload: Not enough free space on resource.')
        try:
            # Data object
            if src_path.is_file() and len(diff + only_fs) > 0:
                logging.info(
                    'IRODS UPLOADING file %s to %s', src_path, cmp_path)
                self.irods_put(src_path, cmp_path, resc_name)
            # Collection
            else:
                logging.info('IRODS UPLOAD started:')
                for irods_path, local_path in diff:
                    # Upload files to distinct data objects.
                    _ = self.ensure_coll(irods_dirname(irods_path))
                    logging.info(
                        'REPLACE: %s with %s', irods_path, local_path)
                    self.irods_put(local_path, irods_path, resc_name)
                # Variable `only_fs` can contain files and folders.
                for rel_path in only_fs:
                    # Create subcollections and upload.
                    rel_path = utils.utils.PurePath(rel_path)
                    local_path = src_path.joinpath(rel_path)
                    if len(rel_path.parts) > 1:
                        new_path = cmp_path.joinpath(rel_path.parent)
                    else:
                        new_path = cmp_path
                    _ = self.ensure_coll(new_path)
                    logging.info('UPLOAD: %s to %s', local_path, new_path)
                    irods_path = new_path.joinpath(rel_path.name)
                    logging.info('CREATE %s', irods_path)
                    self.irods_put(local_path, irods_path, resc_name)
        except Exception as error:
            logging.info('UPLOAD ERROR', exc_info=True)
            raise error

    def download_data(self, src_obj, dst_path, size, buff=BUFF_SIZE, force=False, diffs=None):
        """Dowload data from an iRODS `src_obj` to the local `dst_path`.

        When `src_obj` is a collection, download its contents
        recursively to the local folder/directory `dst_path`.  If
        `src_obj` is a data object, download it to a file in the local
        folder/director.

        Parameters
        ----------
        src_obj : iRODSCollection, iRODSDataObject
            The iRODS collection or data object from where the data will
            be downloaded.
        dst_path : str
            Absolute path to local folder/directory.
        size : int
            Size of data to be uploaded in bytes.
        buff : int
            Buffer size on local storage that should remain after
            download in bytes.
        force : bool
            Ignore storage capacity on the storage system of `dst_path`.
        diffs : list
            Output of diff functions.

        """
        logging.info('iRODS DOWNLOAD: %s-->%s', src_obj.path, dst_path)
        if self.is_dataobject_or_collection(src_obj):
            src_path = utils.utils.IrodsPath(src_obj.path)
        else:
            raise FileNotFoundError(
                'ERROR iRODS download: not a valid source path'
            )
        dst_path = utils.utils.LocalPath(dst_path)
        if not dst_path.is_dir():
            logging.info(
                'DOWNLOAD ERROR: destination path does not exist or is not directory',
                exc_info=True)
            raise FileNotFoundError(
                'ERROR iRODS download: destination path does not exist or is not directory')
        if not os.access(dst_path, os.W_OK):
            logging.info(
                'DOWNLOAD ERROR: No rights to write to destination.',
                exc_info=True)
            raise PermissionError(
                'ERROR iRODS download: No rights to write to destination.')
        cmp_path = dst_path.joinpath(src_path.name)
        # TODO perhaps treat this path as part of the diff
        if self.is_collection(src_obj) and not cmp_path.is_dir():
            os.mkdir(cmp_path)
        # Only download if not present or difference in files.
        if diffs is None:
            if self.is_dataobject(src_obj):
                diff, _, only_irods, _ = self.diffObjFile(
                    src_path, cmp_path, scope="checksum")
            else:
                diff, _, only_irods, _ = self.diffIrodsLocalfs(
                    src_obj, cmp_path, scope="checksum")
        else:
            diff, _, only_irods, _ = diffs
        # Check space on destination.
        if not force:
            space = shutil.disk_usage(dst_path).free
            if size > (space - buff):
                logging.info(
                    'ERROR iRODS download: Not enough space on local disk.',
                    exc_info=True)
                raise NotEnoughFreeSpace(
                    'ERROR iRODS download: Not enough space on local disk.')
        # NOT the same force flag.  This overwrites the local file by default.
        # TODO should there be an option/switch for this 'clobber'ing?
        options = {FORCE_FLAG_KW: ''}
        try:
            # Data object
            if self.is_dataobject(src_obj) and len(diff + only_irods) > 0:
                logging.info(
                    'IRODS DOWNLOADING object: %s to %s',
                    src_path, cmp_path)
                self.irods_get(
                    src_path, cmp_path, options=options)
            # Collection
            # TODO add support for "downloading" empty collections?
            else:
                logging.info("IRODS DOWNLOAD started:")
                for irods_path, local_path in diff:
                    # Download data objects to distinct files.
                    logging.info(
                        'REPLACE: %s with %s', local_path, irods_path)
                    self.irods_get(irods_path, local_path, options=options)
                # Variable `only_irods` can contain data objects and
                # collections.
                for rel_path in only_irods:
                    # Create subdirectories and download.
                    rel_path = utils.utils.PurePath(rel_path)
                    irods_path = src_path.joinpath(rel_path)
                    local_path = cmp_path.joinpath(rel_path)
                    if not local_path.parent.is_dir():
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                    logging.info(
                        'INFO: Downloading %s to %s', irods_path,
                        local_path)
                    self.irods_get(irods_path, local_path, options=options)
        except Exception as error:
            logging.info('DOWNLOAD ERROR', exc_info=True)
            raise error

    def diffObjFile(self, objPath, fsPath, scope="size"):
        """
        Compares and iRODS object to a file system file.
        returns ([diff], [only_irods], [only_fs], [same])
        """
        if os.path.isdir(fsPath) and not os.path.isfile(fsPath):
            raise IsADirectoryError("IRODS FS DIFF: file is a directory.")
        if self.session.collections.exists(objPath):
            raise IsADirectoryError("IRODS FS DIFF: object exists already as collection. "+objPath)

        if not os.path.isfile(fsPath) and self.session.data_objects.exists(objPath):
            return ([], [], [objPath], [])

        elif not self.session.data_objects.exists(objPath) and os.path.isfile(fsPath):
            return ([], [fsPath], [], [])

        #both, file and object exist
        obj = self.session.data_objects.get(objPath)
        if scope == "size":
            objSize = obj.size
            fSize = os.path.getsize(fsPath)
            if objSize != fSize:
                return ([(objPath, fsPath)], [], [], [])
            else:
                return ([], [], [], [(objPath, fsPath)])
        elif scope == "checksum":
            objCheck = obj.checksum
            if objCheck == None:
                try:
                    obj.chksum()
                    objCheck = obj.checksum
                except:
                    logging.info('No checksum for '+obj.path)
                    return([(objPath, fsPath)], [], [], [])
            if objCheck.startswith("sha2"):
                sha2Obj = base64.b64decode(objCheck.split('sha2:')[1])
                with open(fsPath, "rb") as f:
                    stream = f.read()
                    sha2 = hashlib.sha256(stream).digest()
                if sha2Obj != sha2:
                    return([(objPath, fsPath)], [], [], [])
                else:
                    return ([], [], [], [(objPath, fsPath)])
            elif objCheck:
                #md5
                with open(fsPath, "rb") as f:
                    stream = f.read()
                    md5 = hashlib.md5(stream).hexdigest()
                if objCheck != md5:
                    return([(objPath, fsPath)], [], [], [])
                else:
                    return ([], [], [], [(objPath, fsPath)])


    def diffIrodsLocalfs(self, coll, dirPath, scope="size"):
        '''
        Compares and iRODS tree to a directory and lists files that are not in sync.
        Syncing scope can be 'size' or 'checksum'
        Returns: zip([dataObjects][files]) where ther is a difference
        collection: iRODS collection
        '''

        listDir = []
        if not dirPath == None:
            if not os.access(dirPath, os.R_OK):
                raise PermissionError("IRODS FS DIFF: No rights to write to destination.")
            if not os.path.isdir(dirPath):
                raise IsADirectoryError("IRODS FS DIFF: directory is a file.")
            for root, dirs, files in os.walk(dirPath, topdown=False):
                for name in files:
                    listDir.append(os.path.join(root.split(dirPath)[1], name).strip(os.sep))
        listColl = []
        if not coll == None:
            for root, subcolls, obj in coll.walk():
                for o in obj:
                    listColl.append(os.path.join(root.path.split(coll.path)[1], o.name).strip('/'))
        diff = []
        same = []
        for locPartialPath in set(listDir).intersection(listColl):
            iPartialPath = locPartialPath.replace(os.sep, "/")
            if scope == "size":
                objSize = self.session.data_objects.get(coll.path + '/' + iPartialPath).size
                fSize = os.path.getsize(os.path.join(dirPath, iPartialPath))
                if objSize != fSize:
                    diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                else:
                    same.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
            elif scope == "checksum":
                objCheck = self.session.data_objects.get(coll.path + '/' + iPartialPath).checksum
                if objCheck == None:
                    try:
                        self.session.data_objects.get(coll.path + '/' + iPartialPath).chksum()
                        objCheck = self.session.data_objects.get(
                                    coll.path + '/' + iPartialPath).checksum
                    except:
                        logging.info('No checksum for '+coll.path + '/' + iPartialPath)
                        diff.append((coll.path + '/' + iPartialPath, 
                                        os.path.join(dirPath, locPartialPath)))
                        continue
                if objCheck.startswith("sha2"):
                    sha2Obj = base64.b64decode(objCheck.split('sha2:')[1])
                    with open(os.path.join(dirPath, locPartialPath), "rb") as f:
                        stream = f.read()
                        sha2 = hashlib.sha256(stream).digest()
                    if sha2Obj != sha2:
                        diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                    else:
                        same.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                elif objCheck:
                    #md5
                    with open(os.path.join(dirPath, locPartialPath), "rb") as f:
                        stream = f.read()
                        md5 = hashlib.md5(stream).hexdigest()
                    if objCheck != md5:
                        diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                    else:
                        same.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
            else: #same paths, no scope
                diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))

        #adding files that are not on iRODS, only present on local FS
        #adding files that are not on local FS, only present in iRODS
        #adding files that are stored on both devices with the same checksum/size
        irodsOnly = list(set(listColl).difference(listDir))
        for i in range(0, len(irodsOnly)):
            irodsOnly[i] = irodsOnly[i].replace(os.sep, "/")
        return (diff, list(set(listDir).difference(listColl)), irodsOnly, same)



    def deleteData(self, item):
        """
        Delete a data object or a collection recursively.
        item: iRODS data object or collection
        """

        if self.session.collections.exists(item.path):
            logging.info("IRODS DELETE: "+item.path)
            try:
                item.remove(recurse = True, force = True)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                print("ERROR IRODS DELETE: no permissions")
                raise cnap
        elif self.session.data_objects.exists(item.path):
            logging.info("IRODS DELETE: "+item.path)
            try:
                item.unlink(force = True)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                print("ERROR IRODS DELETE: no permissions "+item.path)
                raise cnap

    def irods_dirname(path):
        """Find path less the final element for an iRODS path.

        Parameters
        ----------
        path : str
            An iRODS path, relative or absolute.

        Returns
        -------
        str
            iRODS path less the element after the final '/'

        """
        return utils.utils.IrodsPath(path).parent

    def get_irods_size(self, path_names: list) -> int:
        """Collect the sizes of a set of iRODS data objects and/or
        collections and determine the total size.

        Parameters
        ----------
        path_names : list
            Names of logical iRODS paths.

        Returns
        -------
        int
            Total size [bytes] of all iRODS objects found from the
            logical paths in `path_names`.

        """
        irods_sizes = []
        for path_name in path_names:
            irods_name = utils.utils.IrodsPath(path_name)
            if self.collection_exists(irods_name):
                irods_sizes.append(
                    utils.utils.get_coll_size(
                        self.get_collection(irods_name)))
            elif self.dataobject_exists(irods_name):
                irods_sizes.append(
                    utils.utils.get_data_size(
                        self.get_dataobject(irods_name)))
        return sum(irods_sizes)