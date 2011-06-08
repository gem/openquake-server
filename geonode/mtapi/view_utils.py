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


import decimal
import logging
import math
import os
import subprocess
import tempfile

from django.conf import settings
from geonode.mtapi.models import OqUser, Upload


def round_float(value):
    """
    Takes a float and rounds it to a fixed number of decimal places.

    This function makes uses of the built-in
    :py:method:`decimal.Decimal.quantize` to limit the precision.

    The 'round-half-even' algorithm is used for rounding.

    This should give us what can be considered 'safe' float values for
    geographical coordinates (to side-step precision and rounding errors).

    :type value: float

    :returns: the input value rounded to a hard-coded fixed number of decimal
    places
    """
    float_decimal_places = 7
    quantize_str = '0.' + '0' * float_decimal_places

    return float(
        decimal.Decimal(str(value)).quantize(
            decimal.Decimal(quantize_str),
            rounding=decimal.ROUND_HALF_EVEN))


def log_scale(lower_bound, upper_bound, n):
    """
    Generate a logarithmic scale with n elements. The input lower_bound and
    upper_bound values will be the first and last values (respectively) in the
    scale.

    NOTE: The final scale values will be rounded to a fixed number of decimal
    digits using the :py:function:`utils.round_float`.

    :param lower_bound: This will be the first value in the generated scale.
        lower_bound must be:
            * Greater than 0.0
    :param float upper_bound: This will be the last value in the generated
        scale. upper_bound must be:
            * Greater than 0.0
            * Greater than lower_bound
    :param int n: Number of elements in the scale. n must be at least 2.

    :returns: Logarithmic scale of n values starting with lower_bound and
        ending with upper_bound.
    """

    assert lower_bound > 0.0, "Lower bound must be > 0.0"
    assert upper_bound > 0.0, "Upper bound must be > 0.0"
    assert upper_bound > lower_bound, "Upper bound must be > lower_bound"
    assert n >= 2, "Scale must have at least 2 elements"

    delta = (1.0 / (n - 1)) * math.log10(upper_bound / lower_bound)

    return [round_float(lower_bound * math.pow(10, i * delta)) \
        for i in xrange(n)]


def prepare_upload(root=None):
    """Create a directory for the files, return `Upload` object.

    :returns: the :py:class:`geonode.mtapi.models.Upload` instance
        associated with this upload.
    """
    user = OqUser.objects.filter(user_name="openquake")[0]
    root = root if root else settings.OQ_UPLOAD_DIR
    path = tempfile.mkdtemp(dir=root)
    os.chmod(path, 0777)
    upload = Upload(owner=user, path=path, status="pending", job_pid=0)
    upload.save()
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
    # subprocess.Popen() wants to be fed strings only.
    for idx, cmd in enumerate(cmds):
        if not isinstance(cmd, basestring):
            cmds[idx] = str(cmd)

    process = subprocess.Popen(
        cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
    out, err = process.communicate()
    if process.returncode != 0:
        error = ("%s terminated with exit code: %s\n%s"
                 % (cmds, process.returncode, err))
        logging.error(error)
        if not ignore_exit_code:
            raise Exception(error)
    return (process.returncode, out, err)


def is_process_running(pid=None, pattern=None):
    """Is the process with the given `pid` still running?

    :param int pid: the process ID (pid) to check
    :param str pattern: a string that must occur in the command of the
        process with the given `pid`.
    :returns: `True` if process is still running, `False` otherwise.
    """
    assert pid or pattern, "Either 'pid' or 'pattern' must be set."
    result = False

    code, out, _ = run_cmd(["ps ax"], shell=True)
    if code != 0:
        return result

    #  PID TTY      STAT   TIME COMMAND
    #    1 ?        Ss     0:02 /sbin/init
    #    2 ?        S      0:00 [kthreadd]
    #    3 ?        S      0:07 [ksoftirqd/0]
    #26206 pts/17   Sl     0:54 evince postgresql-8.4.6-A4.pdf
    #26211 ?        Sl     0:00 /usr/lib/evince/evinced

    if pid:
        line_pattern = pid = str(pid)
    else:
        line_pattern = pattern

    # Only consider lines that contain the given pid or pattern.
    lines = [l for l in out.splitlines()[1:] if l.find(line_pattern) > -1]

    for line in lines:
        line = line.strip()
        if not line:
            continue
        data = line.split(None, 4)
        if pid and data[0] != pid:
            continue
        if pattern and data[4].find(pattern) < 0:
            continue
        result = True
        break
    return result
