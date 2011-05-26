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
from utils.oqrunner.config_writer import (_enum_translate,
    _float_list_to_str, _polygon_to_coord_string, _get_iml_bounds_from_vuln_file, _lower_bound, _upper_bound)


class JobConfigWriterTestCase(unittest.TestCase):
    """
    This suite contains general tests for the
    :py:class:`utils.oqrunner.config_writer.JobConfigWriter` class.
    """

    def test_constructor_raises(self):
        """
        The JobConfigWriter constructor should raise an AssertionError if the
        'num_of_derived_imls' parameter is specified with an invalid value.
        """
        fake_job_id = 1234

        self.assertRaises(AssertionError, config_writer.JobConfigWriter, fake_job_id,
            derive_imls_from_vuln=True, num_of_derived_imls=0)
        self.assertRaises(AssertionError, config_writer.JobConfigWriter, fake_job_id,
            derive_imls_from_vuln=True, num_of_derived_imls=1)
        self.assertRaises(AssertionError, config_writer.JobConfigWriter, fake_job_id,
            derive_imls_from_vuln=True, num_of_derived_imls=-1)


    def test_constructor_with_valid_input(self):
        """
        Test that the JobConfigWriter constructor does not throw any errors with known-good
        input combinations.
        """
        config_writer.JobConfigWriter(1234, derive_imls_from_vuln=True, num_of_derived_imls=2)
        config_writer.JobConfigWriter(1234, derive_imls_from_vuln=True, num_of_derived_imls=25)
        # num_of_derived_imls should be ignored if derive_imls_from_vuln is not set to True
        config_writer.JobConfigWriter(1234, num_of_derived_imls=-2)


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
        # Note that the lon,lat order is reversed in the expected string
        # (compared to the polygon below).
        expected_str = '38.0, -122.2, 38.0, -121.7, 37.5, -121.7, 37.5, -122.2'
        polygon = geos.Polygon(
            ((-122.2, 38.0), (-121.7, 38.0), (-121.7, 37.5),
             (-122.2, 37.5), (-122.2, 38.0)))

        actual_str = _polygon_to_coord_string(polygon)
        self.assertEqual(expected_str, actual_str)

    def test_float_list_to_str(self):
        floats = [0.1, 0.3, -0.666666, 3.14159, -2.17828]
        delimiter = '~! '

        expected = '0.1~! 0.3~! -0.666666~! 3.14159~! -2.17828'
        self.assertEqual(expected, _float_list_to_str(
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
                _enum_translate(in_item), out_list[ctr])
    

class VulnerabilityIMLsTestCase(unittest.TestCase):

    TEST_VULN_GOOD = tests.test_data_path('vulnerability.xml')

    # Doesn't not contain enough IML values
    TEST_VULN_NOT_ENOUGH_IMLS = tests.test_fail_data_path('vuln_not_enough_imls.xml')

    # Contains improperly ordered IML values
    TEST_VULN_BAD_IML_ORDER = tests.test_fail_data_path('vuln_bad_iml_order.xml')

    # Contains negative and 0.0 IML values
    TEST_VULN_BAD_IMLS = tests.test_fail_data_path('vuln_bad_imls.xml')
    
    
    def test_lower_bound(self):
        """
        Test _lower_bound with known-good inputs.
        """
        expected_lower_bound = 0.0657675

        lower_bound = _lower_bound(0.0672981496848, 0.0703593786689)

        self.assertEqual(expected_lower_bound, lower_bound)

    def test_lower_bound_raises(self):
        """
        Test that the _lower_bound function raises an AssertionError when the computed
        lower_bound value is <= 0.0.
        """
        self.assertRaises(AssertionError, _lower_bound, 1, 3)  # gives a lower bound of 0.0
        self.assertRaises(AssertionError, _lower_bound, 1, 5)  # gives a negative lower bound

    def test_upper_bound(self):
        """
        Test _upper_bound with known-good inputs.
        """
        expected_upper_bound = 5.62235

        upper_bound = _upper_bound(5.50264416787, 5.26323253716)

        self.assertEqual(expected_upper_bound, upper_bound)

    def test_upper_bound_raises(self):
        """
        Test that the _upper_bound function raises an AssertionError when the computed
        upper_bound value is <= 0.0.
        """
        self.assertRaises(AssertionError, _upper_bound, 2, 6)  # gives an upper bound of 0.0
        self.assertRaises(AssertionError, _upper_bound, 1, 5)  # gives a negative upper bound

    def test_get_iml_bounds_with_good_vuln_file(self):
        """
        Test calculation of IML bounds from a known-good vulnerability file.
        """
        exp_lb = 0.07414
        exp_ub = 1.62586

        actual_lb, actual_ub = _get_iml_bounds_from_vuln_file(self.TEST_VULN_GOOD) 

        self.assertEqual(exp_lb, actual_lb)
        self.assertEqual(exp_ub, actual_ub)

    def test_get_iml_bounds_raises_when_not_enough_imls(self):
        """
        If a vulnerability file contains less than 2 IMLs values in a given IML set,
        an AssertionError should be raised.
        """
        self.assertRaises(
            AssertionError, _get_iml_bounds_from_vuln_file,
            self.TEST_VULN_NOT_ENOUGH_IMLS)

    def test_get_iml_bounds_raises_when_imls_are_not_in_asc_order(self):
        """
        If the IMLs in a given IML set are not arranged in ascending order (where no two values are equal),
        an AssertionError should be raised.
        """
        self.assertRaises(
            AssertionError, _get_iml_bounds_from_vuln_file,
            self.TEST_VULN_BAD_IML_ORDER) 

    def test_get_iml_bounds_raises_on_invalid_imls(self):
        """
        If a vulnerability file contains IML values <= 0.0, an AssertionError should be raised.
        """
        self.assertRaises(
            AssertionError, _get_iml_bounds_from_vuln_file,
            self.TEST_VULN_BAD_IMLS)
