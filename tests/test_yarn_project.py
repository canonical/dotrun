# Standard library
import json
import os
import shutil
import unittest
from subprocess import check_output, STDOUT, CalledProcessError
from os.path import dirname, realpath


class TestYarnProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Switch into the project directory
        """

        # Change to yarn-project directory
        cls.orig_dir = os.getcwd()
        dotrun_dir = dirname(dirname(realpath(__file__)))
        os.chdir(f"{dotrun_dir}/tests/fixtures/yarn-project")

        # Save package.json contents
        with open("package.json") as package_json:
            cls.package_json_contents = package_json.read()

    @classmethod
    def tearDownClass(cls):
        """
        Switch back to the original directory
        """

        check_output(["dotrun", "clean"], stderr=STDOUT)

        # Restory package.json contents
        with open("package.json", "w") as package_json:
            package_json.write(cls.package_json_contents)

        os.chdir(cls.orig_dir)

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
        packages = json.loads(self.package_json_contents)

        with open("package.json", "w") as json_file:
            json.dump(packages, json_file)

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
        Check running `dotrun` again skips installing
        """

        # Change "concurrently" version
        packages = json.loads(self.package_json_contents)

        packages["dependencies"]["concurrently"] = "5.0.2"

        with open("package.json", "w") as package_json:
            json.dump(packages, package_json)

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

    def test_07_clean(self):
        """
        Check `dotrun clean` removes artifacts
        """

        self.assertTrue(os.path.isdir("node_modules"))
        self.assertTrue(os.path.isfile(".dotrun.json"))

        clean_output = check_output(
            ["dotrun", "clean"], stderr=STDOUT
        ).decode()

        self.assertIn("run clean", clean_output)
        self.assertFalse(os.path.isdir("node_modules"))
        self.assertFalse(os.path.isfile(".dotrun.json"))
