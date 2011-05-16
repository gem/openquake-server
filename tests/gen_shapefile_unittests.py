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
Unit tests for the bin/generate_shapefile.py tool.
"""


import os
import unittest

from bin.generate_shapefile import extract_position


class ExtractPositionTestCase(unittest.TestCase):
    """Tests the behaviour of generate_shapefile.extract_position()."""

    def test_extract_position_with_expected_srid(self):
        """
        A (longitude, latitude) tuple is returned.
        """
        xml = '''
          <HMNode gml:id="n_1">
            <HMSite>
              <gml:Point srsName="epsg:4326">
                <gml:pos>-121.8 37.5</gml:pos>
              </gml:Point>
              <vs30>760.0</vs30>
            </HMSite>
            <IML>1.20589970498</IML>
          </HMNode>
        '''
        self.assertEqual(['-121.8', '37.5'], extract_position(xml))

    def test_extract_position_with_unexpected_srid(self):
        """
        In case of a differing spatial reference system an `Exception` is
        thrown.
        """
        xml = '''
          <HMNode gml:id="n_1">
            <HMSite>
              <gml:Point srsName="epsg:4326">
                <gml:pos>-121.8 37.5</gml:pos>
              </gml:Point>
              <vs30>760.0</vs30>
            </HMSite>
            <IML>1.20589970498</IML>
          </HMNode>
        '''
        try:
            extract_position(xml, expected_srid="no-such-srid")
        except Exception, e:
            self.assertEqual("Wrong spatial reference system: 'epsg:4326' "
                             "for position -121.8 37.5", e.args[0])
        else:
            raise Exception("No exception raised!")
