# Standard library
import json
import os
import shutil
import subprocess
import sys
import time
from glob import glob

# Packages
from dotenv import load_dotenv
from termcolor import cprint

# Local
from canonicalwebteam.dotrun.file_helpers import file_md5


class State:
    def __init__(self, filepath):
        """
        Manage a JSON object in a file,
        as you would a dictionary
        """

        self.filepath = filepath

    def __getitem__(self, key):
        if not os.path.isfile(self.filepath):
            return None

        with open(self.filepath) as state_file:
            return json.load(state_file).get(key)

    def __setitem__(self, key, value):
        if os.path.isfile(self.filepath):
            with open(self.filepath) as state_file:
                state = json.load(state_file)
        else:
            state = {}

        state[key] = value

        with open(self.filepath, "w") as state_file:
            return json.dump(state, state_file)


class Project:
    """
    A class for performing operations on a project directory
    """

    def __init__(self, path, env_extra):
        self.path = path
        self.statefile_path = f"{self.path}/.dotrun.json"
        self.state = State(self.statefile_path)
        self.env_extra = {}

        # Check all env values are string format
        for key, value in env_extra.items():
            self.env_extra[key] = str(value)

        if not os.path.isfile(os.path.join(f"{self.path}/package.json")):
            print(f"ERROR: package.json not found in {self.path}")
            sys.exit(1)

    def has_script(self, script_name):
        """
        Check if the project's package.json contains the named script
        """

        with open(f"{self.path}/package.json") as json_file:
            return script_name in json.load(json_file).get("scripts", {})

    def install(self, force=False):
        """
        Install dependencies from package.json,
        if there have been any changes detected
        """

        self._install_yarn_dependencies(force=force)

    def clean(self):
        """
        Clean all dotrun data from project
        """

        if self.has_script("clean"):
            self.exec(["yarn", "run", "clean"], exit_on_error=False)
        else:
            cprint(f"- No 'clean' script found in package.json", "magenta")

        if os.path.isfile(self.statefile_path):
            cprint(f"[ Removing `{self.statefile_path}` ]", "cyan")
            os.remove(self.statefile_path)

        if os.path.isdir("node_modules"):
            cprint(f"[ Removing node dependencies (`node_modules`) ]", "cyan")
            shutil.rmtree("node_modules")

    def exec(self, commands, exit_on_error=True):
        """
        Run commands in the environment
        """

        result = None
        load_dotenv(dotenv_path=f"{self.path}/.env")
        load_dotenv(dotenv_path=f"{self.path}/.env.local")
        env = os.environ
        env.update(self.env_extra)

        # This is kinda nuts, but adding this line to `.yarnrc` before
        # we run yarn is actually the only way
        # to avoid an error about access to /home/{user}/.npmrc
        snap_home = os.environ.get("SNAP_USER_DATA")
        if snap_home:
            with open(f"{snap_home}/.yarnrc", "w") as yarnconfig:
                yarnconfig.write("--no-default-rc true")

        try:
            cprint(f"\n[ $ {' '.join(commands)} ]\n", "cyan")

            result = subprocess.check_call(commands, env=env, cwd=self.path)
        except KeyboardInterrupt:
            cprint(
                f"\n\n[ `{' '.join(commands)}` cancelled - exiting ]", "cyan"
            )
            time.sleep(1)
        except subprocess.CalledProcessError as call_error:
            cprint(
                f"\n[ `{' '.join(commands)}` exited with an error status ]",
                "red",
            )

            if exit_on_error:
                sys.exit(call_error.returncode)

        print("")

        return result

    # Node dependencies

    def _get_yarn_state(self):
        """
        Save package.json, lockfile and installed dependencies state
        """

        # Get installed package versions
        with open(
            os.path.join(self.path, "package.json"), "rb"
        ) as package_json:
            package_settings = json.load(package_json)
            dependencies = package_settings.get("dependencies", {})
            dependencies.update(package_settings.get("devDependencies", {}))

        package_jsons = glob(f"{self.path}/node_modules/*/package.json")
        packages = {}

        # Read package.json dependencies
        for package_json in package_jsons:
            with open(package_json, "r") as package_contents:
                package = json.load(package_contents)
                packages[package["name"]] = package["version"]

        lock_hash = None
        if os.path.isfile(os.path.join(self.path, "yarn.lock")):
            lock_hash = file_md5(os.path.join(self.path, "yarn.lock"))

        return {
            "dependencies": dependencies,
            "installed_packages": packages,
            "lockfile_hash": lock_hash,
        }

    def _install_yarn_dependencies(self, force=False):
        """
        Install yarn dependencies if anything has changed
        """

        changes = False

        if not force:
            cprint("- Checking yarn dependencies ... ", "magenta", end="")
            current_state = self._get_yarn_state()
            previous_state = self.state["yarn"]
            changes = current_state != previous_state

        if changes or force:
            if changes:
                cprint("changes detected", "magenta")
            if force:
                cprint("- Installing yarn dependencies (forced)", "magenta")

            self.exec(["yarn", "install"])

            self.state["yarn"] = self._get_yarn_state()
        else:
            cprint("up to date", "magenta")

