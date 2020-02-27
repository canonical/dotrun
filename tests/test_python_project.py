# Standard library
import os
import pexpect
import shutil
import unittest
from glob import glob
from subprocess import check_output, STDOUT
from os.path import dirname, realpath

# Packages
import requests


class TestPythonProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Switch into the python-project project directory
        """

        cls.orig_dir = os.getcwd()
        dotrun_dir = dirname(dirname(realpath(__file__)))
        os.chdir(f"{dotrun_dir}/tests/fixtures/python-project")

    @classmethod
    def tearDownClass(cls):
        """
        Switch back to the original directory
        """

        check_output(["dotrun", "clean"], stderr=STDOUT)
        os.remove("requirements.txt")
        os.chdir(cls.orig_dir)

    def setUp(self):
        """
        Restore requirements.txt contents
        """

        shutil.copy("requirements.blueprint.txt", "requirements.txt")

    def test_01_first_run_installs(self):
        """
        Check it installs dependencies on first run
        """

        start_output = check_output(["dotrun"], stderr=STDOUT).decode()
        werkzeug = glob(".venv/**/Werkzeug-1.0.0.*/", recursive=True)
        switch = glob(".venv/**/switch-1.1.0.*/", recursive=True)

        self.assertIn("yarn install", start_output)
        self.assertIn("pip3 install", start_output)
        self.assertIn("Werkzeug-1.0.0", start_output)
        self.assertIn("switch-1.1.0", start_output)
        self.assertIn("starting...", start_output)
        self.assertEqual(len(werkzeug), 1)
        self.assertEqual(len(switch), 1)

    def test_02_second_run_skips_install(self):
        """
        Check running `dotrun` again skips installing
        """

        # Check we're in the expected state - with expected dependencies
        werkzeug = glob(".venv/**/Werkzeug-1.0.0.*/", recursive=True)
        switch = glob(".venv/**/switch-1.1.0.*/", recursive=True)
        self.assertEqual(len(werkzeug), 1)
        self.assertEqual(len(switch), 1)

        # Run again
        start_output = check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertNotIn("yarn install", start_output)
        self.assertNotIn("pip3 install", start_output)
        self.assertIn("starting...", start_output)

    def test_03_updating_dependencies(self):
        """
        Changing dependencies causes reinstall
        """

        # Check we're in the expected state - with expected dependencies
        switch_110 = glob(".venv/**/switch-1.1.0.*/", recursive=True)
        self.assertEqual(len(switch_110), 1)

        # Change "random word" version
        with open("requirements.txt") as requirements_file:
            requirements = requirements_file.read()

        requirements = requirements.replace("1.1.0", "1.0.4")

        with open("requirements.txt", "w") as requirements_file:
            requirements_file.write(requirements)

        # Should trigger rebuild
        start_output = check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertIn("pip3 install", start_output)
        self.assertIn("starting...", start_output)

        switch_104 = glob(".venv/**/switch-1.0.4.*/", recursive=True)
        self.assertEqual(len(switch_104), 1)
        self.assertFalse(os.path.exists(switch_110[0]))

    def test_04_removing_packages(self):
        """
        Check removing installed packages triggers rebuild
        """

        # Remove lodash, a sub-dependency of concurrently
        werkzeug = glob(".venv/**/Werkzeug-1.0.0.*/", recursive=True)
        self.assertEqual(len(werkzeug), 1)
        shutil.rmtree(werkzeug[0])

        # Should trigger rebuild
        start_output = check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertIn("pip3 install", start_output)
        self.assertIn("starting...", start_output)

        # Check the dependency came back
        werkzeug = glob(".venv/**/Werkzeug-1.0.0.*/", recursive=True)
        self.assertEqual(len(werkzeug), 1)

    def test_05_install_always_installs(self):
        """
        Check `dotrun install` reinstalls always
        """

        # A basic run shouldn't install
        start_output = check_output(["dotrun"], stderr=STDOUT).decode()

        self.assertNotIn("pip3 install", start_output)
        self.assertIn("starting...", start_output)

        # But "install" should
        install_output = check_output(
            ["dotrun", "install"], stderr=STDOUT
        ).decode()

        self.assertIn("pip3 install", install_output)

    def test_06_server(self):
        """
        Running `dotrun serve` should successfully serve
        a webpage on port 8111
        """

        # Start the server
        serve = pexpect.spawn("dotrun serve", timeout=5)
        serve.expect("http://localhost:8111")

        response = requests.get("http://localhost:8111")

        serve.sendcontrol("c")

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.text, "Serving...")

    def test_07_port_env(self):
        """
        Running `dotrun --env PORT=8999 serve` should successfully serve
        a webpage on port 8999
        """

        # Start the server
        serve = pexpect.spawn("dotrun --env PORT=8999 serve", timeout=5)
        serve.expect("http://localhost:8999")

        response = requests.get("http://localhost:8999")

        serve.sendcontrol("c")

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.text, "Serving...")

    def test_08_clean(self):
        """
        Check `dotrun clean` removes artifacts
        """

        self.assertTrue(os.path.isdir(".venv"))

        clean_output = check_output(
            ["dotrun", "clean"], stderr=STDOUT
        ).decode()

        self.assertIn("'clean' script not found", clean_output)
        self.assertFalse(os.path.isdir(".venv"))
