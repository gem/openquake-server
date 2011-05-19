# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2010-2011, GEM Foundation.
#
# OpenQuake is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# only, as published by the Free Software Foundation.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License version 3 for more details
# (a copy is included in the LICENSE file that accompanied this code).
#
# You should have received a copy of the GNU Lesser General Public License
# version 3 along with OpenQuake.  If not, see
# <http://www.gnu.org/licenses/lgpl-3.0.txt> for a copy of the LGPLv3 License.


"""
Unit tests for the geonode/mtapi/utils.py module.
"""


import os
import subprocess
import unittest

from geonode.mtapi.utils import is_process_running, run_cmd


class IsProcessRunningTestCase(unittest.TestCase):
    """Tests the behaviour of utils.is_process_running()."""

    def test_is_process_running(self):
        """The init process should be found."""
        self.assertTrue(is_process_running(1))

    def test_is_process_running_with_matching_pattern(self):
        """pid and name pattern should match the init process."""
        self.assertTrue(is_process_running(1, "init"))

    def test_is_process_running_with_non_matching_pattern(self):
        """
        pid is right but the name pattern does not match the init process.
        """
        self.assertFalse(is_process_running(1, "openquake"))

    def test_is_process_running_with_compound_command(self):
        """
        pid and name pattern should match a process whose command consists of
        multiple strings.
        """
        p = subprocess.Popen("sleep 5", shell=True)
        self.assertTrue(is_process_running(p.pid, "p 5"))


class RunCmdTestCase(unittest.TestCase):
    """Tests the behaviour of utils.run_cmd()."""

    def test_run_cmd_with_success(self):
        """Invoke a command without errors."""
        code, out, err = run_cmd(["echo", "-n", "Hello world!"])
        self.assertEqual(0, code)
        self.assertEqual("Hello world!", out)
        self.assertEqual("", err)

    def test_run_cmd_with_errors(self):
        """Invoke a command with errors."""
        try:
            code, out, err = run_cmd(["ls", "-AF", "/this/does/not/exist"])
        except Exception, e:
            self.assertEqual(
                "ls terminated with exit code: 2\nls: cannot access "
                "/this/does/not/exist: No such file or directory\n", e.args[0])
        else:
            raise Exception("exception not raised")

    def test_run_cmd_with_errors_and_ignore_exit_code(self):
        """Invoke a command with errors but ignore the exit code."""
        code, out, err = run_cmd(
            ["ls", "-AF", "/this/does/not/exist"], ignore_exit_code=True)
        self.assertEqual(2, code)
        self.assertEqual("", out)
        self.assertEqual("ls: cannot access /this/does/not/exist: No such "
                         "file or directory\n", err)
