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


import mock
import os
import stat
import unittest

from django.conf import settings

from bin.oqrunner import create_input_file_dir, prepare_inputs, run_engine
from db_tests.helpers import DbTestMixin


class RunEngineTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of oqrunner.run_engine()."""

    def setUp(self):
        self.job = self.setup_classic_job()

    def tearDown(self):
        self.teardown_job(self.job)

    def test_run_engine(self):
        """
        run_engine() passes the correct commands to run_cmd().
        """
        with mock.patch('geonode.mtapi.utils.run_cmd') as mock_func:
            # Make all the calls pass.
            mock_func.return_value = (-42, "__out__", "__err__")

            # Run the actual function that is to be tested.
            results = run_engine(self.job)
            # run_engine() is passing through the run_cmd() return value.
            self.assertEqual(mock_func.return_value, results)
            # run_cmd() was called once.
            self.assertEqual(1, mock_func.call_count)
            # The arguments passed to run_cmd() are as follows:
            expected = (
                (["%s/bin/openquake" % settings.OQ_ENGINE_DIR, "--config_file",
                  "%s/config.gem" % self.job.path],),
                {"ignore_exit_code": True})
            self.assertEqual(expected, mock_func.call_args)


class PrepareInputsTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of oqrunner.prepare_inputs()."""

    def setUp(self):
        self.job = self.setup_classic_job()

    def tearDown(self):
        self.teardown_job(self.job)

    def test_prepare_inputs_sets_up_a_config_file(self):
        """
        The job's input directory has a config.gem file that's readable to us.
        """
        prepare_inputs(self.job)
        config_path = os.path.join(self.job.path, "config.gem")
        self.assertTrue(os.path.isfile(config_path))
        self.assertTrue(os.access(config_path, os.R_OK))

    def test_prepare_inputs_sets_up_symlinks(self):
        """
        The job's input directory has symbolic links to
        all the input files in the corresponding upload file set.
        """
        prepare_inputs(self.job)
        for input in self.job.oq_params.upload.input_set.all():
            input_path = os.path.join(
                self.job.path, os.path.basename(input.path))
            self.assertTrue(os.path.islink(input_path))
            self.assertEqual(input.path, os.path.realpath(input_path))


class CreateInputFileDirTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of oqrunner.create_input_file_dir()."""

    def setUp(self):
        self.job = self.setup_classic_job(create_job_path=False)

    def tearDown(self):
        self.teardown_job(self.job)

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
