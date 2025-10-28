"""Entry point for CLI interface."""

import argparse
import importlib.metadata
import sys
from importlib.metadata import version

from ibridges.cli.other import CLI_BULTIN_COMMANDS
from ibridges.cli.shell import get_all_shell_commands

# pylint: disable=protected-access


class ModuleGroupedHelpFormatter(argparse.RawTextHelpFormatter):
    """Custom help formatter that groups commands by the module they come from."""

    def list_ibridges_shell_commands(self):
        """Return a dict mapping CLI command name -> (package name, version)."""
        commands = {}
        for dist in importlib.metadata.distributions():
            for ep in dist.entry_points:
                if ep.group == "ibridges.shell":  # ibridges shell entrypoint
                    commands[ep.name] = (dist.metadata["Name"], dist.version)
        return commands

    def format_help(self):
        """Format the main help, create sections for plugin commands."""
        parser = self.parser
        prog = parser.prog

        # Determine if this is the top-level parser (has subcommands)
        is_main_parser = any(isinstance(a, argparse._SubParsersAction) for a in parser._actions)

        # Map command -> (package, version)
        cmd_packages = self.list_ibridges_shell_commands()

        grouped_commands = {}

        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                seen = set()
                for name, subparser in action._name_parser_map.items():
                    if name in seen:
                        continue

                    # Handle aliases
                    aliases = [
                        a
                        for a, p in action._name_parser_map.items()
                        if p is subparser and a != name
                    ]
                    seen.update([name] + aliases)
                    name_part = name + (f" ({', '.join(aliases)})" if aliases else "")

                    # Description
                    desc = getattr(subparser, "description", "(no description)").replace(
                        "\n", "\n        "
                    )

                    # Determine package
                    pkg, ver = cmd_packages.get(name, ("ibridges", version("ibridges")))
                    heading = f"{pkg} commands (v{ver})"

                    grouped_commands.setdefault(heading, []).append(
                        f"    {name_part}:\n        {desc}"
                    )

        lines = []

        if grouped_commands:
            # Sort headings so "ibridges" commands always come first
            sorted_headings = sorted(
                grouped_commands.keys(),
                key=lambda h: (not h.lower().startswith("ibridges "), h.lower())
                )

            for heading in sorted_headings:
                entries = grouped_commands[heading]
                lines.append(f"{heading}:\n" + "\n".join(entries) + "\n")

        # Only show the header and footer if this is the top-level parser
        if is_main_parser:
            header = [
                f"iBridges CLI version {version('ibridges')}\n",
                f"Usage: {prog} [subcommand] [options]\n",
            ]
            header.extend(lines)
            footer = f"""
    The iBridges CLI does not implement the complete iBridges API. For example, there
    are no commands to modify the access rights to data.

    Example usage:

        {prog} download "irods:~/test.txt"
        {prog} upload ~/test.txt "irods:/test"
        {prog} init
        {prog} sync ~/directory "irods:~/collection"
        {prog} list irods:~/collection
        {prog} meta-add irods:some_dataobj_or_collection new_key new_value new_units
        {prog} meta-list irods:some_dataobj_or_collection
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
        -h, --help    - display this help file and exit
    """
            header.append(footer)
            lines = header
        else:
            lines.append(f"\n\n     {prog}\n")

        return "\n".join(lines)


def create_parser():
    """Create an argparse parser for the CLI.

    Returns
    -------
        An argparse.ArgumentParser object with all the subcommands.

    """
    main_parser = argparse.ArgumentParser(
        prog="ibridges",
        formatter_class=ModuleGroupedHelpFormatter,
    )

    formatter = main_parser.formatter_class(main_parser.prog)
    formatter.parser = main_parser
    main_parser.formatter_class = lambda prog: formatter

    subparsers = main_parser.add_subparsers(dest="subcommand")

    # Add commands from classes
    for command_class in get_all_shell_commands() + CLI_BULTIN_COMMANDS:
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
