"""iBridges package that implements an API for iRods."""

from ibridges.data_operations import download, get_collection, get_dataobject, upload
from ibridges.meta import MetaData
from ibridges.path import IrodsPath
from ibridges.session import Session
from ibridges.tickets import Tickets
from ibridges.search import search_data
from ibridges.sync import sync_data

__all__ = ["Session", "IrodsPath", "download", "get_collection", "get_dataobject", "upload",
           "MetaData", "Tickets"]
