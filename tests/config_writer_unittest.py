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
import tests
import unittest
import uuid

from ConfigParser import ConfigParser
from django.contrib.gis import geos
from utils.oqrunner import config_writer


TEST_REGION = geos.Polygon(
    ((-122.2, 38.0), (-121.7, 38.0), (-121.7, 37.5),
     (-122.2, 37.5), (-122.2, 38.0)))

class JobConfigWriterClassicalTestCase(unittest.TestCase):
    """
    This suite of tests exercises funcionality related to the generation of
    config.gem files for 'Classical' calculations. This suite does not include
    tests which require database interaction. See
    :py:module:`db_tests.config_writer_unittest` for the corresponding database
    tests.
    """

    def test_write_params(self):
        """
        Exercise the private _write_params method. Basically, create a
        JobConfigWriter, call `_write_params`, and verify that the params were
        written to the ConfigParser object of the JobConfigWriter.
        """

        fake_job_id = 1234
        test_params = {
            'general': {'REGION_GRID_SPACING': 0.1},
            'HAZARD': {'MINIMUM_MAGNITUDE': 5.0},
            'RISK': {'CONDITIONAL_LOSS_POE': '0.01 0.10'}}
        cfg_writer = config_writer.JobConfigWriter(fake_job_id)

        cfg_writer._write_params(test_params)

        cfg_parser = cfg_writer.cfg_parser

        for section in test_params.keys():
            self.assertTrue(cfg_parser.has_section(section))

            for k, v in test_params[section].items():
                # we expected the str equivalent of whatever the value is
                self.assertEqual(str(v), cfg_parser.get(section, k))

    
class ConfigWriterUtilsTestCase(unittest.TestCase):
    """
    Exercises the module-level utility functions of
    :py:module:`oqrunner.config_writer`.
    """
    def test_polygon_to_coord_string(self):
        expected_str = '38.0, -122.2, 38.0, -121.7, 37.5, -121.7, 37.5, -122.2'
        polygon = TEST_REGION

        actual_str = config_writer.polygon_to_coord_string(polygon)
        self.assertEqual(expected_str, actual_str)

    def test_float_list_to_str(self):
        floats = [0.1, 0.3, -0.666666, 3.14159, -2.17828]
        delimiter = '~! '

        expected = '0.1~! 0.3~! -0.666666~! 3.14159~! -2.17828'
        self.assertEqual(expected, config_writer.float_list_to_str(
            floats, delimiter))

    def test_enum_translate(self):
        """
        Some config values which are stored in the database need to be
        translated into a legal form for the config file.

        For example, 'pga' in the DB needs to be 'PGA' in the config file.

        TODO(LB): This test kind of sucks, to be honest. It's better than
        nothing, but should probably be revisited later (especially if we need
        to add more translation options). There's no real 'functionality' here,
        just data mapping.
        """

        in_list = [
            'average', 'gmroti50', 'pga', 'sa', 'pgv',
            'pgd', 'none', 'onesided', 'twosided']
        out_list = [
            'Average Horizontal', 'Average Horizontal (GMRotI50)',
            'PGA', 'SA', 'PGV', 'PGD', 'None', '1 Sided', '2 Sided']

        for ctr, in_item in enumerate(in_list):
            self.assertEqual(
                config_writer.enum_translate(in_item), out_list[ctr])
