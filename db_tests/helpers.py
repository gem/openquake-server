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


import math
import os
import random
import shutil

from geonode.mtapi.models import Input, OqJob, OqParams, Output, Upload
from geonode.mtapi import view_utils

from tests.helpers import TestMixin


class DbTestMixin(TestMixin):
    """Mixin class with various helper methods."""

    def setup_upload(self, dbkey=None):
        """Create an upload with associated inputs.

        :param integer dbkey: if set use the upload record with given db key.
        :returns: a :py:class:`geonode.mtapi.models.Upload` instance
        """
        if dbkey:
            [upload] = Upload.objects.filter(id=dbkey)
            return upload

        files = [
            ("gmpe_logic_tree.xml", "lt_gmpe"),
            ("small_exposure.xml", "exposure"),
            ("source_model1.xml", "source"),
            ("source_model2.xml", "source"),
            ("source_model_logic_tree.xml", "lt_source"),
            ("vulnerability.xml", "vulnerability")]
        upload = view_utils.prepare_upload()
        for file, type in files:
            path = os.path.join(upload.path, file)
            # This is equivalent to what the touch command does.
            open(path, "w+").close()
            input = Input(path=path, owner=upload.owner, input_type=type,
                          upload=upload)
            input.save()
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
        # This is like "rm -rf path"
        shutil.rmtree(upload.path, ignore_errors=True)
        if filesystem_only:
            return
        for input in upload.input_set.all():
            input.delete()
        upload.delete()

    def setup_classic_job(self, create_job_path=True, upload_id=None):
        """Create a classic job with associated upload and inputs.

        :param integer upload_id: if set use upload record with given db key.
        :param bool create_job_path: if set the path for the job will be
            created and captured in the job record
        :returns: a :py:class:`geonode.mtapi.models.OqJob` instance
        """
        upload = self.setup_upload(upload_id)
        oqp = OqParams()
        oqp.job_type = "classical"
        oqp.upload = upload
        oqp.region_grid_spacing = 0.01
        oqp.min_magnitude = 5.0
        oqp.investigation_time = 50.0
        oqp.component = "gmroti50"
        oqp.imt = "pga"
        oqp.truncation_type = "twosided"
        oqp.truncation_level = 3
        oqp.reference_vs30_value = 760
        oqp.imls = [
            0.005, 0.007, 0.0098, 0.0137, 0.0192, 0.0269, 0.0376, 0.0527,
            0.0738, 0.103, 0.145, 0.203, 0.284, 0.397, 0.556, 0.778]
        oqp.poes = [0.01, 0.10]
        oqp.realizations = 1
        from django.contrib.gis import geos
        oqp.region = geos.Polygon(
            ((-122.2, 38.0), (-121.7, 38.0), (-121.7, 37.5),
             (-122.2, 37.5), (-122.2, 38.0)))
        oqp.save()
        job = OqJob(oq_params=oqp, owner=upload.owner, job_type="classical")
        job.save()
        if create_job_path:
            job.path = os.path.join(upload.path, str(job.id))
            os.mkdir(job.path)
            os.chmod(job.path, 0777)
            job.save()
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

    def setup_output(self, job_to_use=None, output_type="hazard_map"):
        """Create an output object of the given type.

        :param job_to_use: if set use the passed
            :py:class:`geonode.mtapi.models.OqJob` instance as opposed to
            creating a new one.
        :param str output_type: map type, one of "hazard_map", "loss_map"
        :returns: a :py:class:`geonode.mtapi.models.Output` instance
        """
        job = job_to_use if job_to_use else self.setup_classic_job()
        output = Output(owner=job.owner, oq_job=job, output_type=output_type)
        output.path = self.touch(
            dir=os.path.join(job.path, "computed_output"), suffix=".xml",
            prefix="hzrd." if output_type == "hazard_map" else "loss.")
        output.save()
        return output

    def teardown_output(self, output, teardown_job=True, filesystem_only=True):
        """
        Tear down the file system (and potentially db) artefacts for the
        given output.

        :param output: the :py:class:`geonode.mtapi.models.Output` instance
            in question
        :param bool teardown_job: the associated job and its related artefacts
            shall be torn down as well.
        :param bool filesystem_only: if set the various database records will
            be left intact. This saves time and the test db will be
            dropped/recreated prior to the next db test suite run anyway.
        """
        job = output.oq_job
        if not filesystem_only:
            output.delete()
        if teardown_job:
            self.teardown_job(job, filesystem_only=filesystem_only)

    def add_shapefile_data(self, output):
        """Add shapefile data to the given output instance."""
        prefix = "hazard" if output.output_type == "hazard_map" else "loss"
        dirname = os.path.dirname(output.path)
        layer_name, _ = os.path.splitext(os.path.basename(output.path))
        layer_name = layer_name.replace(".", "-")
        dirname = os.path.join(dirname, "%s-shapefiles" % prefix)
        output.shapefile_path = os.path.join(dirname, "%s.shp" % layer_name)
        os.rename(self.touch(dir=dirname), output.shapefile_path)
        output.min_value = random.random()
        output.max_value = output.min_value * math.pi
        output.save()
        return output.shapefile_path
