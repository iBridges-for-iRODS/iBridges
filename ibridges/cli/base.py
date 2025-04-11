import argparse
import abc
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

    @classmethod
    def get_parser(cls, parser_func=ShellArgumentParser):
        if parser_func == ShellArgumentParser or parser_func == argparse.ArgumentParser:
            parser = parser_func(cls.names[0], description=cls.description)
        else:
            parser = parser_func(cls.names[0], description=cls.description,
                                help=cls.description, aliases=cls.names[1:])
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
