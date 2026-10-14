import irods.session
import pytest

from ibridges.session import Session

def test_anonymous_session_connects(anonymous_session):
    assert anonymous_session.username == "anonymous"
    assert anonymous_session.has_valid_irods_session()
