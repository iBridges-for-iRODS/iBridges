"""Entry point for CLI interface."""

import argparse
import sys

from ibridges.cli.other import CLI_BULTIN_COMMANDS
from ibridges.cli.shell import get_all_shell_commands


def create_parser():
    """Create an argparse parser for the CLI.

    Returns
    -------
        An argparse.ArgumentParser object with all the subcommands.

    """
    main_parser = argparse.ArgumentParser(prog="ibridges")
    subparsers = main_parser.add_subparsers(dest="subcommand")

    for command_class in get_all_shell_commands()+CLI_BULTIN_COMMANDS:
        subpar = command_class.get_parser(subparsers.add_parser)
        subpar.set_defaults(func=command_class.run_command)
    return main_parser

def main():
    """Start main function of the CLI."""
    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])
    args.func(args)

if __name__ == "__main__":
    main()
