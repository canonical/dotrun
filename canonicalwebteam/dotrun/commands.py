# Standard library
import os
import pkg_resources
import sys

# Local packages
from canonicalwebteam.dotrun.models import DotRun, ProjectData


# Set up dotrun for directory
def _dotrun(args):
    env = {}

    for env_string in args["env"]:
        key, value = env_string.split("=")
        env[key] = value

    dotrun = DotRun(
        project_data=ProjectData(args["directory"] or os.getcwd()), env=env
    )

    return dotrun


# Command functions
def version(args):
    print(pkg_resources.get_distribution("canonicalwebteam.dotrun").version)
    sys.exit()


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
    dotrun = _dotrun(args)
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


def list_projects():
    """
    List the names of all projects in the projects_data JSON file
    """

    projects_data = ProjectData().all()

    print("\n# Projects\n")

    for project_id, project_data in projects_data.items():
        print(f"{project_id}: {project_data['path']}")

    print("\n")


def clean(args):
    _dotrun(args).clean()
