"""Base tools for the CLI and shell subcommands."""

from __future__ import annotations

import abc
import argparse
from abc import abstractmethod

from ibridges.cli.util import cli_authenticate


class ShellArgumentParser(argparse.ArgumentParser):
    """Argument parser used for commands used in the shell.

    Arguments are the same as for the normal argparse.ArgumentParser
    and behavior is the same, except for not exiting when an error is raised.
    """

    def exit(self, status=0, message=None):
        """Fake exit when an error is raised."""
        if status:
            print(f'Error: {message}')
        self.printed_help = True  # pylint: disable=attribute-defined-outside-init


class BaseCliCommand(abc.ABC):
    """Base class for creating subcommands for iBridges.

    You will need to at least implement the run_shell method
    to create a new subcommand. Most likely you will also want to
    override the _mod_parser subcommand, which allows you to define the
    arguments of your new command.

    You should also look to set the
    class attributes: names (list of aliases for the command),
    description (description to be shown with the help command).
    Optionally, you can also set the examples with the cls.examples class attribute,
    and cls.autocomplete
    to enable the shell to autocomplete remote or local paths.
    """

    autocomplete: list[str] = []  # Autocompletion for positional arguments
    names: list[str] = []  # Names of the subcommand, need at least one name.
    description: str = "No description available."  # Description of the subcommand.
    examples: list[str] = []  # Examples to be shown in the help, omit ibridges and subcommand name.

    @classmethod
    def get_parser(cls, parser_func=ShellArgumentParser):
        """Create a new parser for either the shell or the CLI.

        Parameters
        ----------
        parser_func, optional
            Function or ArgumentParser class to initialize the parser.

        Returns
        -------
            An argument parser with the arguments set in the proper way, description, etc.

        """
        extra_kwargs = cls.get_examples(parser_func)

        if parser_func in [ShellArgumentParser, argparse.ArgumentParser]:
            parser = parser_func(cls.names[0], description=cls.description, **extra_kwargs,
                                 formatter_class=argparse.RawTextHelpFormatter
                                 )
        else:
            parser = parser_func(cls.names[0], description=cls.description,
                                help=cls.description, aliases=cls.names[1:], **extra_kwargs,
                                formatter_class=argparse.RawTextHelpFormatter)
        return cls._mod_parser(parser)

    @classmethod
    def _mod_parser(cls, parser):
        return parser

    @staticmethod
    @abstractmethod
    def run_shell(session, parser, args):
        """Run the subcommand in the shell.

        Parameters
        ----------
        session:
            Session to be used for running the subcommand.
        parser:
            Parser that the subcommand was created with. Can be used to
            show errors.
        args:
            Arguments that were parsed with the parser.

        """
        raise NotImplementedError()

    @classmethod
    def run_command(cls, args):
        """Run the command in the CLI.

        Most of the time, you will not need to implement this, since by default
        the run_shell method is used. However, if you need different behavior
        from the CLI compared to the shell, you can do implement here.

        Parameters
        ----------
        args
            Arguments to be parsed.

        """
        parser = cls.get_parser(argparse.ArgumentParser)
        with cli_authenticate(parser) as session:
            cls.run_shell(session, parser, args)

    @classmethod
    def get_examples(cls, parser_func):
        """Add the examples to the parser.

        Parameters
        ----------
        parser_func
            Parser function or class to append the examples to.

        Returns
        -------
            Dictionary with the epilog key, if there are no examples, an empty dictionary.

        """
        if len(cls.examples) == 0:
            return {}

        if parser_func == ShellArgumentParser:
            examples = [f"> {cls.names[0]} {ex}" for ex in cls.examples]
        else:
            examples = [f"> ibridges {cls.names[0]} {ex}" for ex in cls.examples]
        ex_str = "\n".join(examples)
        epilog = f"Examples:\n\n{ex_str}"
        return {"epilog": epilog}
