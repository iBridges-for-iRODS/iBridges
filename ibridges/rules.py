"""Rule operations."""

import logging
from typing import Optional

import irods.exception
import irods.rule

from ibridges.session import Session


def execute_rule(
    session: Session,
    rule_file: Optional[str],
    params: Optional[dict],
    output: str = "ruleExecOut",
    instance_name: str = "irods_rule_engine_plugin-irods_rule_language-instance",
    **kwargs,
) -> tuple:
    """Execute an iRODS rule.

    params format example:
    >>> # Notice extra quotes for string literals
    >>> params = {
    >>>     '*obj': '"/zone/home/user"',
    >>>     '*name': '"attr_name"',
    >>>     '*value': '"attr_value"'
    >>> }

    Parameters
    ----------
    session : ibridges.session
        The irods session
    rule_file : str
        Name of the iRODS rule file, or a file-like object representing it.
    params: dict
        Rule input variable(s).
    output : str
        Rule output variable(s).
    instance_name : str
        Changes between irods rule language and python rules.
    kwargs : dict
        optional irods rule parameters.
        For more information: https://github.com/irods/python-irodsclient

    Returns
    -------
    tuple
        (stdout, stderr)

    """
    try:
        rule = irods.rule.Rule(
            session.irods_session,
            rule_file=rule_file,
            params=params,
            instance_name=instance_name,
            output=output,
            **kwargs,
        )
        out = rule.execute()
    except irods.exception.NetworkException as error:
        logging.info("Lost connection to iRODS server.")
        return "", repr(error)
    except irods.exception.SYS_HEADER_READ_LEN_ERR as error:
        logging.info("iRODS server hiccuped.  Check the results and try again.")
        return "", repr(error)
    except Exception as error:
        raise ValueError("Unknown rule execution error") from error
        # logging.info('RULE EXECUTION ERROR', exc_info=True)
        # return '', repr(error)
    stdout, stderr = "", ""
    if len(out.MsParam_PI) > 0:
        buffers = out.MsParam_PI[0].inOutStruct
        stdout = (buffers.stdoutBuf.buf or b"").decode()
        # Remove garbage after terminal newline.
        stdout = "\n".join(stdout.split("\n")[:-1])
        stderr = (buffers.stderrBuf.buf or b"").decode()
    return stdout, stderr
