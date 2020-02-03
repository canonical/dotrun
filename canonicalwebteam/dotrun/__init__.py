#! /usr/bin/env python3

# Standard library
import argparse
import os
import pkg_resources
import sys

# Local packages
from canonicalwebteam.dotrun.models import Project


# Define available commands
# ===
cli_parser = argparse.ArgumentParser(
    description=(
        "Containerized project-level dependency management and "
        "package.json commands"
    )
)

# Options
cli_parser.add_argument(
    "-C", "--directory", help="The directory in which to run commands"
)
cli_parser.add_argument(
    "-s",
    "--skip-install",
    action="store_true",
    default=False,
    help="Don't check for python or node dependencies before running",
)
cli_parser.add_argument(
    "--env",
    action="append",
    default=[],
    help="Environment variables to use when running commands",
)

# Main command
cli_parser.add_argument(
    "command",
    help=(
        "A package.json command to run with `yarn run XXX` inside dotrun.\n"
        "Simply typing `dotrun` will run `yarn run start`."
        "\n"
        "Or a special command - one of:"
        "- version: Print the version\n"
        "- exec: Execute a command within the dotrun context\n"
        "- install: Reinstall node and python dependencies\n"
        "- clean: Run `yarn run clean` and remove all dotrun files\n"
    ),
    nargs="?",
    default="start",
)
cli_parser.add_argument("remainder", nargs=argparse.REMAINDER)


def cli(args):
    """
    Parse the command-line arguments
    """

    arguments = cli_parser.parse_args(args)

    # Commands that don't need dependencies
    if arguments.command == "version":
        print(
            pkg_resources.get_distribution("canonicalwebteam.dotrun").version
        )
        sys.exit()

    # Compile list of environment variables
    env_extra = {}

    for env_string in arguments.env:
        key, value = env_string.split("=")
        env_extra[key] = value

    # Prepare dotrun object
    path = os.getcwd()

    if arguments.directory:
        path = os.path.abspath(arguments.directory)

    dotrun = Project(
        path=path, env_extra=env_extra
    )

    # Process command

    # Clean runs before install
    if arguments.command == "clean":
        return dotrun.clean()

    if arguments.command == "exec":
        return dotrun.exec(arguments.remainder or ["bash"])

    if arguments.command == "install":
        return dotrun.install(force=True)

    if not arguments.skip_install:
        dotrun.install(force=False)

    return dotrun.exec(
        ["yarn", "--no-default-rc", "run", arguments.command]
        + arguments.remainder
    )
