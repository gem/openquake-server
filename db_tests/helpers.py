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
Helper classes/functions needed across multiple database related unit tests.
"""


import os
import shutil

from geonode.mtapi import utils
from geonode.mtapi.models import Input, OqJob, OqParams


class DbTestMixin(object):
    """Tests the behaviour of oqrunner.create_input_file_dir()."""

    def setup_upload(self):
        """Create an upload with associated inputs.

        :returns: a :py:class:`geonode.mtapi.models.Upload` instance
        """
        files = [
            ("gmpe_logic_tree.xml", "lt_gmpe"),
            ("small_exposure.xml", "exposure"),
            ("source_model1.xml", "source"),
            ("source_model2.xml", "source"),
            ("source_model_logic_tree.xml", "lt_source"),
            ("vulnerability.xml", "vulnerability")]
        upload = utils.prepare_upload("/tmp")
        for file, type in files:
            path = os.path.join(upload.path, file)
            open(path, "w+").close()
            input = Input(path=path, owner=upload.owner, input_type=type,
                          upload=upload)
            input.save(using=utils.dbn())
        return upload

    def teardown_upload(self, upload, filesystem_only=True):
        """
        Tear down the file system (and potentially db) artefacts for the
        given upload.

        :param upload: the :py:class:`geonode.mtapi.models.Upload` instance
            in question
        :param bool filesystem_only: if set the upload/input database records
            will be left intact. This saves time and the test db will be
            dropped/recreated prior to the next db test suite run anyway.
        """
        shutil.rmtree(upload.path, ignore_errors=True)
        if filesystem_only:
            return
        for input in upload.input_set.all():
            input.delete()
        upload.delete()

    def setup_classic_job(self, create_job_path=True):
        """Create a classic job with associated upload and inputs.

        :param bool create_job_path: if set the path for the job will be
            created and captured in the job record
        :returns: a :py:class:`geonode.mtapi.models.OqJob` instance
        """
        upload = self.setup_upload()
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
        job = OqJob(oq_params=oqp, owner=upload.owner, job_type="classical")
        job.save(using=utils.dbn())
        if create_job_path:
            job.path = os.path.join(upload.path, str(job.id))
            os.mkdir(job.path)
            os.chmod(job.path, 0777)
            job.save(using=utils.dbn())
        return job

    def teardown_job(self, job, filesystem_only=True):
        """
        Tear down the file system (and potentially db) artefacts for the
        given job.

        :param job: the :py:class:`geonode.mtapi.models.OqJob` instance
            in question
        :param bool filesystem_only: if set the oq_job/oq_param/upload/input
            database records will be left intact. This saves time and the test
            db will be dropped/recreated prior to the next db test suite run
            anyway.
        """
        oqp = job.oq_params
        self.teardown_upload(oqp.upload, filesystem_only=filesystem_only)
        if filesystem_only:
            return
        job.delete()
        oqp.delete()
