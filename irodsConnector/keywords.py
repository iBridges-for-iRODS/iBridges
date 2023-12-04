"""Keywords and definitions"""
import irods.column as cm
import irods.keywords as kw
import irods.models as imodels
#from irods.exception import *

# Keywords
ALL_KW = kw.ALL_KW
FORCE_FLAG_KW = kw.FORCE_FLAG_KW
NUM_THREADS_KW = kw.NUM_THREADS_KW  # 'num_threads'
DEST_RESC_NAME_KW = kw.DEST_RESC_NAME_KW
RESC_NAME_KW = kw.RESC_NAME_KW
TICKET_KW = kw.TICKET_KW
VERIFY_CHKSUM_KW = kw.VERIFY_CHKSUM_KW
REG_CHKSUM_KW = kw.REG_CHKSUM_KW
# Map model names to iquest attribute names
COLL_NAME = imodels.Collection.name
DATA_NAME = imodels.DataObject.name
DATA_CHECKSUM = imodels.DataObject.checksum
META_COLL_ATTR_NAME = imodels.CollectionMeta.name
META_COLL_ATTR_VALUE = imodels.CollectionMeta.value
META_DATA_ATTR_NAME = imodels.DataObjectMeta.name
META_DATA_ATTR_VALUE = imodels.DataObjectMeta.value
RESC_NAME = imodels.Resource.name
RESC_PARENT = imodels.Resource.parent
RESC_STATUS = imodels.Resource.status
RESC_CONTEXT = imodels.Resource.context
USER_GROUP_NAME = imodels.UserGroup.name
USER_NAME = imodels.User.name
USER_TYPE = imodels.User.type
# Query operators
LIKE = cm.Like
# ASCII colors
BLUE = '\x1b[1;34m'
DEFAULT = '\x1b[0m'
RED = '\x1b[1;31m'
YEL = '\x1b[1;33m'
# Misc
BUFF_SIZE = 10**9
MULTIPLIER = 1 / 10**9
NUM_THREADS = 4
# Excpetion mapping
exceptions = {
    'PAM_AUTH_PASSWORD_FAILED(None,)': "Wrong password",
    "NetworkException('Client-Server negotiation failure: CS_NEG_REFUSE,CS_NEG_REQUIRE')":
    '"irods_client_server_policy" not set (correctly) in irods_environment.json' 
}
