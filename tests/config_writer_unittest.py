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
import unittest
import uuid

from django.contrib.git import geos

from geonode.mtapi import models as mt_models
from oqrunner import config_writer


TEST_OWNER_ID = 1
TEST_UPLOAD_PATH = "data/inputs/"

TEST_PARAMS = {
    'CALCULATION_MODE': 'classical',
    'REGION_VERTEX': geos.Polygon(((-122.2, 38.0), (-121.7, 37.5), (-122.2, 37.5), (-122.2, 38.0))),
    'REGION_GRID_SPACING': 0.1,
    'MINIMUM_MAGNITUDE': 5.0,
    'INVESTIGATION_TIME': 200.0,
    'COMPONENT': 'gmroti50',
    'INTENSITY_MEASURE_TYPE': 'pga',
    'GMPE_TRUNCATION_TYPE': '2-sided',
    'TRUNCATION_LEVEL': '3',
    'REFERENCE_VS30_VALUE': '760.0',
    'INTENSITY_MEASURE_LEVELS': [0.005, 0.007, 0.0098, 0.0137, 0.0192,
        0.0269, 0.0376, 0.0527, 0.0738, 0.103, 0.145, 0.203, 0.284,
        0.397, 0.556, 0.778, 1.09, 1.52, 2.13],
    'POES': [0.01, 0.10],
    'NUMBER_OF_LOGIC_TREE_SAMPLES': 2}


# This is a pre-existing example file we'll use to validate the file we create
EXPECTED_OUTPUT_FILE = "data/expected-config.gem"

input_path = lambda path: os.path.join(TEST_UPLOAD_PATH, path)

def create_inputs():
    """
    Create some sample :py:class:`geonode.mtapi.models.Input` objects for the
    test case.
    """
    exposure_path = input_path('exposure.xml')
    exposure = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=exposure_path,
        input_type='exposure',
        size=os.path.getsize(exposure_path))

    vuln_path = input_path('vulnerability.xml')
    vuln = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=vuln_path,
        input_type='vulnerability',
        size=os.path.getsize(vuln_path))

    src_ltree_path = input_path('source-model-logic-tree.xml')
    src_ltree = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=src_ltree_path,
        input_type='ltree',
        size=os.path.getsize(src_ltree_path))

    gmpe_ltree_path = input_path('gmpe-logic-tree.xml')
    gmpe_ltree = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=gmpe_ltree_path,
        input_type='ltree',
        size=os.path.getsize(gmpe_ltree_path))

    source_path = input_path('source-model.xml')
    source = mt_models.Input(
        owner_id=TEST_OWNER_ID,
        path=source_path,
        input_type='source',
        size=os.path.getsize(source_path))

    return (exposure, vuln, src_ltree, gmpe_ltree, source)


class JobConfigWriterTestCase(unittest.TestCase):
    """
    """

    def __init__(self, *args, **kwargs): 
        super(RunnerTestCase, self).__init__(*args, **kwargs)

        # this sets up the basic params for a Classical PSHA calculation
        self.oqparams = mt_models.OqParams(
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

        self.oqjob = mt_models.OqJob(
            owner_id=TEST_OWNER_ID,
            # Use a UUID here since this field needs to be unique;
            # makes the testing environment a little more 'forgiving'
            description='Test job %s' % str(uuid.uuid4()),
            job_type='classical')
            
        self.upload = \
            mt_models.Upload(owner_id=TEST_OWNER_ID, path=TEST_UPLOAD_PATH)

        # load the test data into the db
        # once some of the pieces are saved, we'll need to set ids
        # of subsequent records to resolve foreign key dependencies

        self.upload.save()

        self.oqparams.upload_id = self.upload.id
        self.oqparams.save()

        self.oqjob.oq_params_id = self.oqparams.id
        self.oqjob.save()

        self.inputs = create_inputs()
        for item in self.inputs:
            item.upload_id = self.upload.id
            item.save()

    def test_foo(self):
        print "test foo"
        self.assertFalse(True)

    def test_constructor_raises(self):
        """
        Currently, we only support classical calculations. Event-based and
        deterministic methods are not yet supported.
        """

        fail_cases = [mt_models.OqParams(job_type=x) \
            for x in ('deterministic', 'event-based', 'foobar')]

        for fail in fail_cases:
            self.assertRaises(
                ValueError, config_writer.JobConfigWriter, 'fake/path', fail)
