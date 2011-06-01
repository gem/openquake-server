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


from bin.map_transformer import (
    calculate_loss_data, extract_hazardmap_data, extract_lossmap_data,
    extract_position, find_min_max, create_shapefile,
    create_shapefile_from_hazard_map, create_shapefile_from_loss_map,
    tag_extractor, write_map_data_to_db)

from tests.helpers import TestMixin


def patch_ogr():
    """
    Patch the ogr functions used in the shapefile generator functions.
    We don't want any of them actually called.

    :returns: a (driver_mock, feature_mock) 2-tuple
    """
    layer = mock.Mock(name="layer-mock")
    layer.CreateField.return_value = 0
    layer.GetLayerDefn.return_value = {}
    layer.CreateFeature.return_value = 0

    source = mock.Mock(name="source-mock")
    source.CreateLayer.return_value = layer

    driver = mock.Mock(name="driver-mock")
    driver.CreateDataSource.return_value = source

    feature = mock.Mock(name="feature-mock")

    return(driver, feature)


class CreateLossShapefileTestCase(unittest.TestCase, TestMixin):
    """
    Tests the behaviour of map_transformer.create_shapefile_from_loss_map().
    """
    CONTENT = '''
        <LMNode gml:id="lmn_3">
            <site>
              <gml:Point srsName="epsg:4326">
                <gml:pos>-118.245388 34.055984</gml:pos>
              </gml:Point>
            </site>
            <loss xmlns:ns6="http://openquake.org/xmlns/nrml/0.2"
                  ns6:assetRef="219">
              <ns6:mean>59.1595800341</ns6:mean>
              <ns6:stdDev>53.5693102791</ns6:stdDev>
            </loss>
        </LMNode>
        <LMNode gml:id="lmn_4">
            <site>
              <gml:Point srsName="epsg:4326">
                <gml:pos>-117.245388 35.055984</gml:pos>
              </gml:Point>
            </site>
            <loss xmlns:ns6="http://openquake.org/xmlns/nrml/0.2"
                  ns6:assetRef="220">
              <ns6:mean>0.0</ns6:mean>
              <ns6:stdDev>0.0</ns6:stdDev>
            </loss>
        </LMNode>
        '''

    def tearDown(self):
        os.unlink(self.loss_map)

    def test_create_shapefile_from_loss_map_with_unwanted_zero_val(self):
        """
        Zero values are *not* added to the shapefile when config["zeroes"] is
        `False`.
        """
        self.loss_map = self.touch(self.CONTENT, suffix="xml")
        config = dict(key="11", layer="abc", output="def",
                      path=self.loss_map, type="loss", zeroes=False)

        # We don't want any of the actual ogr functions called, they are all
        # patched.
        driver, feature = patch_ogr()
        with mock.patch("ogr.GetDriverByName") as gdbn:
            gdbn.return_value = driver
            with mock.patch("ogr.Feature") as ofeat:
                ofeat.return_value = feature
                # Call the actual function under test.
                create_shapefile_from_loss_map(config)

        # The zero value is *not* added to the shapefile.
        fields = [m for m in feature.method_calls if m[0] == 'SetField']
        self.assertEqual([('SetField', ('mean', 59.1595800341), {})], fields)

    def test_create_shapefile_from_loss_map_with_wanted_zero_val(self):
        """
        Zero values *are* added to the shapefile when config["zeroes"] is
        `True`.
        """
        self.loss_map = self.touch(self.CONTENT, suffix="xml")
        config = dict(key="12", layer="abc", output="def",
                      path=self.loss_map, type="loss", zeroes=True)

        # We don't want any of the actual ogr functions called, they are all
        # patched.
        driver, feature = patch_ogr()
        with mock.patch("ogr.GetDriverByName") as gdbn:
            gdbn.return_value = driver
            with mock.patch("ogr.Feature") as ofeat:
                ofeat.return_value = feature
                # Call the actual function under test.
                create_shapefile_from_loss_map(config)

        # The zero value is added to the shapefile as well.
        fields = [m for m in feature.method_calls if m[0] == 'SetField']
        self.assertEqual(
            [('SetField', ('mean', 59.1595800341), {}),
             ('SetField', ('mean', 0.0), {})], fields)


