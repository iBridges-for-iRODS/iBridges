"""Definition of keywors and operators for iCAT searches."""

import irods.column as cm
import irods.models as imodels

# search terms (iCAT column names)
COLL_NAME = imodels.Collection.name
COLL_ID = imodels.Collection.id
DATA_NAME = imodels.DataObject.name
DATA_PATH = imodels.DataObject.path
DATA_ID = imodels.DataObject.id
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

# operators
LIKE = cm.Like
