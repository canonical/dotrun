# Standard library
import os
import pkg_resources
import sys

# Local packages
from canonicalwebteam.dotrun import (
    DotRun,
    get_projects_data,
    PROJECTS_DATA_PATH,
)


# Set up dotrun for directory
def _dotrun(args):
    env = {}

    for env_string in args["env"]:
        key, value = env_string.split("=")
        env[key] = value

    dotrun = DotRun(workdir=args["directory"] or os.getcwd(), env=env)

    return dotrun


# Command functions
def version(args):
    print(pkg_resources.get_distribution("canonicalwebteam.dotrun").version)
    sys.exit()


def list_projects(args):
    """
    List the names of all projects in the projects_data JSON file
    """

    projects_data = get_projects_data(PROJECTS_DATA_PATH)

    print("\n# Projects\n")

    if projects_data:
        for project_dir in projects_data.keys():
            print(f"* {project_dir}")
    else:
        print("No active projects")

    print("\n")


def install(args):
    _dotrun(args).install(force=True)


def exec_command(args):
    dotrun = _dotrun(args)
    if not args["skip_install"]:
        dotrun.install(force=args["force_install"])
    dotrun.exec(args["remainder"])


def yarn(args):
    dotrun = _dotrun(args)
    if not args["skip_install"]:
        dotrun.install(force=args["force_install"])
    dotrun.exec(["yarn"] + args["remainder"])


def poetry(args):
    if not args["skip_install"]:
        dotrun.install(force=args["force_install"])
    dotrun.exec(["poetry"] + args["remainder"])


def serve(args):
    dotrun = _dotrun(args)
    if not args["skip_install"]:
        dotrun.install(force=args["force_install"])
    dotrun.serve(watch=args["watch"])


def build(args):
    dotrun = _dotrun(args)
    if not args["skip_install"]:
        dotrun.install(force=args["force_install"])
    dotrun.exec(["yarn", "run", "build"])


def test(args):
    dotrun = _dotrun(args)
    if not args["skip_install"]:
        dotrun.install(force=args["force_install"])
    dotrun.exec(["yarn", "run", "test"])


def clean(args):
    _dotrun(args).clean()