class CreateHazardShapefileTestCase(unittest.TestCase, TestMixin):
    """
    Tests the behaviour of map_transformer.create_shapefile_from_hazard_map().
    """
    CONTENT = '''
        <HMNode gml:id="n_3">
            <HMSite>
              <gml:Point srsName="epsg:4326">
                <gml:pos>-122.1 38.0</gml:pos>
              </gml:Point>
              <vs30>760.0</vs30>
            </HMSite>
            <IML>1.1905288226</IML>
        </HMNode>
        <HMNode gml:id="n_4">
            <HMSite>
              <gml:Point srsName="epsg:4326">
                <gml:pos>-122.1 48.0</gml:pos>
              </gml:Point>
              <vs30>760.0</vs30>
            </HMSite>
            <IML>0.0</IML>
        </HMNode>'''

    def tearDown(self):
        os.unlink(self.hazard_map)

    def test_create_shapefile_from_hazard_map_with_unwanted_zero_val(self):
        """
        Zero values are *not* added to the shapefile when config["zeroes"] is
        `False`.
        """
        self.hazard_map = self.touch(self.CONTENT, suffix="xml")
        config = dict(key="13", layer="abc", output="def",
                      path=self.hazard_map, type="hazard", zeroes=False)

        # We don't want any of the actual ogr functions called, they are all
        # patched.
        driver, feature = patch_ogr()
        with mock.patch("ogr.GetDriverByName") as gdbn:
            gdbn.return_value = driver
            with mock.patch("ogr.Feature") as ofeat:
                ofeat.return_value = feature
                # Call the actual function under test.
                create_shapefile_from_hazard_map(config)

        # The zero value is *not* added to the shapefile.
        fields = [m for m in feature.method_calls if m[0] == 'SetField']
        self.assertEqual([('SetField', ('IML', 1.1905288226), {})], fields)

    def test_create_shapefile_from_hazard_map_with_wanted_zero_val(self):
        """
        Zero values *are* added to the shapefile when config["zeroes"] is
        `True`.
        """
        self.hazard_map = self.touch(self.CONTENT, suffix="xml")
        config = dict(key="14", layer="abc", output="def",
                      path=self.hazard_map, type="hazard", zeroes=True)

        # We don't want any of the actual ogr functions called, they are all
        # patched.
        driver, feature = patch_ogr()
        with mock.patch("ogr.GetDriverByName") as gdbn:
            gdbn.return_value = driver
            with mock.patch("ogr.Feature") as ofeat:
                ofeat.return_value = feature
                # Call the actual function under test.
                create_shapefile_from_hazard_map(config)

        # The zero value is added to the shapefile as well.
        fields = [m for m in feature.method_calls if m[0] == 'SetField']
        self.assertEqual(
            [('SetField', ('IML', 1.1905288226), {}),
             ('SetField', ('IML', 0.0), {})], fields)


