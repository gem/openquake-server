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
Unit tests for the bin/oqrunner.py module.
"""


import mock
import unittest
from urlparse import urljoin

from django.conf import settings

from bin.oqrunner import (
    detect_output_type, extract_results, register_shapefiles_in_location,
    update_layers)


class UpdateLayersTestCase(unittest.TestCase):
    """Tests the behaviour of oqrunner.update_layers()."""

    def test_register_shapefiles_in_location(self):
        """run_cmd() is called correctly."""
        expected = settings.OQ_UPDATE_LAYERS_PATH
        with mock.patch('geonode.mtapi.utils.run_cmd') as mock_func:
            mock_func.return_value = (0, "", "")
            update_layers()
            self.assertEqual(1, mock_func.call_count)
            [command], _ = mock_func.call_args
            self.assertEqual(expected, command)


class RegisterShapefilesInLocationTestCase(unittest.TestCase):
    """Tests the behaviour of oqrunner.register_shapefiles_in_location()."""

    def test_register_shapefiles_in_location(self):
        """curl is called correctly."""
        location = "/a/b/c"
        datastore = "hazardmap"
        url = urljoin(
            settings.GEOSERVER_BASE_URL,
            "rest/workspaces/geonode/datastores/%s/external.shp?configure=all"
            % datastore)
        expected = (
            "curl -v -u 'admin:@dm1n' -XPUT -H 'Content-type: text/plain' "
            "-d 'file:///a/b/c' '%s'" % url)
        with mock.patch('geonode.mtapi.utils.run_cmd') as mock_func:
            mock_func.return_value = (0, "", "")
            register_shapefiles_in_location(location, datastore)
            self.assertEqual(1, mock_func.call_count)
            [curl_command], _ = mock_func.call_args
            self.assertEqual(expected, curl_command)


class ExtractResultsTestCase(unittest.TestCase):
    """Tests the behaviour of oqrunner.extract_results()."""

    def test_extract_results(self):
        """The minimum/maximum values are extracted correctly."""
        sample = "RESULT: ('/path', 16.04934554846202, 629.323267954)"
        path, minimum, maximum = extract_results(sample)
        self.assertTrue(isinstance(path, basestring))
        self.assertEqual("/path", path)
        self.assertTrue(isinstance(minimum, float))
        self.assertEqual(16.04934554846202, minimum)
        self.assertTrue(isinstance(maximum, float))
        self.assertEqual(629.323267954, maximum)

    def test_extract_results_with_malformed_stdout(self):
        """The minimum/maximum values are extracted correctly."""
        sample = "malformed stdout"
        self.assertIs(None, extract_results(sample))


class DetectOutputTypeTestCase(unittest.TestCase):
    """Tests the behaviour of oqrunner.detect_output_type()."""

    def test_detect_output_type_with_hazard(self):
        """A hazard map is correctly detected."""
        self.assertEqual(
            "hazard",
            detect_output_type("tests/data/hazardmap-0.1-quantile-0.25.xml"))

    def test_detect_output_type_with_loss(self):
        """A loss map is correctly detected."""
        self.assertEqual(
            "loss", detect_output_type("tests/data/loss-map-0fcfdbc7.xml"))
