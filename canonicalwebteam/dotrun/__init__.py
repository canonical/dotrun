# Standard library
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from hashlib import md5
from glob import glob

# Packages
import toml
from termcolor import cprint


PROJECTS_DATA_PATH = os.environ["SNAP_USER_COMMON"] + "/projects.json"


@contextmanager
def cwd(path):
    """
    Context manager for temporarily changing directory
    """

    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


def _get_projects_data(filepath):
    """
    Read the JSON file in the filepath
    """

    projects_data = {}

    if os.path.isfile(filepath):
        cprint(f"- Reading from {filepath}", "magenta")
        with open(filepath) as project_data_json:
            projects_data = json.load(project_data_json)

    return projects_data


def _save_project_data(project_data, project_dir):
    """
    Save the settings for a project to the PROJECT_DATA_PATH JSON file
    """

    projects_data = _get_projects_data(PROJECTS_DATA_PATH)
    projects_data[project_dir] = project_data

    with open(PROJECTS_DATA_PATH, "w") as projects_data_json:
        cprint(f"- Saving to {PROJECTS_DATA_PATH}", "magenta")
        json.dump(projects_data, projects_data_json)


def _clear_project_data(project_dir):
    """
    Clear the data for project_dir
    """

    projects_data = _get_projects_data(PROJECTS_DATA_PATH)
    projects_data.pop(project_dir, None)

    with open(PROJECTS_DATA_PATH, "w") as projects_data_json:
        cprint(f"- Removing {project_dir} from {PROJECTS_DATA_PATH}", "magenta")
        json.dump(projects_data, projects_data_json)


def _get_file_hash(filename):
    """
    Produce an MD5 hash value from the contents of a lockfile
    """

    file_hash = None

    if os.path.isfile(filename):
        file_hash = md5()

        with open(filename, "rb") as file_handler:
            for chunk in iter(lambda: file_handler.read(4096), b""):
                file_hash.update(chunk)

    return file_hash.hexdigest()


def list_projects():
    """
    List the names of all projects in the projects_data JSON file
    """

    projects_data = _get_projects_data(PROJECTS_DATA_PATH)

    print("\n# Projects\n")

    if projects_data:
        for project_dir in projects_data.keys():
            print(f"* {project_dir}")
    else:
        print("No active projects")

    print("\n")


