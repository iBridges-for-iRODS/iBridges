import argparse
import sys
from pathlib import Path

from ibridges.cli.base import BaseCliCommand
from ibridges.cli.config import IbridgesConf
from ibridges.cli.meta import CliMetaList
from ibridges.cli.shell import ALL_BUILTIN_COMMANDS, IBridgesShell
from ibridges.cli.util import cli_authenticate
from ibridges.session import Session
from ibridges.interactive import DEFAULT_IENV_PATH
from ibridges.util import (
    find_environment_provider,
    get_environment_providers,
    print_environment_providers,
)


class CliShell(BaseCliCommand):
    names = ["shell"]
    description = "Shell for ibridges commands with autocomplete"

    @staticmethod
    def run_shell(session, parser, args):
        raise NotImplementedError()

    @classmethod
    def run_command(cls, args):
        IBridgesShell().cmdloop()

class CliAlias(BaseCliCommand):
    names = ["alias"]
    description = "Print existing aliases or create new ones."

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "alias",
            help="The new alias to be created",
            type=str,
            default=None,
            nargs="?",
        )
        parser.add_argument(
            "env_path",
            help="iRODS environment path.",
            type=Path,
            default=None,
            nargs="?"
        )
        parser.add_argument(
            "--delete", "-d",
            help="Delete the alias.",
            action="store_true",
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        raise NotImplementedError()

    @classmethod
    def run_command(cls, args):
        parser = cls.get_parser(argparse.ArgumentParser)
        ibridges_conf = IbridgesConf(parser)
        if args.alias is None:
            for ienv_path, entry in ibridges_conf.servers.items():
                prefix = " "
                if ibridges_conf.cur_env in (entry.get("alias", None), ienv_path):
                    prefix = "*"
                cur_alias = entry.get("alias", "[no alias]")
                print(f"{prefix} {cur_alias} -> {ienv_path}")
            return

        # if args.alias == "default":
            # parser.error("Cannot change 'default' alias.")

        if args.delete:
            ibridges_conf.delete_alias(args.alias)
            return

        if args.env_path is None:
            parser.error("Supply env_path to your iRODS environment file to set the alias.")
        else:
            ienv_path = str(args.env_path.absolute())

        if not Path(args.env_path).is_file():
            parser.error(f"Supplied env_path '{args.env_path}' does not exist.")

        ibridges_conf.set_alias(args.alias, ienv_path)


class CliInit(BaseCliCommand):
    names = ["init"]
    description = "Create a cached password for future use."

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "irods_env_path_or_alias",
            help="The path to your iRODS environment JSON file.",
            type=Path,
            default=None,
            nargs="?",
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        raise NotImplementedError()

    @classmethod
    def run_command(cls, args):
        parser = cls.get_parser(argparse.ArgumentParser)
        IbridgesConf(parser).set_env(args.irods_env_path_or_alias)

        with cli_authenticate(parser) as session:
            if not isinstance(session, Session):
                parser.error(f"Irods session '{session}' is not a session.")
        print("ibridges init was succesful.")


class CliSetup(BaseCliCommand):
    names = ["setup"]
    description = "Use templates to create an iRODS environment json."

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "server_name",
            help="Server name to create your irods_environment.json for.",
            type=str,
            default=None,
            nargs="?",
        )
        parser.add_argument("--list", help="List all available server names.", action="store_true")
        parser.add_argument(
            "-o",
            "--output",
            help="Store the environment to a file.",
            type=Path,
            default=DEFAULT_IENV_PATH,
            required=False,
        )
        parser.add_argument(
            "--overwrite", help="Overwrite the irods environment file.", action="store_true"
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        raise NotImplementedError()

    @classmethod
    def run_command(cls, args):
        parser = cls.get_parser(argparse.ArgumentParser)
        env_providers = get_environment_providers()
        if args.list:
            if len(env_providers) == 0:
                print(
                    "No server information was found. To use this function, please install a plugin"
                    " such as:\n\nhttps://github.com/iBridges-for-iRODS/ibridges-servers-uu"
                    "\n\nAlternatively create an irods_environment.json by yourself or with the help "
                    "of your iRODS administrator."
                )
            print_environment_providers(env_providers)
            return

        try:
            provider = find_environment_provider(env_providers, args.server_name)
        except ValueError:
            parser.error(
                f"Unknown server with name {args.server_name}.\n"
                "Use `ibridges setup --list` to list all available server names."
            )

        user_answers = {}
        for question in provider.questions:
            user_answers[question] = input(question + ": ")

        json_str = provider.environment_json(args.server_name, **user_answers)
        if args.output.is_file() and not args.overwrite:
            print(f"File {args.output} already exists, use --overwrite or copy the below manually.")
            print("\n")
            print(json_str)
        elif args.output.is_dir():
            parser.error(f"Output {args.output} is a directory, cannot export irods_environment" " file.")
            sys.exit(234)
        else:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(json_str)

CLI_BULTIN_COMMANDS=[CliShell, CliAlias, CliInit, CliSetup]


