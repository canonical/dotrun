# Standard library
import json
import os
import shutil
import subprocess
import sys
import time
from hashlib import md5
from glob import glob

# Packages
import toml
from termcolor import cprint

# Local
from canonicalwebteam.dotrun.file_helpers import file_md5


class ProjectData:
    """
    Class for interacting with saved metadata about a project
    """

    def __init__(
        self,
        path=None,
        data_dir=os.environ.get(
            "SNAP_USER_COMMON",
            os.path.join(os.environ["HOME"], ".config", "dotrun"),
        ),
    ):
        """
        Just ensure the data dir exists and set the projects.json path
        """

        # Ensure the data directory exists
        os.makedirs(data_dir, exist_ok=True)

        self.path = path
        self.json_path = os.path.join(data_dir, "projects.json")
        self.virtualenv_path = os.path.join(
            data_dir,
            "environment",
            os.path.basename(data_dir)
            + "-"
            + md5(data_dir.encode("utf-8")).hexdigest()[:7],
        )

        # Create python environment
        if not os.path.isdir(self.virtualenv_path):
            cprint(f"- Creating new project environment\n", "magenta")
            cprint(f"[ $ virtualenv {self.virtualenv_path} ]\n", "cyan")
            subprocess.check_call(["virtualenv", self.virtualenv_path])
        else:
            cprint(f"- Using environment at {self.virtualenv_path}", "magenta")

        self.set("virtualenv_path", self.virtualenv_path)

    def set(self, key, value):
        """
        Set a property about the project
        """

        projects_data = self.all()

        if self.path in projects_data:
            projects_data[self.path][key] = value
        else:
            projects_data[self.path] = {key: value}

        self._save(projects_data)

    def get(self, key):
        """
        Retrieve a property about this project
        """

        project_data = self.all()[self.path]

        return project_data.get(key)

    def clean(self):
        """
        Clear the data for project_dir
        """

        cprint(f"\n- Removing virtualenv: {self.virtualenv_path}", "magenta")
        shutil.rmtree(self.virtualenv_path, ignore_errors=True)

        projects_data = self.all()
        projects_data.pop(self.path, None)

        with open(self.json_path, "w") as json_handle:
            cprint(f"- Removing {self.path} from {self.json_path}", "magenta")
            json.dump(projects_data, json_handle)

    def all(self):
        """
        Read the JSON file in the filepath
        """

        projects_data = {}

        if os.path.isfile(self.json_path):
            cprint(f"- Reading from {self.json_path}", "magenta")
            with open(self.json_path) as project_data_json:
                projects_data = json.load(project_data_json)

        return projects_data

    # Private methods

    def _save(self, data):
        """
        Save settings for this project to the JSON file
        """

        projects_data = self.all()
        projects_data[self.path] = data

        self._save_all(projects_data)

    def _save_all(self, projects_data):
        """
        Save settings for all projects to the JSON file
        """

        with open(self.json_path, "w") as json_handle:
            cprint(f"- Saving to {self.json_path}", "magenta")
            json.dump(projects_data, json_handle)