class DotRun:
    """
    A class for performing operations on a project directory
    """

    def __init__(self, workdir, env):
        """
        Based on the provided project path (default to the current directory),
        generate an ENVIRONMENT_PATH, and set the existing
        project_data on the object
        """

        if os.path.isfile("dotrun.toml"):
            with open("dotrun.toml") as settings_file:
                self.SETTINGS = toml.load(settings_file)
        else:
            print("ERROR: dotrun.toml not found in " + os.getcwd())
            sys.exit(1)

        self.WORKDIR = workdir
        self.env = os.environ.copy()
        self.env.update(self.SETTINGS.get("environment-variables", {}))
        self.env.update(env)

        # Check all env values are string format
        for key, value in self.env.items():
            self.env[key] = str(value)

        if not os.path.isfile("package.json"):
            print("ERROR: package.json not found in " + os.getcwd())
            sys.exit(1)

        self.project_data = _get_projects_data(PROJECTS_DATA_PATH).get(
            self.WORKDIR, {}
        )
        environment_dirname = (
            os.path.basename(self.WORKDIR)
            + "-"
            + md5(self.WORKDIR.encode("utf-8")).hexdigest()[:7]
        )
        self.ENVIRONMENT_PATH = os.path.join(
            os.environ["SNAP_USER_COMMON"], "environments", environment_dirname
        )
        cprint(f"- Using environment at {self.ENVIRONMENT_PATH}", "magenta")

        self.project_data["path"] = self.WORKDIR

    def install(self, force=False):
        """
        Install dependencies from pyproject.toml and package.json,
        if there have been any changes detected
        """

        if os.path.isfile("pyproject.toml"):
            self.install_poetry_dependencies(force=force)

        self.install_yarn_dependencies(force=force)

    def install_yarn_dependencies(self, force=False):
        """
        Install yarn dependencies if anything has changed
        """

        changes = False

        yarn_state = {"lock_hash": _get_file_hash("yarn.lock")}

        with open("package.json", "rb") as package_json:
            package_settings = json.load(package_json)
            yarn_state["dependencies"] = package_settings.get(
                "dependencies", {}
            )
            yarn_state["dependencies"].update(
                package_settings.get("devDependencies", {})
            )

        if not force:
            cprint(
                "- Checking dependencies in package.json ... ", "magenta", end=""
            )

            yarn_state["packages"] = self._get_yarn_packages()

            if self.project_data.get("yarn") == yarn_state:
                cprint("up to date", "magenta")
            else:
                cprint("changes detected", "magenta")
                changes = True
        else:
            cprint(
                "- Installing dependencies from package.json (forced)", "magenta"
            )

        if force or changes:
            self._call(["yarn", "install"])
            yarn_state["packages"] = self._get_yarn_packages()
            self.project_data["yarn"] = yarn_state
            _save_project_data(self.project_data, self.WORKDIR)

    def install_poetry_dependencies(self, force=False):
        """
        Install poetry dependencies if anything has changed
        """

        changes = False

        poetry_state = {"lock_hash": _get_file_hash("poetry.lock")}

        with open("pyproject.toml", "r") as pyproject_file:
            pyproject_settings = toml.load(pyproject_file)
            poetry_state["dependencies"] = pyproject_settings["tool"][
                "poetry"
            ]["dependencies"]
            poetry_state["dependencies"].update(
                pyproject_settings["tool"]["poetry"]["dev-dependencies"]
            )

        if not force:
            cprint(
                "- Checking dependencies in pyproject.toml ... ",
                "magenta",
                end="",
            )

            poetry_state["packages"] = self._get_poetry_packages()

            if self.project_data.get("poetry") == poetry_state:
                cprint("up to date", "magenta")
            else:
                changes = True
                cprint("changes detected", "magenta")
        else:
            cprint(
                "- Installing dependencies from pyproject.toml (forced)",
                "magenta",
            )

        if force or changes:
            self._call(["poetry", "install"])
            poetry_state["packages"] = self._get_poetry_packages()
            self.project_data["poetry"] = poetry_state
            _save_project_data(self.project_data, self.WORKDIR)

    def clean(self):
        """
        Clean all dotrun data from project
        """

        try:
            self._call(["yarn", "run", "clean"])
        except Exception as error:
            cprint(f"[ `yarn run clean` error: {error} ]", "red")

        cprint(
            f"\n- Removing project environment: {self.ENVIRONMENT_PATH}",
            "magenta",
        )
        shutil.rmtree(self.ENVIRONMENT_PATH, ignore_errors=True)
        _clear_project_data(self.WORKDIR)

    def exec(self, command):
        """
        Run a command in the environment
        """

        self._call(command)

    # Private functions

    def _call(self, commands):
        """
        Run a command within the python environment
        """

        try:
            if not os.path.isdir(self.ENVIRONMENT_PATH):
                cprint(f"- Creating new project environment\n", "magenta")
                cprint(
                    f"[ $ virtualenv {self.ENVIRONMENT_PATH} ]\n", "cyan"
                )
                subprocess.check_call(["virtualenv", self.ENVIRONMENT_PATH])

            # Set up environment for new virtualenv
            # (Basically do what's done in an `activate` script)
            self.env["VIRTUAL_ENV"] = self.ENVIRONMENT_PATH
            self.env[
                "PATH"
            ] = f"{self.ENVIRONMENT_PATH}/bin:{self.env['PATH']}"
            self.env.pop("PYTHONHOME", None)

            cprint(f"\n[ $ {' '.join(commands)} ]\n", "cyan")

            response = subprocess.check_call(
                commands, env=self.env, cwd=self.WORKDIR
            )
        except KeyboardInterrupt:
            cprint(
                f"\n\n[ `{' '.join(commands)}` cancelled - exiting ]",
                "cyan",
            )
            time.sleep(1)
            sys.exit(1)

        print("")

        return response

    def _get_poetry_packages(self):
        """
        Inspect the "site-packages" folder in the environment to
        list all eggs and wheels
        """

        installed_packages = ""
        packages_dir = f"{self.ENVIRONMENT_PATH}/lib/python3.6/site-packages"

        if os.path.isdir(packages_dir):
            paths = glob(packages_dir + "/*.egg-info") + glob(
                packages_dir + "/*.dist-info"
            )
            installed_packages = [os.path.basename(path) for path in paths]

        return installed_packages

    def _get_yarn_packages(self):
        """
        Inspect "node_modules" to list all packages and versions
        """

        package_jsons = glob(f"{self.WORKDIR}node_modules/*/package.json")
        packages = {}

        for package_json in package_jsons:
            with open(package_json, "r") as package_contents:
                package = json.load(package_contents)
                packages[package["name"]] = package["version"]

        return packages
