import abc
import argparse
from abc import abstractmethod

from ibridges.cli.util import cli_authenticate


class ShellArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if status:
            print(f'Error: {message}')
        self.printed_help = True


class BaseCliCommand(abc.ABC):
    autocomplete = []
    names = []
    description = "No description available."
    examples = []

    @classmethod
    def get_parser(cls, parser_func=ShellArgumentParser):
        extra_kwargs = cls.get_examples(parser_func)

        if parser_func == ShellArgumentParser or parser_func == argparse.ArgumentParser:
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
        raise NotImplementedError()

    @classmethod
    def run_command(cls, args):
        parser = cls.get_parser(argparse.ArgumentParser)
        with cli_authenticate(parser) as session:
            cls.run_shell(session, parser, args)

    @classmethod
    def get_examples(cls, parser_func):
        extra_kwargs = {}
        if len(getattr(cls, "examples")) == 0:
            return {}

        if parser_func == ShellArgumentParser:
            examples = [f"> {cls.names[0]} {ex}" for ex in cls.examples]
        else:
            examples = [f"> ibridges {cls.names[0]} {ex}" for ex in cls.examples]
        ex_str = "\n".join(examples)
        epilog = f"Examples:\n\n{ex_str}"
        return {"epilog": epilog}
