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
Run the OpenQuake engine to perform a calculation. If all goes well we will
generate a shapefile for each resulting hazard/loss map and register the
former with the geonode server.

  -h | --help       : prints this help string
       --host H     : database host machine name [default: localhost]
  -d | --db D       : database to use [default: openquake]
  -j | --jobid J    : database key of the associated oq_job record
  -U | --user U     : database user to use [default: oq_pshai_etl]
  -W | --password W : password for the database user

"""


import getopt
import glob
import logging
import os
import pprint
import re
import sys

from django.conf import settings
from geonode.mtapi import utils
from geonode.mtapi.models import OqJob, Output
from utils.oqrunner import config_writer


logger = logging.getLogger('oqrunner')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


def create_input_file_dir(config):
    """Create a directory for the engine's input files.

    The corresponding :py:class:`geonode.mtapi.models.OqJob` instance will be
    updated with the path created.

    :param dict config: a dictionary with the following configuration data:
        - host (the database host)
        - db (the database name)
        - jobid (the database key of the associated oq_job record)
        - user (the database user)
        - password (the database user password)
    :returns: the :py:class:`geonode.mtapi.models.OqJob` instance
    """
    [job] = OqJob.objects.filter(id=config["jobid"])
    job.path = os.path.join(job.oq_params.upload.path, str(job.id))
    os.mkdir(job.path)
    os.chmod(job.path, 0777)
    job.status = "running"
    job.save()
    return job


def prepare_inputs(job):
    """Prepare a config.gem file and symbolic links to the other input files.

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance in question
    """
    cw = config_writer.JobConfigWriter(job.id)
    cw.serialize()
    for input in job.oq_params.upload.input_set.all().order_by("id"):
        basename = os.path.basename(input.path)
        os.symlink(input.path, os.path.join(job.path, basename))


def run_engine(job):
    """Run the OpenQuake engine and wait for it to terminate.

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance in question
    :returns: a triple (exit code, stdout, stderr) with engine's execution
        outcome
    """
    cmds = [os.path.join(settings.OQ_ENGINE_DIR, "bin/openquake")]
    cmds.append("--config_file")
    cmds.append(os.path.join(job.path, "config.gem"))
    code, out, err = utils.run_cmd(cmds, ignore_exit_code=True)
    if code != 0:
        logging.error(err)
    return (code, out, err)


def run_calculation(config):
    """Start the OpenQuake engine in order to perform a claculation.

    This involves:
        - creating a directory EIFD for the engine's input files
        - generating the config.gem file in EIFD
        - symlinking all the input files (uploaded by the user) in EIFD
        - running the engine
        - generating a shapefile for each hazard/loss map once the engine
          finishes and register these shapefiles with the geonode server
        - creating a database record for each hazard/loss map and capture the
          associated shapefile.
    """
    job = create_input_file_dir(config)
    prepare_inputs(job)
    run_engine(job)
    process_results(job)
    register_shapefiles(job)


def register_shapefiles(job):
    """
    Register the shapefiles generated for the hazard/loss maps with
    Geoserver.

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance in question
    """
    registration_data = []
    for output in job.output_set.all().order_by("id"):
        if not output.shapefile_path:
            continue
        datastore = ("hazardmap" if output.output_type == "hazard_map"
                                 else "lossmap")
        datum = ((os.path.dirname(output.shapefile_path), datastore))
        if datum not in registration_data:
            registration_data.append(datum)

    for datum in registration_data:
        register_shapefiles_in_location(*datum)
    if registration_data:
        update_layers()


def register_shapefiles_in_location(location, datastore):
    """Register the shapefiles in the given location with the Geoserver.

    :param str location: a server-side file system path.
    :param str datastore: one of "hazardmap", "lossmap"
    """
    url = "%s/rest/workspaces/geonode/datastores/%s/external.shp?configure=all"
    url %= (settings.GEOSERVER_BASE_URL, datastore)
    commands = ["curl", "-u", "admin:@dm1n", "-XPUT", "-H",
                "Content-type: text/plain",  "-d" "file://%s" % location, url]
    code, out, err = utils.run_cmd(commands, ignore_exit_code=True)
    if code != 0:
        # Something went wrong..
        logger.error("curl returned with exit code '%s', %s" % (code, err))


def update_layers():
    """Updates the geonode layers, called after shapefile registration."""
    command = (
        "cd %s; python %s updatelayers" % (
            settings.GEONODE_BASEPATH, settings.GEONODE_DJANGOADMIN_PATH))
    code, out, err = utils.run_cmd(command, ignore_exit_code=True, shell=True)


def process_results(job):
    """Generates a shapefile for each hazard/loss map.

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance in question
    """
    maps = find_maps(job)
    for map in maps:
        process_map(map)


def process_map(map):
    """Creates shapefile from map. Updates the respective db record.

    The minimum/maximum values as well as the shapefile path/URL will be
    captured in the output's db record.

    :param map: :py:class:`geonode.mtapi.models.Output` instance in question
    """
    commands = ["%s/bin/gen_shapefile.py" % settings.OQ_APIAPP_DIR]
    commands.append("-k")
    commands.append(str(map.id))
    commands.append("-p")
    commands.append(map.path)
    commands.append("-t")
    commands.append("hazard" if map.output_type == "hazard_map" else "loss")
    code, out, err = utils.run_cmd(commands, ignore_exit_code=True)
    if code == 0:
        # All went well
        map.shapefile_path, map.min_value, map.max_value = extract_results(out)
        map.save()


def extract_results(stdout):
    """Extract the minimum/maximum value from the shapefile generator's
    standard output.

    This is what the stdout will look like in case of success:
      "RESULT: ('/path', 1.9016084306, 1.95760904991)"

    :param string stdout: the standard output produced by the shapefile
    generator.
    :returns: a ('/path', minimum, maximum) triple in case of success or None
        in case of failure.
    """
    regex = re.compile("RESULT:\s+\('([^']+)',\s+([^,]+),\s+([^)]+)\)")
    match = regex.search(stdout)
    if match:
        path, minimum, maximum = match.groups()
        return (path, float(minimum), float(maximum))


def find_maps(job):
    """Find all hazard/result maps and store information about these in the db.

    Assumption: the default output path cannot be changed from the web GUI
    (openquake/default.gem:OUTPUT_DIR = computed_output)

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance in question
    :returns: a list of :py:class:`geonode.mtapi.models.Output` instances, one
        per map.
    """
    results = []
    maps = list(sorted(glob.glob(
        "%s/*map*.xml" % os.path.join(job.path, "computed_output"))))
    maps = [(path, detect_output_type(path)) for path in maps]
    # Ignore anything that's not a hazard or loss map.
    maps = [(path, type) for path, type in maps if type in ("hazard", "loss")]
    for path, type in maps:
        output = Output(owner=job.owner, output_type="%s_map" % type,
                        oq_job=job, path=path, size=os.path.getsize(path))
        output.save()
        results.append(output)
    return results


def detect_output_type(path):
    """Detect and return the output file type.

    :param string path: the path of the output file.
    :returns: one of the following strings: "hazard", "loss" or "unknown"
    """
    # Read a chunk of the output file.
    fh = open(path, "r")
    chunk = fh.read(2048)
    fh.close()

    tags = ("<lossMap", "<hazardMap")
    types = ("loss", "hazard")
    type_dict = dict(zip(tags, types))
    for key, value in type_dict.iteritems():
        if chunk.find(key) >= 0:
            return value
    return "unknown"


# TODO: al-maisan, Sun, Mon, 16 May 2011 17:12:06 +0200
# Package the command line argument processing code below into a utility
# function.
def main(cargs):
    """Run the OpenQuake engine."""
    def strip_dashes(arg):
        """Remove leading dashes, return last portion of string remaining."""
        return arg.split('-')[-1]

    mandatory_args = ["jobid"]
    config = dict(db="openquake", host="localhost", user=None, password=None,
                  jobid=None)
    longopts = ["%s" % k if isinstance(v, bool) else "%s=" % k
                for k, v in config.iteritems()] + ["help"]
    # Translation between short/long command line arguments.
    s2l = dict(d="db", U="user", W="password", j="jobid")

    try:
        opts, _ = getopt.getopt(cargs[1:], "hd:U:W:j:", longopts)
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

    logger.info("config = %s" % pprint.pformat(config))
    pprint.pprint(config)
    run_calculation(config)


if __name__ == '__main__':
    main(sys.argv)
