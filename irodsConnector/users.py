""" user operations
"""
from . import keywords as kw
from . import session


class Users(object):
    """Irods User operations """

    def __init__(self, sess_man: session.Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            sess_man : irods session
                instance of the Session class

        """
        self.sess_man = sess_man

    def get_user_info(self) -> tuple:
        """Query for user type and groups.

        Returns
        -------
        list
            iRODS user type names
        list
            iRODS group names

        """
        query = self.sess_man.session.query(kw.USER_TYPE).filter(kw.LIKE(
            kw.USER_NAME, self.sess_man.username))
        user_type = [
            list(result.values())[0] for result in query.get_results()
        ][0]
        query = self.sess_man.session.query(kw.USER_GROUP_NAME).filter(kw.LIKE(
            kw.USER_NAME, self.sess_man.username))
        user_groups = [
            list(result.values())[0] for result in query.get_results()
        ]
        return user_type, user_groups
