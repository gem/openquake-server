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


import os
import shutil
import unittest
import uuid

import tests

from ConfigParser import ConfigParser
from geonode.mtapi import models as mt_models
from utils.oqrunner import config_writer

from django.contrib.gis import geos


TEST_OWNER_ID = 1
TEST_JOB_PID = 1
TEST_OUTPUT_BASE_PATH = "/tmp/oqserver_tests"

TEST_PARAMS = {
    'CALCULATION_MODE': 'classical',
    'REGION_VERTEX': geos.Polygon(
        ((-122.2, 38.0), (-121.7, 38.0), (-121.7, 37.5),
         (-122.2, 37.5), (-122.2, 38.0))),
    'REGION_GRID_SPACING': 0.01,
    'MINIMUM_MAGNITUDE': 5.0,
    'INVESTIGATION_TIME': 50.0,
    'COMPONENT': 'gmroti50',
    'INTENSITY_MEASURE_TYPE': 'pga',
    'GMPE_TRUNCATION_TYPE': 'twosided',
    'TRUNCATION_LEVEL': '3',
    'REFERENCE_VS30_VALUE': '760.0',
    'INTENSITY_MEASURE_LEVELS': [0.005, 0.007, 0.0098, 0.0137, 0.0192,
        0.0269, 0.0376, 0.0527, 0.0738, 0.103, 0.145, 0.203, 0.284,
        0.397, 0.556, 0.778],
    'POES': [0.01, 0.10],
    'NUMBER_OF_LOGIC_TREE_SAMPLES': 1}

# This is a pre-existing example file we'll use to validate the file we create
EXPECTED_OUTPUT_FILE = "data/expected-config.gem"

# Upload dir
upload_dir_path = lambda upload_uuid: os.path.join(
    TEST_OUTPUT_BASE_PATH, upload_uuid)

# A file in the input dir
upload_file_path = lambda upload_uuid, file: os.path.join(
    upload_dir_path(upload_uuid), file)

# Job folder within the upload dir
job_dir_path = lambda upload_uuid, job_id: os.path.join(
    upload_dir_path(upload_uuid), job_id)


def create_inputs(upload_uuid):
    """
    Create some sample :py:class:`geonode.mtapi.models.Input` objects for the
    test case.

    This function will copy the input files from the base data directory
    to a unique temporary directory for the test.
    """
    exposure_path = upload_file_path(upload_uuid, 'exposure.xml')
    exposure = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=exposure_path,
        input_type='exposure')

    vuln_path = upload_file_path(upload_uuid, 'vulnerability.xml')
    vuln = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=vuln_path,
        input_type='vulnerability')

    src_ltree_path = upload_file_path(
        upload_uuid, 'source-model-logic-tree.xml')
    src_ltree = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=src_ltree_path,
        input_type='lt_source')

    gmpe_ltree_path = upload_file_path(upload_uuid, 'gmpe-logic-tree.xml')
    gmpe_ltree = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=gmpe_ltree_path,
        input_type='lt_gmpe')

    source_path = upload_file_path(upload_uuid, 'source-model.xml')
    source = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=source_path,
        input_type='source')

    inputs = (exposure, vuln, src_ltree, gmpe_ltree, source)

    # copy the files to the test location and get the file size
    for i in inputs:
        file_name = os.path.basename(i.path)
        file_path = tests.test_data_path(file_name)
        shutil.copy(file_path, i.path)
        i.size = os.path.getsize(i.path)

    return inputs


class JobConfigWriterClassicalTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        One-time setup for test data.
        """

        cls.upload_uuid = str(uuid.uuid4())
        cls.upload_dir = upload_dir_path(cls.upload_uuid)
        # create the unique upload dir
        os.makedirs(cls.upload_dir)

        # this sets up the basic params for a Classical PSHA calculation
        cls.oqparams = mt_models.OqParams(
            job_type=TEST_PARAMS['CALCULATION_MODE'],
            region=TEST_PARAMS['REGION_VERTEX'],
            region_grid_spacing=TEST_PARAMS['REGION_GRID_SPACING'],
            min_magnitude=TEST_PARAMS['MINIMUM_MAGNITUDE'],
            investigation_time=TEST_PARAMS['INVESTIGATION_TIME'],
            component=TEST_PARAMS['COMPONENT'],
            imt=TEST_PARAMS['INTENSITY_MEASURE_TYPE'],
            truncation_type=TEST_PARAMS['GMPE_TRUNCATION_TYPE'],
            truncation_level=TEST_PARAMS['TRUNCATION_LEVEL'],
            reference_vs30_value=TEST_PARAMS['REFERENCE_VS30_VALUE'],
            imls=TEST_PARAMS['INTENSITY_MEASURE_LEVELS'],
            poes=TEST_PARAMS['POES'],
            realizations=TEST_PARAMS['NUMBER_OF_LOGIC_TREE_SAMPLES'])

        cls.oqjob = mt_models.OqJob(
            owner_id=TEST_OWNER_ID,
            description='Test job for upload %s' % cls.upload_uuid,
            job_pid=TEST_JOB_PID,
            job_type='classical')

        cls.upload = \
            mt_models.Upload(
                owner_id=TEST_OWNER_ID,
                path=cls.upload_dir,
                job_pid=TEST_JOB_PID)

        # load the test data into the db
        # once some of the pieces are saved, we'll need to set ids
        # of subsequent records to resolve foreign key dependencies

        cls.upload.save()

        cls.oqparams.upload_id = cls.upload.id
        cls.oqparams.save()

        cls.oqjob.oq_params_id = cls.oqparams.id
        cls.oqjob.save()

        # now that we have a oq_job.id, set the job path to upload_path/job_id:
        cls.oqjob.path = os.path.join(cls.upload.path, str(cls.oqjob.id))
        # update the oq_job record
        cls.oqjob.save()

        # Create the job folder underneath the upload folder.
        # The folder structure needs to be in place before the config writer
        # goes to work.
        cls.job_dir = os.path.join(cls.upload_dir, str(cls.oqjob.id))
        os.makedirs(cls.job_dir)

        cls.inputs = create_inputs(cls.upload_uuid)
        for item in cls.inputs:
            item.upload_id = cls.upload.id
            item.save()

    @classmethod
    def tearDownClass(cls):
        """
        Remove temporary files created for the tests.
        """
        shutil.rmtree(cls.upload_dir, ignore_errors=True)

    def test_classical_config_file_generation(self):
        """
        This is somewhat of a 'blackbox' test. We have an existing 'expected'
        config file; given our sample data (which this test suite has loaded
        into the database), we simply generate a config file and compare it to
        the expected file.
        """
        out_path = os.path.join(self.job_dir, 'config.gem')
        expected_config = tests.test_data_path('expected_config.gem')

        cfg_writer = config_writer.JobConfigWriter(self.oqjob.id)

        path_to_new_cfg_file = cfg_writer.serialize()

        # check that the result directory is what we specified
        self.assertEqual(
            os.path.abspath(out_path),
            os.path.abspath(path_to_new_cfg_file))

        self._test_config_files_are_the_same(
            expected_config, path_to_new_cfg_file, oqjob_id=self.oqjob.id)

    def test_classical_config_file_generation_with_vuln_imls(self):
        """
        Test that the config file output has the proper IML values,
        as determined by the job's vulnerability model.
        """
        expected_config = tests.test_data_path('config_with_vuln_imls.gem')

        cfg_writer = config_writer.JobConfigWriter(
            self.oqjob.id,
            derive_imls_from_vuln=True,
            num_of_derived_imls=15)

        path_to_new_cfg_file = cfg_writer.serialize()

        self._test_config_files_are_the_same(
            expected_config, path_to_new_cfg_file, oqjob_id=self.oqjob.id)

    def test_classical_config_file_generation_no_serialize_results_to_db(self):
        """
        By default, config files are generated with the [general] parameter
        SERIALIZE_RESULTS_TO_DB set to True. This test exercises config file
        creation with the parameter set to False.
        """
        expected_config = tests.test_data_path('config_no_serialize_to_db.gem')

        cfg_writer = config_writer.JobConfigWriter(
            self.oqjob.id,
            serialize_results_to_db=False)

        path_to_new_cfg_file = cfg_writer.serialize()

        self._test_config_files_are_the_same(
            expected_config, path_to_new_cfg_file, self.oqjob.id)

    def _test_config_files_are_the_same(self, expected_file, actual_file,
        oqjob_id=None):
        """
        Given two *.gem config files, compare their contents and use test
        assertions to determine if they are the same.

        :param expected_file: path to the expected output
        :param actual_file: path to the actual output
        :param oqjob_id: If specified, check that the OPENQUAKE_JOB_ID
            parameter in the acutal_file is equal to this value. Otherwise just
            compare the files exactly.
        """
        # now compare the new file with the expected file
        exp_parser = ConfigParser()
        exp_fh = open(expected_file, 'r')
        exp_parser.readfp(exp_fh)

        actual_parser = ConfigParser()
        act_fh = open(actual_file, 'r')
        actual_parser.readfp(act_fh)

        # now compare the actual configuration items
        for section in ('general', 'HAZARD', 'RISK'):
            exp_items = exp_parser.items(section)
            actual_items = actual_parser.items(section)

            exp_items.sort()
            actual_items.sort()

            for ctr, (key, _value) in enumerate(exp_items):
                # if we specified a job_id to compare too, handle that here
                if key.upper() == "OPENQUAKE_JOB_ID" and oqjob_id:
                    self.assertEqual((key, str(oqjob_id)), actual_items[ctr])
                else:  # otherwise, just compare exactly what is in the files
                    self.assertEqual(exp_items[ctr], actual_items[ctr])

            exp_fh.close()
            act_fh.close()
