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


import os
import subprocess
import tempfile

from django.conf import settings
from geonode.mtapi.models import OqUser, Upload


def dbn():
    """The name of the database to use."""
    return os.environ.get("OQ_MTAPI_DB", "openquake")


def prepare_upload(root=None):
    """Create a directory for the files, return `Upload` object.

    :returns: the :py:class:`geonode.mtapi.models.Upload` instance
        associated with this upload.
    """
    user = OqUser.objects.using(dbn()).filter(user_name="openquake")[0]
    root = root if root else settings.OQ_UPLOAD_DIR
    path = tempfile.mkdtemp(dir=root)
    os.chmod(path, 0777)
    upload = Upload(owner=user, path=path, status="pending", job_pid=0)
    upload.save(using=dbn())
    return upload


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
    process = subprocess.Popen(
        cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
    out, err = process.communicate()
    if process.returncode != 0 and not ignore_exit_code:
        error = ("%s terminated with exit code: %s\n%s"
                 % (cmds[0], process.returncode, err))
        raise Exception(error)
    return (process.returncode, out, err)


def is_process_running(pid, name_pattern=None):
    """Is the process with the given `pid` still running?

    :param int pid: the process ID (pid) to check
    :param str name_pattern: a string that must occur in the command of the
        process with the given `pid`.
    :returns: `True` if process is still running, `False` otherwise.
    """
    code, out, _ = run_cmd(["ps ax"], shell=True)
    if code != 0:
        return False
    #  PID TTY      STAT   TIME COMMAND
    #    1 ?        Ss     0:02 /sbin/init
    #    2 ?        S      0:00 [kthreadd]
    #    3 ?        S      0:07 [ksoftirqd/0]
    #26206 pts/17   Sl     0:54 evince postgresql-8.4.6-A4.pdf
    #26211 ?        Sl     0:00 /usr/lib/evince/evinced
    result = False
    pid = str(pid)
    # Only consider lines that contain the given pid.
    lines = [line for line in out.split('\n')[1:] if line.find(pid) > -1]
    for line in lines:
        line = line.strip()
        if not line:
            continue
        data = line.split()
        if data[0] != pid:
            continue
        if name_pattern:
            # Is the pattern present in the command the process at hand is
            # running?
            if " ".join(data[4:]).find(name_pattern) > -1:
                result = True
                break
        else:
            result = True
            break
    return result
