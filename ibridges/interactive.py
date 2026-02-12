"""Deprecated module with interactive elements."""

import warnings

from ibridges.authenticate import interactive_auth as iauth


def interactive_auth(*args, **kwargs):
    """Authenticate interactively.

    This function has been moved to ibridges.authenticate.
    """
    warnings.warn("ibridges.interactive.interactive_auth() has been moved, "
                  "use ibridges.authenticate.interactive_auth instead.",
                  DeprecationWarning)
    return iauth(*args, **kwargs)
