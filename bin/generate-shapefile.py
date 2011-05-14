#!/usr/bin/env python
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
Write hazard/loss map data to a shapefile.

  -h | --help       : prints this help string
  -o | --output O   : path to the resulting shapefile
  -p | --path P     : path to the hazard/loss map file to be processed
  -t | --type T     : map type: may be one of hazard/loss
"""

import getopt
import logging
import ogr
import osr
import pprint
import re
import sys


logger = logging.getLogger('nrml_loader')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


def create_shapefile_from_hazard_map(config):
    assert config["type"] == "hazard", "wrong map type: '%s'" % config["type"]

    pos_re = re.compile(
        r"<gml:pos>([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)</gml:pos>")
    iml_re = re.compile(r"<IML>([-+]?\d+\.\d+)</IML>")

    data = []
    pos = None
    iml = None

    fh = open(config["path"], "r")
    for line in fh:
        match = pos_re.search(line)
        if match:
            pos = match.groups()
            continue
        match = iml_re.search(line)
        if match:
            assert pos, "No position for IML"
            data.append((pos,  match.group(1)))
            continue
    fh.close()
    logger.debug("IMLs found: %s" % len(data))
    logger.debug(pprint.pformat(data))

    if not data:
        return

    driver = ogr.GetDriverByName("ESRI Shapefile")
    assert driver is not None, "failed to instantiate driver"

    # Throw away the extension.
    basename = ".".join(config["path"].split(".")[:-1])
    source = driver.CreateDataSource("%s.shp" % basename)
    assert source is not None, "failed to instantiate data source"

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    layer = source.CreateLayer("hazard map", srs, ogr.wkbPoint)
    assert layer is not None, "failed to instantiate layer"

    field = ogr.FieldDefn("IML", ogr.OFTReal)
    assert layer.CreateField(field) == 0, "failed to create 'IML' field"

    for pos, iml in data:
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("IML", float(iml))
        point = ogr.Geometry(ogr.wkbPoint)
        point.SetPoint_2D(0, float(pos[0]), float(pos[1]))
        feature.SetGeometry(point)
        assert layer.CreateFeature(feature) == 0, \
            "Failed to create feature, %s || %s" % (pos, iml)
        feature.Destroy()


def main(cargs):
    """Run the NRML loader."""
    def strip_dashes(arg):
        """Remove leading dashes, return last portion of string remaining."""
        return arg.split('-')[-1]

    config = dict(output="", path="", type="hazard")
    longopts = ["%s" % k if isinstance(v, bool) else "%s=" % k
                for k, v in config.iteritems()] + ["help"]
    # Translation between short/long command line arguments.
    s2l = dict(o="output", p="path", t="type")

    try:
        opts, _ = getopt.getopt(cargs[1:], "ho:p:t:", longopts)
    except getopt.GetoptError, e:
        # User supplied unknown argument(?); print help and exit.
        print e
        print __doc__
        sys.exit(101)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print __doc__
            sys.exit(0)
        # Update the configuration in accordance with the arguments passed.
        opt = strip_dashes(opt)
        if opt not in config:
            opt = s2l[opt]
        arg = arg.strip()
        if arg:
            config[opt] = arg
        else:
            if isinstance(config[opt], bool):
                config[opt] = not config[opt]
            else:
                print "Empty value for '%s' parameter" % opt
                print __doc__
                sys.exit(102)

    # All arguments must be supplied.
    if len(cargs) < 2:
        print __doc__
        sys.exit(103)

    logger.info("config = %s" % pprint.pformat(config))
    if config["type"] == "hazard":
        create_shapefile_from_hazard_map(config)
    else:
        print "loss maps are not supported yet"
        sys.exit(104)


if __name__ == '__main__':
    main(sys.argv)