class CreateShapefileTestCase(unittest.TestCase, TestMixin):
    """Tests the behaviour of map_transformer.create_shapefile()."""

    def setUp(self):
        self.map_file = self.touch()

    def tearDown(self):
        os.unlink(self.map_file)

    def test_create_shapefile_map_is_not_file(self):
        """
        When the passed map file path is not a file an `AssertionError` is
        raised.
        """
        config = dict(key="15", layer="abc", output="def", path="/tmp",
                      type="hazard")
        self.assertRaises(AssertionError, create_shapefile, config)

    def test_create_shapefile_map_file_not_readable(self):
        """
        When the passed map file path is not a file readble by us an
        `AssertionError` is raised.
        """
        os.chmod(self.map_file, 0000)
        config = dict(key="16", layer="abc", output="def", path=self.map_file,
                      type="hazard")
        self.assertRaises(AssertionError, create_shapefile, config)

    def test_create_shapefile_no_output(self):
        """
        If unspecified the output is determined from the map's path/layer.
        """
        config = dict(key="17", layer="", output="", path=self.map_file,
                      type="hazard")
        with mock.patch(
            'bin.map_transformer.create_shapefile_from_hazard_map') as mf:
            mf.return_value = ("", 0, 1)
            create_shapefile(config)
            basename = os.path.basename(self.map_file)
            expected_layer = "%s-%s" % (config["key"], basename)
            [actual_config], _kwargs = mf.call_args
            self.assertEqual(expected_layer, actual_config["layer"])
            dirname = os.path.dirname(self.map_file)
            self.assertEqual(
                os.path.join(dirname, "%s-shapefiles" % config["type"]),
                actual_config["output"])

    def test_create_shapefile_no_output_with_dots(self):
        """
        If unspecified the output is determined from the map's path/layer.
        All dot characters in the layer name will be replaced by dashes.
        """
        map_file2 = self.touch(prefix="we.love.dots.")
        config = dict(key="18", layer="", output="", path=map_file2,
                      type="hazard")
        with mock.patch(
            'bin.map_transformer.create_shapefile_from_hazard_map') as mf:
            mf.return_value = ("", 0, 1)
            create_shapefile(config)
            basename = os.path.basename(map_file2)
            basename, _ = os.path.splitext(basename)
            expected_layer = (
                "%s-%s" % (config["key"], basename.replace(".", "-")))
            [actual_config], _kwargs = mf.call_args
            self.assertEqual(expected_layer, actual_config["layer"])
            dirname = os.path.dirname(self.map_file)
            self.assertEqual(
                os.path.join(dirname, "%s-shapefiles" % config["type"]),
                actual_config["output"])
        os.unlink(map_file2)

    def test_create_shapefile_with_non_existent_output(self):
        """
        When the output path does not exist an `AssertionError` is raised.
        """
        config = dict(key="19", layer="abc", output="/def", path="/tmp",
                      type="hazard")
        self.assertRaises(AssertionError, create_shapefile, config)

    def test_create_shapefile_with_output_not_file_or_dir(self):
        """
        When the output path is neither a directory nor a file an
        `AssertionError` is raised.
        """
        os.symlink(self.map_file, "/tmp/map-sym-link")
        config = dict(key="20", layer="abc", output="/def",
                      path="/tmp/map-sym-link", type="hazard")
        self.assertRaises(AssertionError, create_shapefile, config)
        os.unlink("/tmp/map-sym-link")

    def test_create_shapefile_with_hazard_map(self):
        """
        Make sure the right function is called for hazard maps.
        """
        config = dict(key="21", layer="", output="", path=self.map_file,
                      type="hazard")
        with mock.patch(
            'bin.map_transformer.create_shapefile_from_hazard_map') as mf:
            mf.return_value = ("", 0, 1)
            create_shapefile(config)
            self.assertEqual(1, mf.call_count)

    def test_create_shapefile_with_loss_map(self):
        """
        Make sure the right function is called for loss maps.
        """
        config = dict(key="22", layer="", output="", path=self.map_file,
                      type="loss")
        with mock.patch(
            'bin.map_transformer.create_shapefile_from_loss_map') as mf:
            mf.return_value = ("", 0, 1)
            create_shapefile(config)
            self.assertEqual(1, mf.call_count)

    def test_create_shapefile_with_unknown_map(self):
        """
        An `AssertionError` is raised for unknown map types.
        """
        config = dict(key="23", layer="abc", output="/def", path="/tmp",
                      type="unknown")
        self.assertRaises(AssertionError, create_shapefile, config)


