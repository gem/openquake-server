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
Run the OpenQuake engine to perform a calculation. If all goes well the
hazard/loss map data will either be written to
    - the database (default behaviour) or to
    - shapefiles and these be registered with the geonode server

  -h | --help       : prints this help string
  -j | --jobid J    : database key of the associated oq_job record
  -s | --shapefile  : write map data to shapefiles as opposed to database
"""


import getopt
import glob
import logging
import os
import pprint
import re
import subprocess
import sys

from urlparse import urljoin

from django.conf import settings
from geonode.mtapi.models import OqJob, Output
from geonode.mtapi import view_utils
from utils.oqrunner import config_writer


logger = logging.getLogger('oqrunner')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
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
        - jobid (the database key of the associated oq_job record)
        - shapefile (whether map data should be written to shapefiles)
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
    for an_input in job.oq_params.upload.input_set.all().order_by("id"):
        basename = os.path.basename(an_input.path)
        os.symlink(an_input.path, os.path.join(job.path, basename))


def run_engine(job):
    """Run the OpenQuake engine and wait for it to terminate.

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance in question
    :returns: a triple (exit code, stdout, stderr) with engine's execution
        outcome
    """
    logger.info("> run_engine")
    cmds = [os.path.join(settings.OQ_ENGINE_DIR, "bin/openquake")]
    cmds.append("--config_file")
    cmds.append(os.path.join(job.path, "config.gem"))
    logger.info("cmds: %s" % cmds)
    code, out, err = view_utils.run_cmd(cmds, ignore_exit_code=True)
    logger.info("code: '%s'" % code)
    logger.info("out: '%s'" % out)
    if code != 0:
        logger.error(err)
    logger.info("< run_engine")
    return (code, out, err)


def run_calculation(config):
    """Start the OpenQuake engine in order to perform a claculation.

    This involves:
        - creating a directory EIFD for the engine's input files
        - generating the config.gem file in EIFD
        - symlinking all the input files (uploaded by the user) in EIFD
        - running the engine
        - creating a database record for each hazard/loss map
        - write hazard/loss map data to database or to shapefiles (and
          register the latter with the geonode server)
    """
    job = create_input_file_dir(config)
    prepare_inputs(job)
    code, _, _ = run_engine(job)
    if code != 0:
        logger.error("OpenQuake engine exited with code %s, aborting.." % code)
        job.status = "failed"
        job.save()
        sys.exit(code)
    process_results(job, config)
    if config["shapefiles"]:
        register_shapefiles(job)
    job.status = "succeeded"
    job.save()


def register_shapefiles(job):
    """
    Register the shapefiles generated for the hazard/loss maps with
    Geoserver.

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance in question
    """
    logger.info("> register_shapefiles")
    registration_data = []
    for output in job.output_set.all().order_by("id"):
        if not output.shapefile_path:
            continue
        datastore = ("hazardmap" if output.output_type == "hazard_map"
                                 else "lossmap")
        datastore = "%s-%s" % (job.id, datastore)
        datum = ((os.path.dirname(output.shapefile_path), datastore))
        if datum not in registration_data:
            registration_data.append(datum)

    logger.info("registration_data: %s" % registration_data)
    for datum in registration_data:
        register_shapefiles_in_location(*datum)
    if registration_data:
        update_layers()
    logger.info("< register_shapefiles")


def register_shapefiles_in_location(location, datastore):
    """Register the shapefiles in the given location with the Geoserver.

    :param str location: a server-side file system path.
    :param str datastore: one of "<job_id>-hazardmap", "<job_id>-lossmap"
    """
    logger.info("> register_shapefiles_in_location")
    url = urljoin(
        settings.GEOSERVER_BASE_URL,
        "rest/workspaces/geonode/datastores/%s/external.shp?configure=all")
    url %= datastore
    command = ("curl -v -u 'admin:@dm1n' -XPUT -H 'Content-type: text/plain' "
               "-d '%s' '%s'" % (urljoin('file://', location), url))
    logger.info("location: '%s'" % location)
    logger.info("url: '%s'" % url)
    logger.info("command: %s" % command)

    code, out, err = view_utils.run_cmd(
        command, ignore_exit_code=True, shell=True)

    logger.info("code: '%s'" % code)
    logger.info("out: '%s'" % out)
    logger.info("err: '%s'" % err)
    logger.info("< register_shapefiles_in_location")


def update_layers():
    """Updates the geonode layers, called after shapefile registration."""
    logger.info("> update_layers")

    command = settings.OQ_UPDATE_LAYERS_PATH
    logger.info("command: %s" % command)

    if view_utils.is_process_running(pattern=command):
        logger.info("A process that updates layers is already running..")
        return

    # Our default python path breaks the virtualenv running the "updatelayers"
    # command.
    python_path = os.environ["PYTHONPATH"]
    logger.info("PYTHONPATH: '%s'" % python_path)
    os.environ["PYTHONPATH"] = ""

    # Run the "updatelayers" command in asynchronous fashion.
    subprocess.Popen(command, env=os.environ)

    # Restore python path.
    os.environ["PYTHONPATH"] = python_path
    logger.info("< update_layers")


def process_results(job, config):
    """Generates a shapefile for each hazard/loss map.

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance in question
    """
    maps = find_maps(job)
    for a_map in maps:
        process_map(a_map, config)


def process_map(a_map, config):
    """Creates shapefile from a map. Updates the respective db record.

    The minimum/maximum values as well as the shapefile path/URL will be
    captured in the output's db record.

    :param a_map: :py:class:`geonode.mtapi.models.Output` instance in question
    """
    commands = ["%s/bin/map_transformer.py" % settings.OQ_APIAPP_DIR]
    commands.append("-k")
    commands.append(str(a_map.id))
    commands.append("-p")
    commands.append(a_map.path)
    if config.get("shapefile"):
        commands.append("--shapefile")
    commands.append("-t")
    commands.append("hazard" if a_map.output_type == "hazard_map" else "loss")
    code, out, _ = view_utils.run_cmd(commands, ignore_exit_code=True)
    if code == 0:
        # All went well
        if config.get("shapefile"):
            a_map.shapefile_path, a_map.min_value, a_map.max_value = \
                extract_results(out)
        else:
            _, a_map.min_value, a_map.max_value = extract_results(out)
        a_map.save()


def extract_results(stdout):
    """Extract the minimum/maximum value from the shapefile generator's
    standard output.

    This is what the stdout will look like in case of success:
      - for shapefiles:
            "RESULT: ('/path', 1.9016084306, 1.95760904991)"
      - for hazard/loss map data in database
            "RESULT: (99, 2.8016084306, 2.75760904991)"

    :param string stdout: the standard output produced by the shapefile
    generator.
    :returns: a ('/path', minimum, maximum) triple in case of success or None
        in case of failure.
    """
    shapefile_regex = re.compile(
        "RESULT:\s+\('([^']+)',\s+([^,]+),\s+([^)]+)\)")
    database_regex = re.compile(
        "RESULT:\s+\((\d+),\s+([^,]+),\s+([^)]+)\)")
    match = shapefile_regex.search(stdout)
    if match:
        path, minimum, maximum = match.groups()
        return (path, float(minimum), float(maximum))
    match = database_regex.search(stdout)
    if match:
        map_data_key, minimum, maximum = match.groups()
        return (int(map_data_key), float(minimum), float(maximum))


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
    maps = [(path, map_type) for path, map_type in maps
            if map_type in ("hazard", "loss")]
    for path, map_type in maps:
        output = Output(owner=job.owner, output_type="%s_map" % map_type,
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
    config = dict(jobid=None, shapefile=False)
    longopts = ["%s" % k if isinstance(v, bool) else "%s=" % k
                for k, v in config.iteritems()] + ["help"]
    # Translation between short/long command line arguments.
    s2l = dict(j="jobid", s="shapefile")

    try:
        opts, _ = getopt.getopt(cargs[1:], "hj:s", longopts)
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
