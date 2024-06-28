"""iBridges package that implements an API for iRods."""

from ibridges.data_operations import download, sync, upload
from ibridges.meta import MetaData
from ibridges.path import IrodsPath
from ibridges.search import search_data
from ibridges.session import Session
from ibridges.tickets import Tickets

__all__ = [
    "Session",
    "IrodsPath",
    "download",
    "upload",
    "MetaData",
    "Tickets",
    "search_data",
    "sync",
]
