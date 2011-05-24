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
import mock
import os
import stat
import unittest

from django.conf import settings

from bin.oqrunner import (
    create_input_file_dir, find_maps, prepare_inputs, process_map,
    register_shapefiles, run_engine)

from db_tests.helpers import DbTestMixin


class RegisterShapefilesTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of oqrunner.register_shapefiles()."""

    def setUp(self):
        # The hazard map has a shapefile.
        hazard_map = self.setup_output()
        self.job = hazard_map.oq_job
        self.add_shapefile_data(hazard_map)
        self.hazard_location = os.path.dirname(hazard_map.shapefile_path)

        # The loss map has *no* shapefile.
        self.loss_map = self.setup_output(
            job_to_use=self.job, output_type="loss_map")
        self.assertTrue(hazard_map.id < self.loss_map.id)

    def tearDown(self):
        self.teardown_job(self.job)

    def test_register_shapefiles(self):
        """register_shapefiles_in_location() is called for the maps."""
        # Add a shapefile to the loss map.
        self.add_shapefile_data(self.loss_map)
        loss_location = os.path.dirname(self.loss_map.shapefile_path)
        with mock.patch('bin.oqrunner.register_shapefiles_in_location') \
            as mock_func:
            register_shapefiles(self.job)
            # Both the hazard and the loss map have a shapefile. Hence the 2
            # calls to register_shapefiles_in_location().
            self.assertEqual(2, mock_func.call_count)
            [(args1, _), (args2, _)] = mock_func.call_args_list
            self.assertEqual((self.hazard_location, "hazardmap"), args1)
            self.assertEqual((loss_location, "lossmap"), args2)

    def test_register_shapefiles_with_map_wo_shapefile(self):
        """register_shapefiles_in_location() is called for the maps."""
        with mock.patch('bin.oqrunner.register_shapefiles_in_location') \
            as mock_func:
            register_shapefiles(self.job)
            # The loss map has no shapefile and is ignored.
            self.assertEqual(1, mock_func.call_count)
            [(args1, _)] = mock_func.call_args_list
            self.assertEqual((self.hazard_location, "hazardmap"), args1)


class ProcessMapTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of oqrunner.process_map()."""

    def setUp(self):
        self.job = self.setup_classic_job()
        # Prepare the output files.
        self.output_path = os.path.join(self.job.path, "computed_output")
        os.mkdir(self.output_path)
        map_files = glob.glob("db_tests/data/*map*.xml")

        hazardmaps = list(sorted(
            [file for file in map_files
             if os.path.basename(file).find("hazard") > -1]))
        assert hazardmaps, "No hazard maps found"
        lossmaps = list(sorted(
            [file for file in map_files
             if os.path.basename(file).find("loss") > -1]))
        assert lossmaps, "No loss maps found"

        # We want one of hazard/loss map each.
        for file in [hazardmaps.pop(0), lossmaps.pop(0)]:
            basename = os.path.basename(file)
            os.symlink(os.path.realpath(file),
                       os.path.join(self.output_path, basename))

    def tearDown(self):
        self.teardown_job(self.job)

    def test_process_map_calls_shapefile_gen_correctly_with_hazard(self):
        """
        The shapefile generator tool is invoked correctly for a hazard map.
        """
        maps = find_maps(self.job)
        self.assertEqual(2, len(maps))
        [hazard_map, _] = maps
        basename = os.path.basename(hazard_map.path)
        self.assertEqual("hazard_map", hazard_map.output_type)
        with mock.patch('geonode.mtapi.utils.run_cmd') as mock_func:
            mock_func.return_value = (
                0, "RESULT: ('/a/b/c', 16.04934554846202, 629.323267954)", "")
            process_map(hazard_map)
            expected = (
                (['%s/bin/gen_shapefile.py' % settings.OQ_APIAPP_DIR,
                  '-k', str(hazard_map.id),
                  '-p', '%s/computed_output/%s' % (self.job.path, basename),
                  '-t', 'hazard'],),
                {'ignore_exit_code': True})
            self.assertEqual(expected, mock_func.call_args)

    def test_process_map_calls_shapefile_gen_correctly_with_loss(self):
        """
        The shapefile generator tool is invoked correctly for a loss map.
        """
        maps = find_maps(self.job)
        self.assertEqual(2, len(maps))
        [_, loss_map] = maps
        basename = os.path.basename(loss_map.path)
        self.assertEqual("loss_map", loss_map.output_type)
        with mock.patch('geonode.mtapi.utils.run_cmd') as mock_func:
            mock_func.return_value = (
                0, "RESULT: ('/d/e/f', 61.4039544548262, 926.3032629745)", "")
            process_map(loss_map)
            expected = (
                (['%s/bin/gen_shapefile.py' % settings.OQ_APIAPP_DIR,
                  '-k', str(loss_map.id),
                  '-p', '%s/computed_output/%s' % (self.job.path, basename),
                  '-t', 'loss'],),
                {'ignore_exit_code': True})
            self.assertEqual(expected, mock_func.call_args)

    def test_process_map_shapefile_generated_correctly_with_hazard(self):
        """The db record for the hazard map is updated."""
        maps = find_maps(self.job)
        self.assertEqual(2, len(maps))
        [hazard_map, _] = maps
        self.assertEqual("hazard_map", hazard_map.output_type)
        with mock.patch('geonode.mtapi.utils.run_cmd') as mock_func:
            mock_func.return_value = (
                0, "RESULT: ('/g/h/i', 17.17, 18.18)", "")
            process_map(hazard_map)
            self.assertEqual("/g/h/i", hazard_map.shapefile_path)
            self.assertEqual(17.17, hazard_map.min_value)
            self.assertEqual(18.18, hazard_map.max_value)

    def test_process_map_shapefile_generated_correctly_with_loss(self):
        """The db record for the loss map is updated."""
        maps = find_maps(self.job)
        self.assertEqual(2, len(maps))
        [_, loss_map] = maps
        self.assertEqual("loss_map", loss_map.output_type)
        with mock.patch('geonode.mtapi.utils.run_cmd') as mock_func:
            mock_func.return_value = (
                0, "RESULT: ('/j/k/l', 19.19, 21.21)", "")
            process_map(loss_map)
            self.assertEqual("/j/k/l", loss_map.shapefile_path)
            self.assertEqual(19.19, loss_map.min_value)
            self.assertEqual(21.21, loss_map.max_value)

    def test_process_map_with_shapefile_generator_error(self):
        """
        If the shapefile generation fails for a map the db record is *not*
        updated.
        """
        maps = find_maps(self.job)
        self.assertEqual(2, len(maps))
        [hazard_map, _] = maps
        self.assertEqual("hazard_map", hazard_map.output_type)
        with mock.patch('geonode.mtapi.utils.run_cmd') as mock_func:
            mock_func.return_value = (
                1, "", "failed to generate shapefile")
            process_map(hazard_map)
            self.assertIs(None, hazard_map.shapefile_path)
            self.assertIs(None, hazard_map.min_value)
            self.assertIs(None, hazard_map.max_value)


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

        self.assertEqual("pending", self.job.status)
        job = create_input_file_dir(config)
        self.assertEqual("running", job.status)
        info = os.stat(job.path)
        self.assertTrue(stat.S_ISDIR(info.st_mode))
        self.assertEqual("0777", oct(stat.S_IMODE(info.st_mode)))
        self.assertEqual(
            os.path.join(job.oq_params.upload.path, str(job.id)),
            job.path)
