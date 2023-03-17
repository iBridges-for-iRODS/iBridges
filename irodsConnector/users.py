""" user operations
"""
import irodsConnector.keywords as kw
from irodsConnector.session import Session


class Users(object):
    """Irods User operations """
    def get_user_info(self, ses_man: Session) -> tuple:
        """Query for user type and groups.

        Parameters
        ----------
        ses_man : irods session
            Instance of the Session class

        Returns
        -------
        list
            iRODS user type names
        list
            iRODS group names

        """
        query = ses_man.session.query(kw.USER_TYPE).filter(kw.LIKE(
            kw.USER_NAME, ses_man.session.username))
        user_type = [
            list(result.values())[0] for result in query.get_results()
        ][0]
        query = ses_man.session.query(kw.USER_GROUP_NAME).filter(kw.LIKE(
            kw.USER_NAME, ses_man.session.username))
        user_groups = [
            list(result.values())[0] for result in query.get_results()
        ]
        return user_type, user_groups
