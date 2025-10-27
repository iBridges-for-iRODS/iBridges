"""Entry point for CLI interface."""

import argparse
import sys

from ibridges.cli.other import CLI_BULTIN_COMMANDS
from ibridges.cli.shell import get_all_shell_commands

from importlib.metadata import version


class SubcommandHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super().__init__(prog)
        self.parser = None  # we'll assign this later

    def format_help(self):
        # Access the parser object we attached
        parser = self.parser
        prog = parser.prog

        # Collect subcommands and their help text
        subcommands_text = []
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for cmd, subparser in action.choices.items():
                    help_text = (subparser.description or subparser.help or "").strip()
                    help_text = help_text.replace("\n", "\n        ")
                    subcommands_text.append(f"    {cmd}:\n        {help_text}")

        subcommands_block = "\n".join(subcommands_text)

        return f"""iBridges CLI version {version("ibridges")}

Usage: {prog} [subcommand] [options]

Available subcommands:
{subcommands_block}

The iBridges CLI does not implement the complete iBridges API. For example, there
are no commands to modify metadata on the irods server.

Example usage:

    {prog} download "irods:~/test.txt"
    {prog} upload ~/test.txt "irods:/test"
    {prog} init
    {prog} sync ~/directory "irods:~/collection"
    {prog} list irods:~/collection
    {prog} mkcoll irods://~/bli/bla/blubb
    {prog} tree irods:~/collection
    {prog} search --path-pattern "%.txt"
    {prog} search --metadata "key" "value" "units"
    {prog} search --metadata "key" --metadata "key2" "value2"
    {prog} setup uu-its

Reuse a configuration by an alias:
    {prog} init ~/.irods/irods_environment.json --alias my_irods
    {prog} init my_irods

Program information:
    -v, --version - display CLI version and exit
    -h, --help    - display this help file and exit
"""

def create_parser():
    """Create an argparse parser for the CLI.

    Returns
    -------
        An argparse.ArgumentParser object with all the subcommands.

    """
    main_parser = argparse.ArgumentParser(prog="ibridges",
    add_help=False,  # we handle help manually
    formatter_class=SubcommandHelpFormatter)

    formatter = main_parser.formatter_class(main_parser.prog)
    formatter.parser = main_parser
    main_parser.formatter_class = lambda prog: formatter

    subparsers = main_parser.add_subparsers(dest="subcommand")

    for command_class in get_all_shell_commands()+CLI_BULTIN_COMMANDS:
        subpar = command_class.get_parser(subparsers.add_parser)
        subpar.set_defaults(func=command_class.run_command)
    return main_parser

def main():
    """Start main function of the CLI."""
    parser = create_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        return
    args = parser.parse_args(sys.argv[1:])
    args.func(args)

if __name__ == "__main__":
    main()
