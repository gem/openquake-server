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
database related unit tests for the geonode/mtapi/views.py module.
"""


import unittest

from geonode.mtapi.views import detect_input_type


class DetectInputTypeTestCase(unittest.TestCase):
    """Tests the behaviour of views.detect_input_type()."""

    def test_detect_input_type_with_source(self):
        """
        A source model file is detected correctly.
        """
        chunk = '''
        <?xml version='1.0' encoding='utf-8'?>
        <nrml xmlns:gml="http://www.opengis.net/gml"
              xmlns:qml="http://quakeml.org/xmlns/quakeml/1.1"
              xmlns="http://openquake.org/xmlns/nrml/0.2"
              gml:id="n1">

            <!-- sourceModel is a gml:Feature -->
            <sourceModel gml:id="sm1">
                <config/>
        '''
        self.assertEqual("source", detect_input_type(chunk))

    def test_detect_input_type_with_source_ltree(self):
        """
        A source model file logic tree is detected correctly.
        """
        chunk = '''
        <?xml version="1.0" encoding="UTF-8"?>
        <nrml xmlns:gml="http://www.opengis.net/gml"
              xmlns="http://openquake.org/xmlns/nrml/0.2"
              gml:id="n1">
            <logicTreeSet>

                <logicTree id="lt1">
                        <logicTreeBranchSet branchingLevel="1" uncertaintyType="sourceModel">
        '''
        self.assertEqual("lt_source", detect_input_type(chunk))

    def test_detect_input_type_with_gmpe_ltree(self):
        """
        A GMPE logic tree is detected correctly.
        """
        chunk = '''
        <?xml version="1.0" encoding="UTF-8"?>

        <nrml xmlns:gml="http://www.opengis.net/gml"
              xmlns="http://openquake.org/xmlns/nrml/0.2"
              gml:id="n1">
            <logicTreeSet>
                <logicTree id="lt1" tectonicRegion="Active Shallow Crust">
                    <logicTreeBranchSet branchingLevel="1" uncertaintyType="gmpeModel">
        '''
        self.assertEqual("lt_gmpe", detect_input_type(chunk))

    def test_detect_input_type_with_exposure(self):
        """
        An exposure file is detected correctly.
        """
        chunk = '''
        <?xml version="1.0"?>
        <nrml xmlns="http://openquake.org/xmlns/nrml/0.2" xmlns:gml="http://www.opengis.net/gml" gml:id="nrml">
          <exposurePortfolio gml:id="ep">
            <exposureList gml:id="LA01" assetCategory="buildings" lossCategory="economic_loss">
        '''
        self.assertEqual("exposure", detect_input_type(chunk))

    def test_detect_input_type_with_vulnerability(self):
        """
        An vulnerability file is detected correctly.
        """
        chunk = '''
        <?xml version="1.0"?>
        <nrml xmlns="http://openquake.org/xmlns/nrml/0.2" xmlns:gml="http://www.opengis.net/gml" gml:id="nrml">
          <vulnerabilityModel>
            <discreteVulnerabilitySet vulnerabilitySetID="HAZUS" assetCategory="buildings" lossCategory="economic_loss">
        '''
        self.assertEqual("vulnerability", detect_input_type(chunk))
