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


import glob
import os
import stat
import unittest

from bin.oqrunner import create_input_file_dir, find_maps, prepare_inputs

from db_tests.helpers import DbTestMixin


class FindMapsTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of oqrunner.find_maps()."""

    def setUp(self):
        self.job = self.setup_classic_job()
        # Prepare the output files.
        self.output_path = os.path.join(self.job.path, "computed_output")
        os.mkdir(self.output_path)
        xml_files = glob.glob("db_tests/data/*.xml")
        for file in xml_files:
            basename = os.path.basename(file)
            os.symlink(os.path.realpath(file),
                       os.path.join(self.output_path, basename))

    def tearDown(self):
        self.teardown_job(self.job)

    def test_find_maps(self):
        """
        All maps are found.
        """
        expected = [
            '%s/hazardmap-0.01-mean.xml' % self.output_path,
            '%s/hazardmap-0.01-quantile-0.25.xml' % self.output_path,
            '%s/hazardmap-0.01-quantile-0.50.xml' % self.output_path,
            '%s/hazardmap-0.1-mean.xml' % self.output_path,
            '%s/hazardmap-0.1-quantile-0.25.xml' % self.output_path,
            '%s/hazardmap-0.1-quantile-0.50.xml' % self.output_path,
            '%s/loss-map-0fcfdbc7.xml' % self.output_path]
        found = find_maps(self.job)
        self.assertEqual(expected,
                         list(sorted([output.path for output in found])))

    def test_find_maps_and_types(self):
        """
        All maps are found, the types are correct.
        """
        expected = [
            ('hazardmap-0.01-mean.xml', "hazard_map"),
            ('hazardmap-0.01-quantile-0.25.xml', "hazard_map"),
            ('hazardmap-0.01-quantile-0.50.xml', "hazard_map"),
            ('hazardmap-0.1-mean.xml', "hazard_map"),
            ('hazardmap-0.1-quantile-0.25.xml', "hazard_map"),
            ('hazardmap-0.1-quantile-0.50.xml', "hazard_map"),
            ('loss-map-0fcfdbc7.xml', "loss_map")]
        found = find_maps(self.job)
        self.assertEqual(
            expected,
            list(sorted([(os.path.basename(o.path), o.output_type)
                         for o in found])))

    def test_find_maps_and_job_reference(self):
        """
        All maps are found, the db records refer to the correct job.
        """
        expected = [
            ('hazardmap-0.01-mean.xml', self.job),
            ('hazardmap-0.01-quantile-0.25.xml', self.job),
            ('hazardmap-0.01-quantile-0.50.xml', self.job),
            ('hazardmap-0.1-mean.xml', self.job),
            ('hazardmap-0.1-quantile-0.25.xml', self.job),
            ('hazardmap-0.1-quantile-0.50.xml', self.job),
            ('loss-map-0fcfdbc7.xml', self.job)]
        found = find_maps(self.job)
        self.assertEqual(
            expected,
            list(sorted([(os.path.basename(o.path), o.oq_job)
                         for o in found])))

    def test_find_maps_and_sizes(self):
        """
        All maps are found, the sizes captured in the db records are correct.
        """
        expected = [
            '%s/hazardmap-0.01-mean.xml' % self.output_path,
            '%s/hazardmap-0.01-quantile-0.25.xml' % self.output_path,
            '%s/hazardmap-0.01-quantile-0.50.xml' % self.output_path,
            '%s/hazardmap-0.1-mean.xml' % self.output_path,
            '%s/hazardmap-0.1-quantile-0.25.xml' % self.output_path,
            '%s/hazardmap-0.1-quantile-0.50.xml' % self.output_path,
            '%s/loss-map-0fcfdbc7.xml' % self.output_path]
        sizes = dict([(f, os.path.getsize(f)) for f in expected])
        found = find_maps(self.job)
        for output in found:
            self.assertEqual(sizes[output.path], output.size)


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
