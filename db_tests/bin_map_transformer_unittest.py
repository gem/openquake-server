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
Database unit tests for the bin/map_transformer.py tool.
"""


import mock
import operator
import os
import unittest

from django.core.exceptions import ObjectDoesNotExist

from bin.map_transformer import write_map_data_to_db
from db_tests.helpers import DbTestMixin
import utils


class WriteMapDataToDbDbTestCase(unittest.TestCase, DbTestMixin):
    """Tests the behaviour of map_transformer.write_map_data_to_db()."""

    def tearDown(self):
        if hasattr(self, "job_to_tear_down") and self.job_to_tear_down:
            self.teardown_job(self.job_to_tear_down)

    def test_write_map_data_to_db_with_loss_hazard_mismatch(self):
        """
        Writing loss data for a hazard map results in an AssertionError.
        """
        hazard_map = self.setup_output()
        self.job_to_tear_down = hazard_map.oq_job
        config = {
            "key": "%s" % hazard_map.id,
            "layer": "77-lossmap-0.01-quantile-0.25", "output": "tests/77",
            "path": "tests/data/loss-map-0fcfdbc7.xml", "type": "loss"}
        try:
            write_map_data_to_db(config)
        except AssertionError, e:
            self.assertEqual(
                "Invalid map type ('hazard_map') for the given data ('loss')",
                e.args[0])

    def test_write_map_data_to_db_with_hazard_loss_mismatch(self):
        """
        Writing hazard data for a loss map results in an AssertionError.
        """
        loss_map = self.setup_output(output_type="loss_map")
        self.job_to_tear_down = loss_map.oq_job
        config = {
            "key": "%s" % loss_map.id,
            "layer": "78-hazardmap-0.01-quantile-0.25",
            "output": "tests/78",
            "path": "tests/data/hazardmap-0.1-quantile-0.25.xml",
            "type": "hazard"}
        try:
            write_map_data_to_db(config)
        except AssertionError, e:
            self.assertEqual(
                "Invalid map type ('loss_map') for the given data ('hazard')",
                e.args[0])

    def test_write_map_data_to_db_with_invalid_output_key(self):
        """
        Not being able to find the output record results in an
        ObjectDoesNotExist error.
        """
        config = {
            "key": "-111",
            "layer": "77-lossmap-0.01-quantile-0.25", "output": "tests/77",
            "path": "tests/data/loss-map-0fcfdbc7.xml", "type": "loss"}
        try:
            write_map_data_to_db(config)
        except ObjectDoesNotExist, e:
            self.assertEqual(
                "Output matching query does not exist.", e.args[0])

    def test_write_map_data_to_db_with_hazard_map(self):
        """
        Writing hazard map data works.
        """
        expected_hazard_data = [
            ([-121.8, 37.9], 1.23518683436),
            ([-122.0, 37.5], 1.19244541041),
            ([-122.1, 38.0], 1.1905288226)]

        def coords(idx):
            """Access the point coordinates."""
            return tuple(expected_hazard_data[idx][0])

        def value(idx):
            """Access the hazard value."""
            return utils.round_float(expected_hazard_data[idx][1])

        hazard_map = self.setup_output(output_type="hazard_map")
        self.job_to_tear_down = hazard_map.oq_job
        config = {
            "key": "%s" % hazard_map.id,
            "layer": "78-hazardmap-0.01-quantile-0.25",
            "output": "tests/78",
            "path": "tests/data/hazardmap-0.1-quantile-0.25.xml",
            "type": "hazard"}
        write_map_data_to_db(config)
        self.assertEqual(0, len(hazard_map.lossmapdata_set.all()))
        self.assertEqual(3, len(hazard_map.hazardmapdata_set.all()))
        for idx, hazard in enumerate(hazard_map.hazardmapdata_set.all()):
            self.assertEqual(coords(idx), hazard.location.coords)
            self.assertEqual(value(idx), utils.round_float(hazard.value))

    def test_write_map_data_to_db_with_loss_map(self):
        """
        Writing hazard loss data works.
        """
        expected_loss_data = [
            ([-118.229726, 34.050622], 16.04934554846202),
            ([-118.241243, 34.061557], 629.323267954),
            ([-118.245388, 34.055984], 245.9928520658)]

        def coords(idx):
            """Access the point coordinates."""
            return tuple(expected_loss_data[idx][0])

        def value(idx):
            """Access the loss value."""
            return utils.round_float(expected_loss_data[idx][1])

        loss_map = self.setup_output(output_type="loss_map")
        self.job_to_tear_down = loss_map.oq_job
        config = {
            "key": "%s" % loss_map.id,
            "layer": "77-lossmap-0.01-quantile-0.25",
            "output": "tests/77", "path": "tests/data/loss-map-0fcfdbc7.xml",
            "type": "loss"}
        write_map_data_to_db(config)
        self.assertEqual(0, len(loss_map.hazardmapdata_set.all()))
        self.assertEqual(3, len(loss_map.lossmapdata_set.all()))
        for idx, loss in enumerate(loss_map.lossmapdata_set.all()):
            self.assertEqual(coords(idx), loss.location.coords)
            self.assertEqual(value(idx), utils.round_float(loss.value))
