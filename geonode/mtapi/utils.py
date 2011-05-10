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


def run_cmd(cmds, ignore_exit_code=False):
    """Run the given command and return the exit code, stdout and stderr.

    :param list cmds: the strings that comprise the command to run
    :param bool ignore_exit_code: if `True` no `Exception` will be raised for
        non-zero command exit code.
    :returns: an `(exit code, stdout, stderr)` triple
    :raises Exception: when the command terminates with a non-zero command
        exit code.
    """
    p = subprocess.Popen(
        cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0 and not ignore_exit_code:
        error = ("%s terminated with exit code: %s\n%s"
                 % (cmds[0], p.returncode, err))
        raise Exception(error)
    return (p.returncode, out, err)
