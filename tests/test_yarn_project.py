# Standard library
import json
import os
import pexpect
import shutil
import unittest
from subprocess import check_output, STDOUT, CalledProcessError
from os.path import dirname, realpath


class TestYarnProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Switch into the yarn-project project directory
        """

        cls.orig_dir = os.getcwd()
        dotrun_dir = dirname(dirname(realpath(__file__)))
        os.chdir(f"{dotrun_dir}/tests/fixtures/yarn-project")

    @classmethod
    def tearDownClass(cls):
        """
        Switch back to the original directory
        """

        check_output(["dotrun", "clean"], stderr=STDOUT)
        os.remove("package.json")
        os.chdir(cls.orig_dir)

    def setUp(self):
        """
        Restore package.json contents
        """

        shutil.copy("package.blueprint.json", "package.json")

    def test_01_first_run_installs(self):
        """
        Check it installs dependencies on first run
        """

        start_output = check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertIn("yarn install", start_output)
        self.assertIn("Build: alpha", start_output)
        self.assertIn("Serving: omega", start_output)
        self.assertTrue(os.path.isdir("node_modules/concurrently"))

        # Check concurrently version
        with open("node_modules/concurrently/package.json") as json_file:
            concurrently_package = json.load(json_file)

        self.assertIn("5.1.0", concurrently_package["version"])

    def test_02_second_run_skips_install(self):
        """
        Check running `dotrun` again skips installing
        """

        # Simply reformatting package.json should have no effect
        with open("package.json") as json_file:
            json_content = json.load(json_file)

        with open("package.json", "w") as json_file:
            json.dump(json_content, json_file)

        # Check we're in the expected state - with expected dependencies
        self.assertTrue(os.path.isdir("node_modules/concurrently"))

        with open("node_modules/concurrently/package.json") as json_file:
            concurrently_package = json.load(json_file)

        self.assertIn("5.1.0", concurrently_package["version"])

        # Run again
        start_output = check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertNotIn("yarn install", start_output)
        self.assertIn("Build: alpha", start_output)
        self.assertIn("Serving: omega", start_output)

    def test_03_updating_dependencies(self):
        """
        Updating dependencies causes reinstallation
        """

        # Change "concurrently" version
        with open("package.json") as json_file:
            json_content = json.load(json_file)

        json_content["dependencies"]["concurrently"] = "5.0.2"

        with open("package.json", "w") as package_json:
            json.dump(json_content, package_json)

        # Should trigger rebuild
        start_output = check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertIn("yarn install", start_output)
        self.assertIn("Build: alpha", start_output)
        self.assertIn("Serving: omega", start_output)

        with open("node_modules/concurrently/package.json") as json_file:
            concurrently_package = json.load(json_file)

        self.assertIn("5.0.2", concurrently_package["version"])

    def test_04_removing_packages(self):
        """
        Check removing installed packages triggers rebuild
        """

        # Remove lodash, a sub-dependency of concurrently
        shutil.rmtree("node_modules")

        # Should trigger rebuild
        start_output = check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertIn("yarn install", start_output)
        self.assertIn("Build: alpha", start_output)
        self.assertIn("Serving: omega", start_output)

    def test_05_install_always_installs(self):
        """
        Check `dotrun install` reinstalls always
        """

        # A basic run shouldn't install
        start_output = check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertNotIn("yarn install", start_output)
        self.assertIn("Build: alpha", start_output)
        self.assertIn("Serving: omega", start_output)

        # But "install" should
        install_output = check_output(
            ["dotrun", "install"], stderr=STDOUT
        ).decode()

        self.assertIn("yarn install", install_output)

    def test_06_failing_script(self):
        """
        Check running a failing script returns an error code
        """

        with self.assertRaises(CalledProcessError) as context:
            check_output(["dotrun", "fail"], stderr=STDOUT).decode()

        self.assertIn("Failed", context.exception.output.decode())
        self.assertEqual(context.exception.returncode, 26)

    def test_07_error_if_missing_start_script(self):
        """
        Running `dotrun` errors if no `start` script,
        and prints usage
        """

        # First, remove the "start" script from package.json
        with open("package.json") as json_file:
            json_content = json.load(json_file)

        del json_content["scripts"]["start"]

        with open("package.json", "w") as json_file:
            json.dump(json_content, json_file)

        # Now check `dotrun` fails
        with self.assertRaises(CalledProcessError) as context:
            check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertIn(
            "`start` script not found", context.exception.output.decode()
        )

    def test_08_chained_commands(self):
        """
        Check chained '&&'  yarn commands inside package.json
        succeed without complaining about .npmrc
        """

        chain = pexpect.spawn("dotrun chain", timeout=10)
        chain.expect(pexpect.EOF)
        chain.close()

        self.assertEqual(chain.exitstatus, 0)

    def test_09_clean(self):
        """
        Check `dotrun clean` removes artifacts
        """

        self.assertTrue(os.path.isdir("node_modules"))
        self.assertTrue(os.path.isfile(".dotrun.json"))

        clean_output = check_output(
            ["dotrun", "clean"], stderr=STDOUT
        ).decode()

        self.assertIn("'clean' script not found", clean_output)
        self.assertFalse(os.path.isdir("node_modules"))
        self.assertFalse(os.path.isfile(".dotrun.json"))
