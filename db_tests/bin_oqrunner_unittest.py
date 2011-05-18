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
database related unit tests for the bin/oqrunner.py module.
"""


import os
import shutil
import stat
import tempfile
import unittest

from geonode.mtapi import utils
from geonode.mtapi.models import OqJob, OqParams, OqUser, Upload
from bin.oqrunner import create_input_file_dir


class CreateInputFileDirTestCase(unittest.TestCase):
    """Tests the behaviour of oqrunner.create_input_file_dir()."""

    def setUp(self):
        [user] = OqUser.objects.using(
            utils.dbn()).filter(user_name="openquake")
        path = tempfile.mkdtemp()
        os.chmod(path, 0777)
        upload = Upload(owner=user, path=path, status="succeeded", job_pid=10)
        upload.save(using=utils.dbn())
        oqp = OqParams()
        oqp.job_type = "classical"
        oqp.upload = upload
        oqp.region_grid_spacing = 0.25
        oqp.min_magnitude = 7.6
        oqp.investigation_time = 50.0
        oqp.component = "average"
        oqp.imt = "pga"
        oqp.truncation_type = "none"
        oqp.truncation_level = 1.1
        oqp.reference_vs30_value = 1.2
        oqp.imls = [1.0, 1.1]
        oqp.poes = [2.0, 2.1]
        oqp.realizations = 3
        from django.contrib.gis.geos import GEOSGeometry
        oqp.region = GEOSGeometry(
            'POLYGON(( 10 10, 10 20, 20 20, 20 15, 10 10))')
        oqp.save(using=utils.dbn())
        self.job = OqJob(oq_params=oqp, owner=user, job_type="classical")
        self.job.save(using=utils.dbn())

    def tearDown(self):
        # Ignore all the rows in the test database. The latter will be
        # dropped/recreated prior to the next test run.
        shutil.rmtree(self.job.oq_params.upload.path, ignore_errors=True)

    def test_create_input_file_dir(self):
        """
        An <upload_path>/<jobid> directory will be created with 0777
        permissions.
        """
        config = {
            'db': 'openquake', 'host': 'localhost', 'jobid': self.job.id,
            'password': 'xxx', 'user': 'oq_uiapi_writer'}

        job = create_input_file_dir(config)
        info = os.stat(job.path)
        self.assertTrue(stat.S_ISDIR(info.st_mode))
        self.assertEqual("0777", oct(stat.S_IMODE(info.st_mode)))
        self.assertEqual(
            os.path.join(job.oq_params.upload.path, str(job.id)),
            job.path)
