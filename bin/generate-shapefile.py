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
Write hazard/loss map data to a shapefile. If all goes well the tool will
print the minimum and maximum value(*) seen to the standard output.

  -h | --help       : prints this help string
  -k | --key K      : database key of the hazard/loss map
  -l | --layer L    : shapefile layer name
  -o | --output O   : path to the resulting shapefile
  -p | --path P     : path to the hazard/loss map file to be processed
  -t | --type T     : map type: may be one of hazard/loss

(*) IML and loss mean for hazard and loss maps respectively.
"""

import getopt
import logging
import ogr
import operator
import os
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
    """Reads a hazard map and creates a shapefile from it.

    :param dict config: a configuration `dict` with the following data
        items:
            - key (db key of the hazard map file)
            - layer (shapefile layer name)
            - output (shapefile path)
            - path (map file to be processed)
            - type (map type, hazard or loss)
    :returns: a float 2-tuple with the minimum and maximum IML value seen
        or None in case of an empty hazard map.
    """
    assert config["type"] == "hazard", "wrong map type: '%s'" % config["type"]

    # The hazard map has sequences of <gml:pos> tags followed by a an <IML>
    # tag.
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

    # At this point we have read the locations with their associated
    # intesity level measure (IML) values.
    driver = ogr.GetDriverByName("ESRI Shapefile")
    assert driver is not None, "failed to instantiate driver"

    source = driver.CreateDataSource(config["output"])
    assert source is not None, "failed to instantiate data source"

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    layer = source.CreateLayer(
        "%s-hazard-map" % config["layer"], srs, ogr.wkbPoint)
    assert layer is not None, "failed to instantiate layer"

    field = ogr.FieldDefn("IML", ogr.OFTReal)
    assert layer.CreateField(field) == 0, "failed to create 'IML' field"

    minimum = 1000000000.0
    maximum = -1000000000.0
    for pos, iml in data:
        iml = float(iml)
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("IML", iml)
        if iml < minimum:
            minimum = iml
        if iml > maximum:
            maximum = iml

        # Set the geometry.
        point = ogr.Geometry(ogr.wkbPoint)
        point.SetPoint_2D(0, float(pos[0]), float(pos[1]))
        feature.SetGeometry(point)

        assert layer.CreateFeature(feature) == 0, \
            "Failed to create feature, %s || %s" % (pos, iml)
        feature.Destroy()

    assert minimum <= maximum, "Internal error, IML out of range?"
    return (minimum, maximum)


def create_shapefile_from_loss_map(config):
    """Reads a loss map and creates a shapefile from it.

    For locations with multiple assets, the average of the assets' mean
    values will be written to the shapefile.

    :param dict config: a configuration `dict` with the following data
        items:
            - key (db key of the hazard map file)
            - layer (shapefile layer name)
            - output (shapefile path)
            - path (map file to be processed)
            - type (map type, hazard or loss)
    :returns: a float 2-tuple with the minimum and maximum mean value seen
        or None in case of an empty loss map.
    """
    assert config["type"] == "loss", "wrong map type: '%s'" % config["type"]

    # We will iterate over all <LMNode> tags and
    #   - first look for a <gml:pos> tag
    #   - then look for a sequence of <loss> tags (one per asset)
    lmnode_re = re.compile('(<LMNode.+?/LMNode>)+', re.DOTALL)
    pos_re = re.compile(
        '<site>.+pos>([^>]+)</[^>]*pos>.+/[^>]*site>', re.DOTALL)
    loss_re = re.compile('''
     (<loss[^>]+assetRef="([^">]+)"[^>]*>    # assetRef attribute
      [^>]+mean>([^>]+)</[^>]*mean>
      [^>]+stdDev>([^>]+)</[^>]*stdDev>
      [^>]*/[^>]*loss>)+
    ''', (re.DOTALL|re.VERBOSE))

    data = []
    pos = None

    fh = open(config["path"], "r")
    xml = fh.read()
    fh.close()

    for lmnode in lmnode_re.findall(xml):
        # We matched a full <LMNode> including its children.
        # Look for the position first.
        match = pos_re.search(lmnode)
        # Split longitude/latitude.
        pos = match.group(1).split()
        # This will capture assetRef, mean and stdDev for each <loss> tag.
        losses = [loss[1:] for loss in loss_re.findall(lmnode)]
        data.append((pos, losses))

    logger.debug("Losses found: %s" % len(data))
    logger.debug(pprint.pformat(data))

    if not data:
        return

    driver = ogr.GetDriverByName("ESRI Shapefile")
    assert driver is not None, "failed to instantiate driver"

    source = driver.CreateDataSource(config["output"])
    assert source is not None, "failed to instantiate data source"

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    layer = source.CreateLayer(
        "%s-loss-map" % config["layer"], srs, ogr.wkbPoint)
    assert layer is not None, "failed to instantiate layer"

    field = ogr.FieldDefn("mean", ogr.OFTReal)
    assert layer.CreateField(field) == 0, "failed to create 'mean' field"

    # This will be used to pick the mean value from a (assetRef, mean, stdDev)
    # 3-tuple.
    mean_getter = operator.itemgetter(1)
    minimum = 1000000000.0
    maximum = -1000000000.0
    for pos, losses in data:
        feature = ogr.Feature(layer.GetLayerDefn())

        # Get the 'mean' values for all the losses a this position.
        means = [float(mean_getter(loss)) for loss in losses]
        meanmean = sum(means)/len(means)
        feature.SetField("mean", meanmean)
        if meanmean < minimum:
            minimum = meanmean
        if meanmean > maximum:
            maximum = meanmean

        # Set the geometry.
        point = ogr.Geometry(ogr.wkbPoint)
        point.SetPoint_2D(0, float(pos[0]), float(pos[1]))
        feature.SetGeometry(point)

        assert layer.CreateFeature(feature) == 0, \
            "Failed to create feature, %s || %s" % (pos, losses)
        feature.Destroy()

    assert minimum <= maximum, "Internal error, loss mean out of range?"
    return (minimum, maximum)


def main(cargs):
    # TODO: al-maisan, Sun, 15 May 2011 19:34:34 +0200: package the command
    # line argument processing code below into a utility function.
    """Run the NRML loader."""
    def strip_dashes(arg):
        """Remove leading dashes, return last portion of string remaining."""
        return arg.split('-')[-1]

    mandatory_args = ["key", "path"]
    config = dict(key="", layer="", output="", path="", type="hazard")
    longopts = ["%s" % k if isinstance(v, bool) else "%s=" % k
                for k, v in config.iteritems()] + ["help"]
    # Translation between short/long command line arguments.
    s2l = dict(k="key", l="layer", o="output", p="path", t="type")

    try:
        opts, _ = getopt.getopt(cargs[1:], "hk:l:o:p:t:", longopts)
    except getopt.GetoptError, e:
        # User supplied unknown argument(?); print help and exit.
        print e
        print __doc__
        sys.exit(101)

    for help_flag in ("-h", "--help"):
        if help_flag in opts:
            print __doc__
            sys.exit(0)

    seen_args = []
    for arg, value in opts:
        # Update the configuration in accordance with the arguments passed.
        arg = strip_dashes(arg)
        if arg not in config:
            arg = s2l[arg]
        seen_args.append(arg)
        value = value.strip()
        if value:
            config[arg] = value
        else:
            if isinstance(config[arg], bool):
                config[arg] = not config[arg]
            else:
                print "Empty value for '%s' parameter" % arg
                print __doc__
                sys.exit(102)

    # All mandatory arguments must be supplied.
    for mandatory_arg in mandatory_args:
        if mandatory_arg not in seen_args:
            print "The '%s' parameter must be specified." % mandatory_arg
            print __doc__
            sys.exit(103)

    assert os.path.isfile(config["path"]), \
        "'%s' is not a file" % config["path"]
    assert os.access(config["path"], os.R_OK), \
        "'%s' is not readable" % config["path"]

    if not config["output"]:
        dirname, filename = os.path.split(config["path"])
        config["output"] = "%s/%s" % (dirname, config["key"])
        os.mkdir(config["output"])
        os.chmod(config["output"], 0777)
        basename, _ = os.path.splitext(filename)
        config["layer"] = "%s-%s" % (config["key"], basename)
    else:
        if os.path.isfile(config["output"]):
            outdir = os.path.dirname(config["output"])
        else:
            outdir = config["output"]
        assert os.access(outdir, os.W_OK), "'%s' is not writable" % outdir

    logger.info("config = %s" % pprint.pformat(config))

    pprint.pprint(config)
    minmax = None
    if config["type"] == "hazard":
        minmax = create_shapefile_from_hazard_map(config)
    elif  config["type"] == "loss":
        minmax = create_shapefile_from_loss_map(config)
    else:
        print "unknown map type: '%s'" % config["type"]
        sys.exit(104)

    if minmax:
        print "RESULT: %s" % str(minmax)


if __name__ == '__main__':
    main(sys.argv)
