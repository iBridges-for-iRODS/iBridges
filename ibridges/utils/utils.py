### Filesystem utils
def ensure_dir(pathname: path.LocalPath) -> bool:
    """Ensure `pathname` exists as a directory.

    Parameters
    ----------
    pathname : pathLocalPath
        The path to be ensured.

    Returns
    -------
    bool
        If `pathname` exists/was created.

    """
    try:
        pathname.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as error:
        logging.info('Error ensuring directory: %r', error)
    return dirpath.is_dir()


def get_downloads_dir() -> path.LocalPath:
    """Find the platform-dependent 'Downloads' directory.

    Returns
    -------
    LocalPath
        Absolute path to 'Downloads' directory.

    """
    if is_posix():
        return path.LocalPath('~', 'Downloads').expanduser()
    else:
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            return path.LocalPath(winreg.QueryValueEx(key, downloads_guid)[0])


def get_working_dir() -> path.LocalPath:
    """Determine working directory where iBridges started.

    Returns
    -------
    LocalPath
        Directory path of the executable.

    """
    if getattr(sys, 'frozen', False):
        return path.LocalPath(sys.executable).parent
    elif __file__:
        return path.LocalPath(__file__).parent
    else:
        return path.LocalPath('.')


def get_local_size(pathnames: list) -> int:
    """Collect the sizes of a set of local files and/or directories and
    determine the total size recursively.

    Parameters
    ----------
    pathnames : list
        Names of input paths.

    Returns
    -------
    int
        Total size [bytes] of all local files found from the paths in
        `pathnames`.

    """
    sizes = []
    for pathname in pathnames:
        pathobj = path.LocalPath(pathname)
        if pathobj.is_dir():
            for dirname, _, filenames in os.walk(pathobj):
                for filename in filenames:
                    filepath = path.LocalPath(dirname, filename)
                    sizes.append(filepath.stat().st_size)
        elif pathobj.is_file():
            sizes.append(pathobj.stat().st_size)
    return sum(sizes)


### Network utils
def can_connect(hostname: str, port: int) -> bool:
    """Check connectivity to an iRODS server.

    Parameters
    ----------
    hostname : str
        FQDN/IP of an iRODS server.

    Returns
    -------
    bool
        Connection to `hostname` possible.

    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.settimeout(10.0)
            sock.connect((hostname, port))
            return True
        except socket.error:
            return False

### Output conversion

def bytes_to_str(value: int) -> str:
    """Render incoming number of bytes to a string with units.

    Parameters
    ----------
    value : int
        Number of bytes.

    Returns
    -------
    str
        Rendered string with units.

    """
    if value < 1e12:
        return f'{value / 1e9:.3f} GB'
    else:
        return f'{value / 1e12:.3f} TB'


### Logger utils
def set_log_level(log_level: int = None):
    """Set the log level excluding DEBUG-level entries from other
    modules.  If log_level not specified, attempt to access the verbose
    setting from the configuration.

    Parameters
    ----------
    log_level : int
        Level to set the current logger.

    """
    if log_level is None:
        cntxt = context.Context()
        verbose = cntxt.ibridges_configuration.config.get('verbose', 'info')
        log_level = LOG_LEVEL.get(verbose, logging.INFO)
    logging.getLogger().setLevel(log_level)
    if log_level == logging.DEBUG:
        for logger in logging.Logger.manager.loggerDict.values():
            if hasattr(logger, 'name'):
                if logger.name != 'root' and not logger.name.startswith('irods'):
                    logger.debug('Disabling logger: %s', logger.name)
                    logger.disabled = True


def init_logger(app_name: str):
    """Initialize the application logging service.

    Parameters
    ----------
    app_name : str
        Application name as base name of the log file.

    """
    old_factory = logging.getLogRecordFactory()

    def new_factory(*args, **kwargs) -> logging.LogRecord:
        """Custom record factory"""
        record = old_factory(*args, **kwargs)
        # Limit the size of the log message to something sane.
        record.msg = record.msg[:MAX_MSG_LEN]
        record.prefix = ''
        record.postfix = ''
        if record.levelname == 'WARNING':
            record.prefix = YELLOW
            record.postfix = DEFAULT
        if record.levelname == 'ERROR':
            record.prefix = RED
            record.postfix = DEFAULT
        return record

    logging.setLogRecordFactory(new_factory)
    logger = logging.getLogger()
    logdir = path.LocalPath(context.IBRIDGES_DIR).expanduser()
    logfile = logdir.joinpath(f'{app_name}.log')
    log_formatter = logging.Formatter(
        '[%(asctime)s] %(name)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')
    file_handler = logging.handlers.RotatingFileHandler(logfile, 'a', 100000, 1)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
    log_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(prefix)s%(message)s%(postfix)s')
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)
    # Indicate start of a new session
    with open(logfile, 'a', encoding='utf-8') as logfd:
        logfd.write('\n\n')
        underscores = f'{"_" * 50}\n'
        logfd.write(underscores * 2)
        logfd.write(f'\t\t{datetime.datetime.now().isoformat()}\n')
        logfd.write(underscores * 2)
