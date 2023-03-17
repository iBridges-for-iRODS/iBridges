""" user operations
"""
import irodsConnector.keywords as kw
from irodsConnector.session import Session


class Users(object):
    """Irods User operations """
    _ses_man = None

    def __init__(self, ses_man: Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            ses_man : irods session
                instance of the Session class

        """
        self._ses_man = ses_man

    def get_user_info(self) -> tuple:
        """Query for user type and groups.

        Returns
        -------
        list
            iRODS user type names
        list
            iRODS group names

        """
        query = self._ses_man.session.query(kw.USER_TYPE).filter(kw.LIKE(
            kw.USER_NAME, self._ses_man.session.username))
        user_type = [
            list(result.values())[0] for result in query.get_results()
        ][0]
        query = self._ses_man.session.query(kw.USER_GROUP_NAME).filter(kw.LIKE(
            kw.USER_NAME, self._ses_man.session.username))
        user_groups = [
            list(result.values())[0] for result in query.get_results()
        ]
        return user_type, user_groups
