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


import subprocess
import sys
import time
import unittest

from geonode.mtapi.view_utils import is_process_running, log_scale, run_cmd


class IsProcessRunningTestCase(unittest.TestCase):
    """Tests the behaviour of utils.is_process_running()."""

    def test_is_process_running(self):
        """The init process should be found."""
        self.assertTrue(is_process_running(1))

    def test_is_process_running_with_matching_pattern(self):
        """pid and name pattern should match the init process."""
        if sys.platform == "darwin":
            self.assertTrue(is_process_running(1, "launchd"))
        else:
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

    def test_is_process_running_with_no_pid(self):
        """
        The name pattern should match a process even though no pid is given.
        """
        the_time = str(time.time())
        subprocess.Popen("sleep 5; echo %s >/dev/null" % the_time, shell=True)
        self.assertTrue(is_process_running(pattern=the_time))

    def test_is_process_running_with_no_pid_and_multi_match(self):
        """
        The name pattern should match in case where we have multiple process
        and no pid is given.
        """
        the_time = str(time.time())
        subprocess.Popen("sleep 5; echo %s >/dev/null" % the_time, shell=True)
        subprocess.Popen("sleep 6; echo %s >/dev/null" % the_time, shell=True)
        self.assertTrue(is_process_running(pattern=the_time))

    def test_is_process_running_with_neither_pid_nor_pattern(self):
        """
        One or both parameters must be passed. Otherwise an AssertionError is
        raised.
        """
        self.assertRaises(AssertionError, is_process_running)


class RunCmdTestCase(unittest.TestCase):
    """Tests the behaviour of utils.run_cmd()."""

    def test_run_cmd_with_success(self):
        """Invoke a command without errors."""
        code, out, err = run_cmd(["echo", "-n", "Hello world!"])
        self.assertEqual(0, code)
        self.assertEqual("Hello world!", out)
        self.assertEqual("", err)

    def test_run_cmd_with_errors(self):
        """
        Invoke a command with errors.

        This is handled in a slightly diferent way depending on the platform.

        In Linux, the command we will test is considered a 'misuse of shell
        built-ins' resulting in a exit code 2, according to this source:
        http://tldp.org/LDP/abs/html/exitcodes.html

        However, OSX considers this be a general error and returns an exit code
        of 1. Also, the actual error message is slightly different.
        """
        if sys.platform == "darwin":
            expected_msg = (
                "['ls', '-AF', '/this/does/not/exist'] terminated with "
                "exit code: 1\nls: /this/does/not/exist: No "
                "such file or directory\n")
        else:
            expected_msg = (
                "['ls', '-AF', '/this/does/not/exist'] terminated with "
                "exit code: 2\nls: cannot access /this/does/not/exist: No "
                "such file or directory\n")

        try:
            code, out, err = run_cmd(["ls", "-AF", "/this/does/not/exist"])
        except Exception, e:
            self.assertEqual(expected_msg, e.args[0])
        else:
            raise Exception("exception not raised")

    def test_run_cmd_with_errors_and_ignore_exit_code(self):
        """Invoke a command with errors but ignore the exit code."""
        if sys.platform == "darwin":
            expected_code = 1
            expected_msg = \
                "ls: /this/does/not/exist: No such file or directory\n"
        else:
            expected_code = 2
            expected_msg = (
                "ls: cannot access /this/does/not/exist: No such "
                "file or directory\n")

        code, out, err = run_cmd(
            ["ls", "-AF", "/this/does/not/exist"], ignore_exit_code=True)
        self.assertEqual(expected_code, code)
        self.assertEqual("", out)
        self.assertEqual(expected_msg, err)


class ScalesTestCase(unittest.TestCase):
    """
    This test suite exercise the number scale generation in the
    :py:module:`utils` module.
    """

    def test_log_scale(self):
        lb = 0.060256
        ub = 9.780226
        n = 10

        expected_scale = [
            0.060255999999999997, 0.1060705, 0.1867192, 0.32868750000000002,
            0.57859870000000002, 1.0185251, 1.7929411, 3.1561694999999999,
            5.5559022999999996, 9.7802260000000008]

        scale = log_scale(lb, ub, n)

        # the first and last values in the scale should be equal to
        # the lower_bound and upper_bound, respectively
        self.assertEqual(lb, scale[0])
        self.assertEqual(ub, scale[-1])

        self.assertEqual(expected_scale, scale)

    def test_log_scale_raises_when_n_lt_2(self):
        """
        This test ensures that :py:function:`utils.log_scale` raises
        errors when 'n' is less than two ('n' indicates the length of the
        generated scale).
        """
        # args are in the order: lower_bound, upper_bound, n (num of elements)
        self.assertRaises(AssertionError, log_scale, 0.01, 0.1, 1)

    def test_log_scale_raises_when_lb_is_0(self):
        """
        This test ensures that :py:function:`utils.log_scale` raises
        errors when lower bound is 0.0.
        """
        self.assertRaises(AssertionError, log_scale, 0, 3.14, 10)

    def test_log_scale_raises_when_ub_is_0(self):
        """
        This test ensures that :py:function:`utils.log_scale` raises
        errors when upper bound is 0.0.
        """
        self.assertRaises(AssertionError, log_scale, 0.1, 0, 10)

    def test_log_scale_raises_when_bounds_are_0(self):
        """
        This test ensures that :py:function:`utils.log_scale` raises
        errors when lower bound and upper bound are both 0.0.
        """
        self.assertRaises(AssertionError, log_scale, 0, 0, 10)

    def test_log_scale_raises_when_lb_gt_ub(self):
        """
        This test ensures that :py:function:`utils.log_scale` raises
        errors when lower bound > the upper bound.
        """
        self.assertRaises(AssertionError, log_scale, 0.1, 0.01, 10)

    def test_log_scale_raises_when_lb_eq_ub(self):
        """
        This test ensures that :py:function:`utils.log_scale` raises
        errors when lower bound == upper bound
        """
        self.assertRaises(AssertionError, log_scale, 0.1, 0.1, 10)
