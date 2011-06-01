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
database related unit tests for the geonode/mtapi/utils.py module.
"""


import os
import stat
import unittest

from geonode.mtapi.models import Upload
from geonode.mtapi.view_utils import prepare_upload


class PrepareUploadTestCase(unittest.TestCase):
    """Tests the behaviour of utils.prepare_upload()."""

    def test_prepare_upload(self):
        """
        `prepare_upload` returns a :py:class:`geonode.mtapi.models.Upload`
        instance. The latter's `path` must be a file system directory and have
        `0777` permissions.
        """
        upload = prepare_upload()
        self.assertTrue(isinstance(upload, Upload))
        info = os.stat(upload.path)
        self.assertTrue(stat.S_ISDIR(info.st_mode))
        self.assertEqual('0777', oct(stat.S_IMODE(info.st_mode)))
