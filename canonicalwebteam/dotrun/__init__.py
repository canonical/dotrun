# Standard library
import json
import os
import subprocess
from hashlib import md5
from glob import glob

# Packages
import toml


PROJECTS_DATA_PATH = os.environ["SNAP_USER_COMMON"] + "/projects.json"


def _get_projects_data(filepath):
    """
    Read the JSON file in the filepath
    """

    projects_data = {}

    if os.path.isfile(filepath):
        print(f"- Reading from {filepath}")
        with open(filepath) as project_data_json:
            projects_data = json.load(project_data_json)

    return projects_data


def _save_project_data(project_data, project_id):
    """
    Save the settings for a project to the PROJECT_DATA_PATH JSON file
    """

    projects_data = _get_projects_data(PROJECTS_DATA_PATH)
    projects_data[project_id] = project_data

    with open(PROJECTS_DATA_PATH, "w") as projects_data_json:
        print(f"- Saving to {PROJECTS_DATA_PATH}")
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

    print("[ Known projects ]\n")

    for project_name in _get_projects_data(PROJECTS_DATA_PATH).keys():
        print(f"* {project_name}")

    print("\n")


class DotRun:
    """
    A class for performing operations on a project directory
    """

    def __init__(
        self,
        project_path=os.getcwd(),
        projects_data=_get_projects_data(PROJECTS_DATA_PATH),
    ):
        """
        Based on the provided project path (default to the current directory),
        generate a PROJECT_ID, an ENVIRONMENT_PATH, and set the existing
        project_data on the object
        """

        self.PROJECT_PATH = os.path.abspath(project_path)
        self.PROJECT_ID = (
            os.path.basename(self.PROJECT_PATH)
            + "-"
            + md5(self.PROJECT_PATH.encode("utf-8")).hexdigest()[:7]
        )
        self.ENVIRONMENT_PATH = (
            os.environ["SNAP_USER_COMMON"] + "/environments/" + self.PROJECT_ID
        )
        self.project_data = projects_data.get(self.PROJECT_ID, {})

    def _call(self, command):
        """
        Run a command within the environment
        """

        if not os.path.isdir(self.ENVIRONMENT_PATH):
            print(f"\n[ Creating new project environment ]")
            print(
                f"[ $ virtualenv --system-site-packages {self.ENVIRONMENT_PATH} ]\n"
            )
            subprocess.check_call(["virtualenv", self.ENVIRONMENT_PATH])

        print(f"\n[ $ {command} ]\n")

        response = subprocess.check_call(
            [
                "bash",
                "-c",
                f". {self.ENVIRONMENT_PATH}/bin/activate; {command}",
            ]
        )

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

        package_jsons = glob(f"{self.PROJECT_PATH}node_modules/*/package.json")
        packages = {}

        for package_json in package_jsons:
            with open(package_json, "r") as package_contents:
                package = json.load(package_contents)
                packages[package["name"]] = package["version"]

        return packages

    def install_yarn_dependencies(self):
        """
        Install yarn dependencies if anything has changed
        """

        print("- Checking Yarn dependencies ... ", end="")

        yarn_state = {
            "packages": self._get_yarn_packages(),
            "lock_hash": _get_file_hash("yarn.lock"),
        }

        with open("package.json", "rb") as package_json:
            package_settings = json.load(package_json)
            yarn_state["dependencies"] = package_settings.get(
                "dependencies", {}
            )
            yarn_state["dependencies"].update(
                package_settings.get("devDependencies", {})
            )

        if self.project_data.get("yarn") == yarn_state:
            print("up-to-date")
        else:
            print("changes detected")
            self._call("yarn install")
            yarn_state["packages"] = self._get_yarn_packages()
            self.project_data["yarn"] = yarn_state
            _save_project_data(self.project_data, self.PROJECT_ID)

    def install_poetry_dependencies(self):
        """
        Install poetry dependencies if anything has changed
        """

        print("- Checking Poetry dependencies ... ", end="")

        poetry_state = {
            "packages": self._get_poetry_packages(),
            "lock_hash": _get_file_hash("poetry.lock"),
        }

        with open("pyproject.toml", "r") as pyproject_file:
            pyproject_settings = toml.load(pyproject_file)
            poetry_state["dependencies"] = pyproject_settings["tool"][
                "poetry"
            ]["dependencies"]
            poetry_state["dependencies"].update(
                pyproject_settings["tool"]["poetry"]["dev-dependencies"]
            )

        if self.project_data.get("poetry") == poetry_state:
            print("up-to-date")
        else:
            print("changes detected")
            self._call("poetry install")
            poetry_state["packages"] = self._get_poetry_packages()
            self.project_data["poetry"] = poetry_state
            _save_project_data(self.project_data, self.PROJECT_ID)

    def serve(self):
        """
        First install any necessary dependencies, then
        run "yarn run serve" to run the "serve" script in package.json
        """

        if os.path.isfile("pyproject.toml"):
            self.install_poetry_dependencies()

        self.install_yarn_dependencies()

        self._call("yarn run serve")
