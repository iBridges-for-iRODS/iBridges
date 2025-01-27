from irods.exception import CollectionDoesNotExist
from irods.exception import DataObjectDoesNotExist
from irods.exception import DoesNotExist

class NotACollection(DoesNotExist):
    pass

class NotADataObject(DoesNotExist):
    pass
