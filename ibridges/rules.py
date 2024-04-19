"""Rule operations."""
import logging

import irods.exception
import irods.rule

from ibridges.session import Session


def execute_rule(session: Session, rule_file: str = '', **kwargs) -> tuple:
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
    kwargs : dict example keywords:
        body    : str,rulename
            Name of the rule on the irods server.
        params : dict
            Rule arguments.
        instance_name : str
            changes between irods rule language and python rules.
        output : str
            Rule output variable(s).


    Returns
    -------
    tuple
        (stdout, stderr)

    """
    if 'output' not in kwargs:
        kwargs['output'] = 'ruleExecOut'
    if 'instance_name' not in kwargs:
        kwargs['instance_name'] = 'irods_rule_engine_plugin-irods_rule_language-instance'

    try:
        rule = irods.rule.Rule(
            session.irods_session, rule_file=rule_file, **kwargs)
        out = rule.execute()
    except irods.exception.NetworkException as error:
        logging.info('Lost connection to iRODS server.')
        return '', repr(error)
    except irods.exception.SYS_HEADER_READ_LEN_ERR as error:
        logging.info('iRODS server hiccuped.  Check the results and try again.')
        return '', repr(error)
    except Exception as error:
        raise ValueError("Unknown rule execution error") from error
        # logging.info('RULE EXECUTION ERROR', exc_info=True)
        # return '', repr(error)
    stdout, stderr = '', ''
    if len(out.MsParam_PI) > 0:
        buffers = out.MsParam_PI[0].inOutStruct
        stdout = (buffers.stdoutBuf.buf or b'').decode()
        # Remove garbage after terminal newline.
        stdout = '\n'.join(stdout.split('\n')[:-1])
        stderr = (buffers.stderrBuf.buf or b'').decode()
    return stdout, stderr
