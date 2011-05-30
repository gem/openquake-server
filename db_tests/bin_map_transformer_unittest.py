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
Unit tests for the bin/map_transformer.py tool.
"""


import mock
import operator
import os
import unittest


from bin.map_transformer import write_map_data_to_db

from tests.helpers import DbTestMixin


class WriteMapDataToDbDbTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of map_transformer.write_map_data_to_db()."""

    def test_write_map_data_to_db_with_hazard_data(self):
        """
        extract_hazardmap_data() is called for hazard maps.
        """

    def test_write_map_data_to_db_with_loss_data(self):
        """
        extract_lossmap_data() and calculate_loss_data()
        are called for loss maps.
        """

    def test_write_map_data_to_db_with_unknown_type(self):
        """
        Calling write_map_data_to_db() with an unknown map type results in an
        AssertionError.
        """

    def test_write_map_data_to_db_with_loss_hazard_mismatch(self):
        """
        Writing loss data for a hazard map results in an AssertionError.
        """

    def test_write_map_data_to_db_with_hazard_loss_mismatch(self):
        """
        Writing hazard data for a loss map results in an AssertionError.
        """

    def test_write_map_data_to_db_with_invalid_output_key(self):
        """
        Not being able to find the output record results in an AssertionError.
        """

    def test_write_map_data_to_db_with_hazard_map(self):
        """
        Writing hazard map data works.
        """

    def test_write_map_data_to_db_with_loss_map(self):
        """
        Writing hazard loss data works.
        """