class CalculateLossDataTestCase(unittest.TestCase):
    """Tests the behaviour of map_transformer.calculate_loss_data()."""

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
    """Tests the behaviour of map_transformer.find_min_max()."""

    def test_find_min_max_for_hazard_maps(self):
        """
        Hazard map minimum and maximum values are found correctly.
        """
        data = [
            (['-121.8', '37.9'], '1.23518683436'),
            (['-122.0', '37.5'], '1.19244541041'),
            (['-122.1', '38.0'], '1.1905288226')]

        self.assertEqual((1.1905288226, 1.23518683436),
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
    """Tests the behaviour of map_transformer.extract_hazardmap_data()."""

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
    """Tests the behaviour of map_transformer.extract_lossmap_data()."""

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
    """Tests the behaviour of map_transformer.extract_position()."""

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
    """Tests the behaviour of map_transformer.tag_extractor()."""

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
        <loss xmlns:ns3="http://openquake.org/xmlns/nrml/0.2"
              ns3:assetRef="104">
          <ns3:mean>260.1793321</ns3:mean>
          <ns3:stdDev>298.536543258</ns3:stdDev>
        </loss>
        <loss xmlns:ns4="http://openquake.org/xmlns/nrml/0.2"
              ns4:assetRef="105">
          <ns4:mean>205.54063128</ns4:mean>
          <ns4:stdDev>182.363531209</ns4:stdDev>
        </loss>
        <loss xmlns:ns5="http://openquake.org/xmlns/nrml/0.2"
              ns5:assetRef="106">
          <ns5:mean>163.603304574</ns5:mean>
          <ns5:stdDev>222.371828022</ns5:stdDev>
        </loss>
      </LMNode>''', '''<LMNode gml:id="lmn_3">
        <site>
          <gml:Point srsName="epsg:4326">
            <gml:pos>-118.245388 34.055984</gml:pos>
          </gml:Point>
        </site>
        <loss xmlns:ns6="http://openquake.org/xmlns/nrml/0.2"
              ns6:assetRef="219">
          <ns6:mean>59.1595800341</ns6:mean>
          <ns6:stdDev>53.5693102791</ns6:stdDev>
        </loss>
        <loss xmlns:ns7="http://openquake.org/xmlns/nrml/0.2"
              ns7:assetRef="220">
          <ns7:mean>104.689400653</ns7:mean>
          <ns7:stdDev>65.9931553211</ns7:stdDev>
        </loss>
        <loss xmlns:ns8="http://openquake.org/xmlns/nrml/0.2"
              ns8:assetRef="221">
          <ns8:mean>82.1438713787</ns8:mean>
          <ns8:stdDev>156.848140719</ns8:stdDev>
        </loss>
      </LMNode>''']

        for idx, hmnode in enumerate(tag_extractor(
            "LMNode", "tests/data/loss-map-0fcfdbc7.xml")):
            self.assertEqual(expected_data[idx], hmnode)


class WriteMapDataToDbTestCase(unittest.TestCase):
    """Tests the behaviour of map_transformer.write_map_data_to_db()."""

    def test_write_map_data_to_db_with_hazard_data(self):
        """
        extract_hazardmap_data() is called for hazard maps.
        """
        config = {
            "key": "78", "layer": "78-hazardmap-0.01-quantile-0.25",
            "output": "tests/78",
            "path": "tests/data/hazardmap-0.1-quantile-0.25.xml",
            "type": "hazard"}
        with mock.patch("bin.map_transformer.extract_hazardmap_data") as mf:
            mf.return_value = []
            write_map_data_to_db(config)
            self.assertEqual(1, mf.call_count)
            args, _ = mf.call_args
            self.assertEqual((config,), args)

    def test_write_map_data_to_db_with_no_hazard_data(self):
        """
        In case that no hazard map data is found, a (map_db_key, 0.0, 0.0)
        triple will be returned.
        """
        config = {
            "key": "78", "layer": "78-hazardmap-0.01-quantile-0.25",
            "output": "tests/78",
            "path": "tests/data/hazardmap-0.1-quantile-0.25.xml",
            "type": "hazard"}
        with mock.patch("bin.map_transformer.extract_hazardmap_data") as mf:
            mf.return_value = []
            results = write_map_data_to_db(config)
            self.assertEqual((config["key"], 0.0, 0.0), results)

    def test_write_map_data_to_db_with_loss_data(self):
        """
        extract_lossmap_data() and calculate_loss_data() are called for loss
        maps.
        """
        config = {
            "key": "77", "layer": "77-lossmap-0.01-quantile-0.25",
            "output": "tests/77", "path": "tests/data/loss-map-0fcfdbc7.xml",
            "type": "loss"}
        with mock.patch("bin.map_transformer.extract_lossmap_data") as eld:
            with mock.patch("bin.map_transformer.calculate_loss_data") as cld:
                cld.return_value = eld.return_value = []
                write_map_data_to_db(config)
                self.assertEqual(1, eld.call_count)
                args, _ = eld.call_args
                self.assertEqual((config,), args)
                self.assertEqual(1, cld.call_count)
                args, _ = cld.call_args
                self.assertEqual(([],), args)

    def test_write_map_data_to_db_with_no_loss_data(self):
        """
        In case that no loss map data is found, a (map_db_key, 0.0, 0.0)
        triple will be returned.
        """
        config = {
            "key": "77", "layer": "77-lossmap-0.01-quantile-0.25",
            "output": "tests/77", "path": "tests/data/loss-map-0fcfdbc7.xml",
            "type": "loss"}
        with mock.patch("bin.map_transformer.extract_lossmap_data") as eld:
            with mock.patch("bin.map_transformer.calculate_loss_data") as cld:
                cld.return_value = eld.return_value = []
                results = write_map_data_to_db(config)
                self.assertEqual((config["key"], 0.0, 0.0), results)

    def test_write_map_data_to_db_with_unknown_type(self):
        """
        Calling write_map_data_to_db() with an unknown map type results in an
        AssertionError.
        """
        config = {
            "key": "77", "layer": "77-nauticalmap-0.01-quantile-0.25",
            "output": "tests/77",
            "path": "tests/data/nautical-map-0fcfdbc7.xml",
            "type": "nautical"}
        self.assertRaises(Exception, write_map_data_to_db, config)
