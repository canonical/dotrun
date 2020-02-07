import os
import subprocess
import unittest
from os.path import dirname, realpath


class TestEmptyProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Switch into the project directory
        """

        cls.orig_dir = os.getcwd()
        dotrun_dir = dirname(dirname(realpath(__file__)))
        os.chdir(f"{dotrun_dir}/tests/fixtures/empty-project")

    @classmethod
    def tearDownClass(cls):
        """
        Switch back to the original directory
        """

        os.chdir(cls.orig_dir)

    def test_help(self):
        """
        Check --help works and outputs some expected help content
        """

        help_output = subprocess.check_output(["dotrun", "--help"]).decode()
        self.maxDiff = None
        self.assertIn("--help", help_output)
        self.assertIn("usage".lower(), help_output.lower())
        self.assertIn("dotrun", help_output)

    def test_no_package_json(self):
        """
        Check we get an error if there's no package.json
        """

        with self.assertRaises(subprocess.CalledProcessError) as context:
            subprocess.check_output(["dotrun"])

        self.assertEqual(context.exception.returncode, 1)
        self.assertIn('package.json', context.exception.output.decode())
