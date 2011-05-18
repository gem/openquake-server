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


import operator
import unittest


from bin.gen_shapefile import (
    calculate_loss_data, extract_hazardmap_data, extract_lossmap_data,
    extract_position, find_min_max, tag_extractor)


class CalculateLossDataTestCase(unittest.TestCase):
    """Tests the behaviour of generate_shapefile.calculate_loss_data()."""

    def test_calculate_loss_data(self):
        """
        Mean values are summed up for all assets at a certain location.
        """
        data = [
        (['-118.229726', '34.050622'],
         [('0', '1.71451736293', '2.00606841051'),
          ('1', '14.3314083523', '11.9001178481'),
          ('2', '0.00341983323202', '0.0218042708753')]),
        (['-118.241243', '34.061557'],
         [('104', '260.1793321', '298.536543258'),
          ('105', '205.54063128', '182.363531209'),
          ('106', '163.603304574', '222.371828022')]),
        (['-118.245388', '34.055984'],
         [('219', '59.1595800341', '53.5693102791'),
          ('220', '104.689400653', '65.9931553211'),
          ('221', '82.1438713787', '156.848140719')])]
        expected_data = [
            (['-118.229726', '34.050622'], 16.04934554846202),
            (['-118.241243', '34.061557'], 629.323267954),
            (['-118.245388', '34.055984'], 245.9928520658)]

        self.assertEqual(expected_data, calculate_loss_data(data))


class FindMinMaxTestCase(unittest.TestCase):
    """Tests the behaviour of generate_shapefile.find_min_max()."""

    def test_find_min_max_for_hazard_maps(self):
        """
        Hazard map minimum and maximum values are found correctly.
        """
        data = [
            (['-121.8', '37.9'], '1.23518683436'),
            (['-122.0', '37.5'], '1.19244541041'),
            (['-122.1', '38.0'], '1.1905288226')]

        self.assertEqual(('1.1905288226', '1.23518683436'),
                         find_min_max(data, operator.itemgetter(1)))

    def test_find_min_max_for_loss_maps(self):
        """
        Hazard map minimum and maximum values are found correctly.
        """
        data = [
            (['-118.229726', '34.050622'], 16.04934554846202),
            (['-118.241243', '34.061557'], 629.323267954),
            (['-118.245388', '34.055984'], 245.9928520658)]

        self.assertEqual((16.04934554846202, 629.323267954),
                         find_min_max(data, operator.itemgetter(1)))

    def test_find_min_max_with_empty_data(self):
        """
        An `Exception` is raised in case of empty data.
        """
        try:
            find_min_max([], lambda x: x)
        except Exception, e:
            self.assertEqual("Empty data set", e.args[0])
        else:
            self.fail(msg="No exception raised!")


class ExtractHazardmapDataTestCase(unittest.TestCase):
    """Tests the behaviour of generate_shapefile.extract_hazardmap_data()."""

    def test_extract_hazardmap_data(self):
        """
        Hazard map data is extracted correctly.
        """
        config = {
            "key": "78", "layer": "78-hazardmap-0.01-quantile-0.25",
            "output": "tests/78",
            "path": "tests/data/hazardmap-0.1-quantile-0.25.xml",
            "type": "hazard"}
        expected_data = [
            (['-121.8', '37.9'], '1.23518683436'),
            (['-122.0', '37.5'], '1.19244541041'),
            (['-122.1', '38.0'], '1.1905288226')]

        self.assertEqual(expected_data, extract_hazardmap_data(config))


class ExtractLossmapDataTestCase(unittest.TestCase):
    """Tests the behaviour of generate_shapefile.extract_lossmap_data()."""

    def test_extract_lossmap_data(self):
        """
        Loss map data is extracted correctly.
        """
        config = {
            "key": "77", "layer": "77-lossmap-0.01-quantile-0.25",
            "output": "tests/77", "path": "tests/data/loss-map-0fcfdbc7.xml",
            "type": "loss"}
        expected_data = [
        (['-118.229726', '34.050622'],
         [('0', '1.71451736293', '2.00606841051'),
          ('1', '14.3314083523', '11.9001178481'),
          ('2', '0.00341983323202', '0.0218042708753')]),
        (['-118.241243', '34.061557'],
         [('104', '260.1793321', '298.536543258'),
          ('105', '205.54063128', '182.363531209'),
          ('106', '163.603304574', '222.371828022')]),
        (['-118.245388', '34.055984'],
         [('219', '59.1595800341', '53.5693102791'),
          ('220', '104.689400653', '65.9931553211'),
          ('221', '82.1438713787', '156.848140719')])]

        self.assertEqual(expected_data, extract_lossmap_data(config))


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
            self.fail(msg="No exception raised!")