class DotRun:
    """
    A class for performing operations on a project directory
    using an encapsulated Python virtualenv
    """

    def __init__(self, project_data, env):
        config_filepath = os.path.join(project_data.path, "dotrun.toml")

        if os.path.isfile(config_filepath):
            with open(config_filepath) as settings_file:
                self.settings = toml.load(settings_file)
        else:
            print("ERROR: dotrun.toml not found in " + project_data.path)
            sys.exit(1)

        self.project_data = project_data
        self.env = os.environ.copy()
        self.env.update(self.settings.get("environment-variables", {}))
        self.env.update(env)

        # Check all env values are string format
        for key, value in self.env.items():
            self.env[key] = str(value)

        if not os.path.isfile(os.path.join(project_data.path, "package.json")):
            print("ERROR: package.json not found in " + project_data.path)
            sys.exit(1)

    def install(self, force=False):
        """
        Install dependencies from pyproject.toml and package.json,
        if there have been any changes detected
        """

        if os.path.isfile(
            os.path.join(self.project_data.path, "pyproject.toml")
        ):
            self.install_poetry_dependencies(force=force)

        self.install_yarn_dependencies(force=force)

    def install_yarn_dependencies(self, force=False):
        """
        Install yarn dependencies if anything has changed
        """

        changes = False
        lock_path = os.path.join(self.project_data.path, "yarn.lock")
        yarn_state = {"lock_hash": file_md5(lock_path)}

        with open(
            os.path.join(self.project_data.path, "package.json"), "rb"
        ) as package_json:
            package_settings = json.load(package_json)
            yarn_state["dependencies"] = package_settings.get(
                "dependencies", {}
            )
            yarn_state["dependencies"].update(
                package_settings.get("devDependencies", {})
            )

        if not force:
            cprint(
                "- Checking dependencies in package.json ... ",
                "magenta",
                end="",
            )

            yarn_state["packages"] = self._get_yarn_packages()

            if self.project_data.get("yarn") == yarn_state:
                cprint("up to date", "magenta")
            else:
                cprint("changes detected", "magenta")
                changes = True
        else:
            cprint(
                "- Installing dependencies from package.json (forced)",
                "magenta",
            )

        if force or changes:
            self._call(["yarn", "--no-default-rc", "install"])
            yarn_state["packages"] = self._get_yarn_packages()
            self.project_data.set("yarn", yarn_state)

    def install_poetry_dependencies(self, force=False):
        """
        Install poetry dependencies if anything has changed
        """

        changes = False
        lock_path = os.path.join(self.project_data.path, "poetry.lock")
        poetry_state = {"lock_hash": file_md5(lock_path)}

        with open(
            os.path.join(self.project_data.path, "pyproject.toml"), "r"
        ) as pyproject_file:
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
            self.project_data.set("poetry", poetry_state)

    def clean(self):
        """
        Clean all dotrun data from project
        """

        try:
            self._call(["yarn", "--no-default-rc", "run", "clean"])
        except Exception as error:
            cprint(
                f"[ `yarn --no-default-rc run clean` error: {error} ]", "red"
            )

        self.project_data.clean()

    def serve(self, watch=False):
        """
        Run "yarn run serve", and also run "yarn run watch" alongside it
        """

        # Run watcher, if required
        if watch:
            cprint(f"- Adding watcher", "magenta")
            self._call(
                ["yarn", "--no-default-rc", "run", "serve"],
                background_commands=[
                    "yarn",
                    "--no-default-rc",
                    "run",
                    "watch",
                ],
            )
        else:
            self._call(["yarn", "--no-default-rc", "run", "serve"])

    def exec(self, command):
        """
        Run a command in the environment
        """

        self._call(command)

    # Private functions

    def _call(self, commands, background_commands=None):
        """
        Run a command within the python environment. Optionally run another
        command in the background. The background command will be
        terminated when the foreground command terminates.
        """

        response = None

        try:
            # Set up environment for new virtualenv
            # (Basically do what's done in an `activate` script)
            self.env["VIRTUAL_ENV"] = self.project_data.virtualenv_path
            self.env["PATH"] = (
                self.project_data.virtualenv_path + "/bin:" + self.env["PATH"]
            )
            self.env.pop("PYTHONHOME", None)

            if background_commands:
                background_process = subprocess.Popen(
                    background_commands,
                    env=self.env,
                    cwd=self.project_data.path,
                )
                cprint(
                    f"\n[ $ {' '.join(background_commands)} & "
                    f"{' '.join(commands)} ]\n",
                    "cyan",
                )
            else:
                cprint(f"\n[ $ {' '.join(commands)} ]\n", "cyan")

            response = subprocess.check_call(
                commands, env=self.env, cwd=self.project_data.path
            )

            if background_commands:
                cprint(
                    f"\n\n[ Terminating `{' '.join(background_commands)}` ]",
                    "cyan",
                )
                background_process.terminate()
        except KeyboardInterrupt:
            if background_commands:
                cprint(
                    f"\n\n[ Terminating `{' '.join(background_commands)}` ]",
                    "cyan",
                )
                background_process.terminate()

            cprint(
                f"\n\n[ `{' '.join(commands)}` cancelled - exiting ]", "cyan"
            )
            time.sleep(1)

        print("")

        return response

    def _get_poetry_packages(self):
        """
        Inspect the "site-packages" folder in the environment to
        list all eggs and wheels
        """

        installed_packages = ""
        packages_dir = (
            self.project_data.virtualenv_path + "/lib/python3.6/site-packages"
        )

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

        package_jsons = glob(
            f"{self.project_data.path}node_modules/*/package.json"
        )
        packages = {}

        for package_json in package_jsons:
            with open(package_json, "r") as package_contents:
                package = json.load(package_contents)
                packages[package["name"]] = package["version"]

        return packages
