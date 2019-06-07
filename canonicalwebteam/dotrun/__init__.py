# Standard library
import json
import os
import subprocess
from hashlib import md5
from glob import glob

# Packages
import toml


PROJECT_DATA_PATH = os.environ["SNAP_USER_COMMON"] + "/projects.json"
PROJECT_PATH = os.getcwd()
PROJECT_ID = (
    os.path.basename(PROJECT_PATH)
    + "-"
    + md5(PROJECT_PATH.encode("utf-8")).hexdigest()[:7]
)
ENVIRONMENT = os.environ["SNAP_USER_COMMON"] + "/" + PROJECT_ID


projects = {}

if os.path.isfile(PROJECT_DATA_PATH):
    print(f"- Reading from {PROJECT_DATA_PATH}")
    with open(PROJECT_DATA_PATH) as project_data_json:
        projects = json.load(project_data_json)


project = projects.get(PROJECT_PATH, {})


def call(command):
    """
    Run a command within the environment
    """

    if not os.path.isdir(ENVIRONMENT):
        print(f"\n[ Creating new project environment ]")
        print(f"[ $ virtualenv {ENVIRONMENT} ]\n")
        subprocess.check_call(["virtualenv", ENVIRONMENT])

    print(f"\n[ $ {command} ]\n")

    response = subprocess.check_call(
        ["bash", "-c", f". {ENVIRONMENT}/bin/activate; {command}"]
    )

    print("")

    return response


def _save(project):
    projects[PROJECT_PATH] = project

    with open(PROJECT_DATA_PATH, "w") as project_data_json:
        json.dump(projects, project_data_json)


def list_projects():
    print("[ Known projects ]\n")

    for project_name in projects.keys():
        print(f"* {project_name}")

    print("\n")


def _get_python_packages():
    installed_packages = ""
    packages_dir = f"{ENVIRONMENT}/lib/python3.6/site-packages"

    if os.path.isdir(packages_dir):
        paths = glob(packages_dir + "/*.egg-info") + glob(
            packages_dir + "/*.dist-info"
        )
        installed_packages = [os.path.basename(path) for path in paths]

    return installed_packages


def _get_lock_hash(filename):
    lock_hash = None

    if os.path.isfile(filename):
        lock_hash = md5()

        with open("poetry.lock", "rb") as lockfile:
            for chunk in iter(lambda: lockfile.read(4096), b""):
                lock_hash.update(chunk)

    return lock_hash.hexdigest()


def _get_yarn_packages():
    package_jsons = glob("node_modules/*/package.json")
    packages = {}

    for package_json in package_jsons:
        with open(package_json, "r") as package_contents:
            package = json.load(package_contents)
            packages[package["name"]] = package["version"]

    return packages


def install_yarn_dependencies():
    """
    Install yarn dependencies if anything has changed
    """

    print("- Checking Yarn dependencies ... ", end="")

    with open("package.json", "rb") as package_json:
        package_settings = json.load(package_json)
        yarn_dependencies = package_settings.get("dependencies", {})
        yarn_dependencies.update(package_settings.get("devDependencies", {}))

    yarn_lock_hash = _get_lock_hash("yarn.lock")

    if (
        project.get("yarn_dependencies") == yarn_dependencies
        and project.get("yarn_lock_hash") == yarn_lock_hash
        and project.get("yarn_packages") == _get_yarn_packages()
    ):
        print("up-to-date")
    else:
        print("changes detected")
        call("yarn install")
        project["yarn_dependencies"] = yarn_dependencies
        project["yarn_lock_hash"] = yarn_lock_hash
        project["yarn_packages"] = _get_yarn_packages()
        _save(project)


def install_poetry_dependencies():
    """
    Install poetry dependencies if anything has changed
    """

    print("- Checking Poetry dependencies ... ", end="")

    with open("pyproject.toml", "r") as pyproject_file:
        pyproject_settings = toml.load(pyproject_file)
        poetry_dependencies = pyproject_settings["tool"]["poetry"][
            "dependencies"
        ]
        poetry_dependencies.update(
            pyproject_settings["tool"]["poetry"]["dev-dependencies"]
        )

    poetry_lock_hash = _get_lock_hash("poetry.lock")

    if (
        project.get("poetry_dependencies") == poetry_dependencies
        and project.get("poetry_lock_hash") == poetry_lock_hash
        and project.get("python_packages") == _get_python_packages()
    ):
        print("up-to-date")
    else:
        print("changes detected")
        call("poetry install")
        project["poetry_dependencies"] = poetry_dependencies
        project["poetry_lock_hash"] = poetry_lock_hash
        project["python_packages"] = _get_python_packages()
        _save(project)


def serve():
    if os.path.isfile("pyproject.toml"):
        install_poetry_dependencies()

    install_yarn_dependencies()

    call("yarn run serve")
