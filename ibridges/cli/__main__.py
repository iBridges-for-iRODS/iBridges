import argparse
import sys

from ibridges.cli.other import CLI_BULTIN_COMMANDS
from ibridges.cli.shell import ALL_BUILTIN_COMMANDS


def create_parser():
    main_parser = argparse.ArgumentParser(prog="ibridges")
    subparsers = main_parser.add_subparsers(dest="subcommand")

    for command_class in ALL_BUILTIN_COMMANDS+CLI_BULTIN_COMMANDS:
        subpar = command_class.get_parser(subparsers.add_parser)
        subpar.set_defaults(func=command_class.run_command)
    return main_parser

def main():
    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])
    args.func(args)

if __name__ == "__main__":
    main()
