"""iBridges package that implements an API for iRods."""

from ibridges.data_operations import download, get_collection, get_dataobject, upload
from ibridges.meta import MetaData
from ibridges.path import IrodsPath
from ibridges.search import search_data
from ibridges.session import Session
from ibridges.sync import sync_data
from ibridges.tickets import Tickets

__all__ = ["Session", "IrodsPath", "download", "get_collection", "get_dataobject", "upload",
           "MetaData", "Tickets", "search_data", "sync_data"]
