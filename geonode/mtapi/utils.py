#!/usr/bin/env python
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


"""Various utility functions used by the django API"""


import subprocess


def run_cmd(cmds, ignore_exit_code=False, shell=False):
    """Run the given command and return the exit code, stdout and stderr.

    :param list cmds: the strings that comprise the command to run
    :param bool ignore_exit_code: if `True` no `Exception` will be raised for
        non-zero command exit code.
    :param bool shell: this flag is simply passed through to `subprocess.Popen`
    :returns: an `(exit code, stdout, stderr)` triple
    :raises Exception: when the command terminates with a non-zero command
        exit code.
    """
    p = subprocess.Popen(
        cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
    out, err = p.communicate()
    if p.returncode != 0 and not ignore_exit_code:
        error = ("%s terminated with exit code: %s\n%s"
                 % (cmds[0], p.returncode, err))
        raise Exception(error)
    return (p.returncode, out, err)


def is_process_running(pid, name_pattern=None):
    """Is the process with the given `pid` still running?

    :param int pid: the process ID (pid) to check
    :param str name_pattern: a string that must occur in the command of the
        process with the given `pid`.
    :returns: `True` if process is still running, `False` otherwise.
    """
    code, out, err = run_cmd(["ps ax"], shell=True)
    if code != 0:
        return False
    #  PID TTY      STAT   TIME COMMAND
    #    1 ?        Ss     0:02 /sbin/init
    #    2 ?        S      0:00 [kthreadd]
    #    3 ?        S      0:07 [ksoftirqd/0]
    #26206 pts/17   Sl     0:54 evince postgresql-8.4.6-A4.pdf
    #26211 ?        Sl     0:00 /usr/lib/evince/evinced
    result = False
    for line in out.split('\n')[1:]:
        line = line.strip()
        if not line:
            continue
        data = line.split()
        if int(data[0]) != pid:
            continue
        if name_pattern:
            if data[4].find(name_pattern) > -1:
                result = True
                break
        else:
            result = True
            break
    return result