class TagExtractorTestCase(unittest.TestCase):
    """Tests the behaviour of generate_shapefile.tag_extractor()."""

    def test_tag_extractor_with_hazard_map(self):
        """
        `HMNode` tags are extracted correctly.
        """
        expected_data = ['''<HMNode gml:id="n_1">
        <HMSite>
          <gml:Point srsName="epsg:4326">
            <gml:pos>-121.8 37.9</gml:pos>
          </gml:Point>
          <vs30>760.0</vs30>
        </HMSite>
        <IML>1.23518683436</IML>
      </HMNode>''', '''<HMNode gml:id="n_2">
        <HMSite>
          <gml:Point srsName="epsg:4326">
            <gml:pos>-122.0 37.5</gml:pos>
          </gml:Point>
          <vs30>760.0</vs30>
        </HMSite>
        <IML>1.19244541041</IML>
      </HMNode>''', '''<HMNode gml:id="n_3">
        <HMSite>
          <gml:Point srsName="epsg:4326">
            <gml:pos>-122.1 38.0</gml:pos>
          </gml:Point>
          <vs30>760.0</vs30>
        </HMSite>
        <IML>1.1905288226</IML>
      </HMNode>''']

        for idx, hmnode in enumerate(tag_extractor(
            "HMNode", "tests/data/hazardmap-0.1-quantile-0.25.xml")):
            self.assertEqual(expected_data[idx], hmnode)

    def test_tag_extractor_with_loss_map(self):
        """
        `LMNode` tags are extracted correctly.
        """
        expected_data = ['''<LMNode gml:id="lmn_1">
        <site>
          <gml:Point srsName="epsg:4326">
            <gml:pos>-118.229726 34.050622</gml:pos>
          </gml:Point>
        </site>
        <loss xmlns:ns0="http://openquake.org/xmlns/nrml/0.2" ns0:assetRef="0">
          <ns0:mean>1.71451736293</ns0:mean>
          <ns0:stdDev>2.00606841051</ns0:stdDev>
        </loss>
        <loss xmlns:ns1="http://openquake.org/xmlns/nrml/0.2" ns1:assetRef="1">
          <ns1:mean>14.3314083523</ns1:mean>
          <ns1:stdDev>11.9001178481</ns1:stdDev>
        </loss>
        <loss xmlns:ns2="http://openquake.org/xmlns/nrml/0.2" ns2:assetRef="2">
          <ns2:mean>0.00341983323202</ns2:mean>
          <ns2:stdDev>0.0218042708753</ns2:stdDev>
        </loss>
      </LMNode>''', '''<LMNode gml:id="lmn_2">
        <site>
          <gml:Point srsName="epsg:4326">
            <gml:pos>-118.241243 34.061557</gml:pos>
          </gml:Point>
        </site>
        <loss xmlns:ns3="http://openquake.org/xmlns/nrml/0.2" ns3:assetRef="104">
          <ns3:mean>260.1793321</ns3:mean>
          <ns3:stdDev>298.536543258</ns3:stdDev>
        </loss>
        <loss xmlns:ns4="http://openquake.org/xmlns/nrml/0.2" ns4:assetRef="105">
          <ns4:mean>205.54063128</ns4:mean>
          <ns4:stdDev>182.363531209</ns4:stdDev>
        </loss>
        <loss xmlns:ns5="http://openquake.org/xmlns/nrml/0.2" ns5:assetRef="106">
          <ns5:mean>163.603304574</ns5:mean>
          <ns5:stdDev>222.371828022</ns5:stdDev>
        </loss>
      </LMNode>''', '''<LMNode gml:id="lmn_3">
        <site>
          <gml:Point srsName="epsg:4326">
            <gml:pos>-118.245388 34.055984</gml:pos>
          </gml:Point>
        </site>
        <loss xmlns:ns6="http://openquake.org/xmlns/nrml/0.2" ns6:assetRef="219">
          <ns6:mean>59.1595800341</ns6:mean>
          <ns6:stdDev>53.5693102791</ns6:stdDev>
        </loss>
        <loss xmlns:ns7="http://openquake.org/xmlns/nrml/0.2" ns7:assetRef="220">
          <ns7:mean>104.689400653</ns7:mean>
          <ns7:stdDev>65.9931553211</ns7:stdDev>
        </loss>
        <loss xmlns:ns8="http://openquake.org/xmlns/nrml/0.2" ns8:assetRef="221">
          <ns8:mean>82.1438713787</ns8:mean>
          <ns8:stdDev>156.848140719</ns8:stdDev>
        </loss>
      </LMNode>''']

        for idx, hmnode in enumerate(tag_extractor(
            "LMNode", "tests/data/loss-map-0fcfdbc7.xml")):
            self.assertEqual(expected_data[idx], hmnode)
