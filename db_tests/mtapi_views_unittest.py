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
database related unit tests for the geonode/mtapi/views.py module.
"""


import unittest

from geonode.mtapi.models import OqJob
from geonode.mtapi.views import prepare_job

from db_tests.helpers import DbTestMixin


class PrepareJobTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of views.prepare_job()."""

    def test_prepare_upload(self):
        """
        `prepare_job` returns a :py:class:`geonode.mtapi.models.OqJob`
        instance. The latter's `oq_params` property refers to the correct
        upload record.
        """
        upload = self.setup_upload()
        post_params = {
            "model":"openquake.calculationparams",
            "upload": upload.id,
            "fields":
               {"job_type": "classical",
                "region_grid_spacing": 0.1,
                "min_magnitude": 5,
                "investigation_time": 50,
                "component": "average",
                "imt": "pga",
                "truncation_type": "none",
                "truncation_level": 3,
                "reference_v30_value": 800,
                "imls": [ 0.2,0.02,0.01],
                "poes": [0.2,0.02,0.01],
                "realizations": 6,
                "region": "POLYGON((16.460737205888 41.257786872643, "
                    "16.460898138429 41.257786872643, 16.460898138429 "
                    "41.257923984376, 16.460737205888 41.257923984376, "
                    "16.460737205888 41.257786872643))"}}
        job = prepare_job(post_params)
        self.assertTrue(isinstance(job, OqJob))
        self.assertEqual(upload, job.oq_params.upload)

    def test_prepare_upload_param_values(self):
        """
        `prepare_job` returns a :py:class:`geonode.mtapi.models.OqJob`
        instance. The latter's `oq_params` property is initialized correctly.
        """
        upload = self.setup_upload()
        post_params = {
            "model":"openquake.calculationparams",
            "upload": upload.id,
            "fields":
               {"job_type": "classical",
                "region_grid_spacing": 0.1,
                "min_magnitude": 5,
                "investigation_time": 50,
                "component": "average",
                "imt": "pga",
                "truncation_type": "none",
                "truncation_level": 3,
                "reference_v30_value": 800,
                "imls": [ 0.2,0.02,0.01],
                "poes": [0.2,0.02,0.01],
                "realizations": 6,
                "region": "POLYGON((16.460737205888 41.257786872643, "
                    "16.460898138429 41.257786872643, 16.460898138429 "
                    "41.257923984376, 16.460737205888 41.257923984376, "
                    "16.460737205888 41.257786872643))"}}
        oqp = prepare_job(post_params).oq_params
        trans_tab = dict(reference_v30_value="reference_vs30_value")
        param_names =  (
            "job_type", "region_grid_spacing", "min_magnitude",
            "investigation_time", "component", "imt", "truncation_type",
            "truncation_level", "reference_v30_value", "imls", "poes",
            "realizations")
        for param_name in param_names:
            attr_name = trans_tab.get(param_name, param_name)
            self.assertEqual(getattr(oqp, attr_name),
                             post_params["fields"][param_name])
