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


import mock
import os
import unittest

from django.conf import settings

from geonode.mtapi.models import OqJob, Upload
from geonode.mtapi.views import prepare_job, start_job

from db_tests.helpers import DbTestMixin


def get_post_params(additional_fields=None):
    """
    Return a dictionary similar to the POST parameters received by the
    "hazard_risk_calc" API endpoint.

    :param dict additional_data: additional data the caller wants added to the
        dict to be returned.
    """
    upload = DbTestMixin().setup_upload()
    post_params = {
        "model": "openquake.calculationparams",
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
            "imls": [0.2, 0.02, 0.01],
            "poes": [0.2, 0.02, 0.01],
            "realizations": 6,
            "region": "POLYGON((16.460737205888 41.257786872643, "
                "16.460898138429 41.257786872643, 16.460898138429 "
                "41.257923984376, 16.460737205888 41.257923984376, "
                "16.460737205888 41.257786872643))"}}
    if additional_fields:
        post_params["fields"].update(additional_fields)
    return post_params


class PrepareJobTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of views.prepare_job()."""

    def test_prepare_job(self):
        """
        `prepare_job` returns a :py:class:`geonode.mtapi.models.OqJob`
        instance. The latter's `oq_params` property refers to the correct
        upload record.
        """
        post_params = get_post_params()
        job = prepare_job(post_params)
        self.assertTrue(isinstance(job, OqJob))
        [upload] = Upload.objects.filter(id=post_params["upload"])
        self.assertEqual(upload, job.oq_params.upload)

    def test_prepare_job_param_values(self):
        """
        `prepare_job` returns a :py:class:`geonode.mtapi.models.OqJob`
        instance. The latter's `oq_params` property is initialized correctly.
        """
        post_params = get_post_params()
        oqp = prepare_job(post_params).oq_params
        trans_tab = dict(reference_v30_value="reference_vs30_value")
        param_names = (
            "job_type", "region_grid_spacing", "min_magnitude",
            "investigation_time", "component", "imt", "truncation_type",
            "truncation_level", "reference_v30_value", "imls", "poes",
            "realizations")
        for param_name in param_names:
            attr_name = trans_tab.get(param_name, param_name)
            self.assertEqual(getattr(oqp, attr_name),
                             post_params["fields"][param_name])

    def test_prepare_job_ignored_params(self):
        """
        `prepare_job()` ignores the following parameters: "period",
        "gm_correlated" and "histories" for classical job types.
        """
        ignored_fields = {"period": 1, "histories": 1, "gm_correlated": False}
        post_params = get_post_params(ignored_fields)
        oqp = prepare_job(post_params).oq_params
        trans_tab = dict(reference_v30_value="reference_vs30_value")
        param_names = (
            "job_type", "region_grid_spacing", "min_magnitude",
            "investigation_time", "component", "imt", "truncation_type",
            "truncation_level", "reference_v30_value", "imls", "poes",
            "realizations")
        for param_name in param_names:
            attr_name = trans_tab.get(param_name, param_name)
            self.assertEqual(getattr(oqp, attr_name),
                             post_params["fields"][param_name])


class StartJobTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of views.start_job()."""

    def test_start_job(self):
        """
        The oqrunner process is started with the correct path/arguments and
        its process ID (pid) is captured in the corresponding job record.
        """
        post_params = get_post_params()
        job = prepare_job(post_params)
        process_mock = mock.MagicMock(name="mock:the-process")
        process_mock.pid = 31459
        popen_mock = mock.MagicMock(name="mock:subprocess.Popen")
        popen_mock.return_value = process_mock
        with mock.patch('subprocess.Popen', new=popen_mock) as mock_func:
            start_job(job)
            args, _kwargs = mock_func.call_args
            self.assertEqual(
                (["%s/bin/oqrunner.py" % settings.OQ_APIAPP_DIR, "-j",
                  str(job.id)],), args)
            self.assertEqual(31459, job.job_pid)
