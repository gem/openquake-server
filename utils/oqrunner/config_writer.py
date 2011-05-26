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
This module provides utilities for generating OpenQuake job config files.
"""


import os

from ConfigParser import ConfigParser
from geonode.mtapi import models


CLASSICAL_DEFAULTS = {
    'general': {},  # classical has no defaults in 'general'
    'HAZARD': {
        'HAZARD_CALCULATION_MODE': 'Classical',
        'SOURCE_MODEL_LT_RANDOM_SEED': 23,
        'OUTPUT_DIR': 'computed_output',
        'GMPE_LT_RANDOM_SEED': 5,
        'MAXIMUM_DISTANCE': 200.0,
        'WIDTH_OF_MFD_BIN': 0.1,
        'DAMPING': 5.0,
        'REFERENCE_DEPTH_TO_2PT5KM_PER_SEC_PARAM': 5.0,
        'SADIGH_SITE_TYPE': 'Rock',
        'INCLUDE_AREA_SOURCES': 'true',
        'TREAT_AREA_SOURCE_AS': 'Point Sources',
        'AREA_SOURCE_DISCRETIZATION': 0.1,
        'AREA_SOURCE_MAGNITUDE_SCALING_RELATIONSHIP': \
            'W&C 1994 Mag-Length Rel.',
        'INCLUDE_GRID_SOURCES': 'true',
        'TREAT_GRID_SOURCE_AS': 'Point Sources',
        'GRID_SOURCE_MAGNITUDE_SCALING_RELATIONSHIP': \
            'W&C 1994 Mag-Length Rel.',
        'INCLUDE_FAULT_SOURCE': 'true',
        'FAULT_RUPTURE_OFFSET': 5.0,
        'FAULT_SURFACE_DISCRETIZATION': 1.0,
        'FAULT_MAGNITUDE_SCALING_RELATIONSHIP': 'Wells & Coppersmith (1994)',
        'FAULT_MAGNITUDE_SCALING_SIGMA': 0.0,
        'RUPTURE_ASPECT_RATIO': 1.5,
        'RUPTURE_FLOATING_TYPE': 'Along strike and down dip',
        'INCLUDE_SUBDUCTION_FAULT_SOURCE': 'true',
        'SUBDUCTION_FAULT_RUPTURE_OFFSET': 10.0,
        'SUBDUCTION_FAULT_SURFACE_DISCRETIZATION': 10.0,
        'SUBDUCTION_FAULT_MAGNITUDE_SCALING_RELATIONSHIP': \
            'Wells & Coppersmith (1994)',
        'SUBDUCTION_FAULT_MAGNITUDE_SCALING_SIGMA': 0.0,
        'SUBDUCTION_RUPTURE_ASPECT_RATIO': 1.5,
        'SUBDUCTION_RUPTURE_FLOATING_TYPE': 'Along strike and down dip',
        'QUANTILE_LEVELS': '0.25 0.50 0.75',
        'COMPUTE_MEAN_HAZARD_CURVE': 'true',
        'STANDARD_DEVIATION_TYPE': 'Total'},
    'RISK': {
        'RISK_CALCULATION_MODE': 'Classical PSHA',
        'LOSS_CURVES_OUTPUT_PREFIX': 'classical-demo',
        'LOSS_MAP': 'loss_map.tiff',
        'LOSS_RATIO_MAP': 'loss_ratio_map.tiff',
        'RISK_CELL_SIZE': 0.0005,
        'AGGREGATE_LOSS_CURVE': 1}}
CLASSICAL_INPUT = {
    'HAZARD': {
        'SOURCE_MODEL_LOGIC_TREE_FILE': 'lt_source',
        'GMPE_LOGIC_TREE_FILE': 'lt_gmpe'},
    'RISK': {
        'EXPOSURE': 'exposure',
        'VULNERABILITY': 'vulnerability'}}


def polygon_to_coord_string(polygon):
    """
    Derive a correctly formatted 'REGION_VERTEX' string from a
    :py:class:`django.contrib.gis.geos.polygon.Polygon`.

    NOTE: Job config files requires coordinates to be in the order lat, lon.
    However, the order of the coordinates in the input polygon object is
    lon, lat (equivalent to x, y).

    :type polygon: :py:class:`django.contrib.gis.geos.polygon.Polygon`

    :returns: String of coordinate points, in the order of lat, lon. Example::
        '38.0, -122.2, 38.0, -121.7, 37.5, -121.7, 37.5, -122.2'
    """
    # get a list of the lon,lat pairs
    # like so:
    # [(-122.2, 38.0),
    #  (-121.7, 37.5),
    #  (-122.2, 37.5),
    #  (-122.2, 38.0),
    #  (-122.2, 38.0)]
    coords = list(polygon.coords[0])

    # these polygons form a closed loop, so first and last coord are the same
    # we can ditch the last coord
    coords.pop()

    points = []
    for coord in coords:
        # reverse the order of the lon,lat values
        points.append(coord[1])
        points.append(coord[0])

    coord_str = ', '.join([str(pt) for pt in points])

    return coord_str


def float_list_to_str(float_list, delimiter):
    """
    Convert a list of floats to a string, each number separated by the
    specified delimiter.

    :returns: A string representation the list of floats joined with the
        specified string. For example, given a float_list of `[0.1, 0.2, 0.3]`
        and a delimiter of '#|', the return value will be::
        '0.1#|0.2#|0.3'
    """
    return delimiter.join([str(x) for x in float_list])


def enum_translate(value):
    """
    Translate a DB enum value to a legal value for the config file.

    For example, the COMPONENT param can have a value of 'Average Horizontal'
    or 'Average Horizontal (GMRotI50)'. In the database, these value are
    represented as 'average' and 'gmroti50', respectively.

    These enumerations are defined and maintained in the various classes in
    :py:module:`geonode.mtapi.models`.

    :param value: DB representation of a config value
    :type value: str

    :returns: config file representation of the config enum, or None if no
        match is found
    """
    enum_map = {
        'average': 'Average Horizontal',
        'gmroti50': 'Average Horizontal (GMRotI50)',
        'pga': 'PGA',
        'sa': 'SA',
        'pgv': 'PGV',
        'pgd': 'PGD',
        'none': 'None',
        'onesided': '1 Sided',
        'twosided': '2 Sided'}

    return enum_map.get(value, None)


def get_classical_user_params(oqparams):
    """
    Get a dict of the params specified by the user from the UI.

    :param oqparams: :py:class:`geonode.mtapi.models.OqParams` instance

    :returns: Dict keyed by config file section name. Each value will be
    a dict of config param/value pairs. Example::
        {'general': {
            'REGION_GRID_SPACING': 0.1,
            ... },
         'HAZARD': {'MINIMUM_MAGNITUDE': 5.0,
            ... },
         'RISK': {'CONDITIONAL_LOSS_POE': '0.01 0.10'}}
    """
    # A bit of translation is needed to convert the db 'enum' values for some
    # attributes to legal values for a config file.

    poes_str = float_list_to_str(oqparams.poes, ' ')

    params = {
        'general': {
            'REGION_GRID_SPACING': oqparams.region_grid_spacing,
            'REGION_VERTEX': polygon_to_coord_string(oqparams.region)},
        'HAZARD': {
            'MINIMUM_MAGNITUDE': oqparams.min_magnitude,
            'INVESTIGATION_TIME': oqparams.investigation_time,
            'COMPONENT': enum_translate(oqparams.component),
            'INTENSITY_MEASURE_TYPE': enum_translate(oqparams.imt),
            'GMPE_TRUNCATION_TYPE': enum_translate(oqparams.truncation_type),
            'TRUNCATION_LEVEL': oqparams.truncation_level,
            'REFERENCE_VS30_VALUE': oqparams.reference_vs30_value,
            'INTENSITY_MEASURE_LEVELS': float_list_to_str(oqparams.imls, ', '),
            'POES_HAZARD_MAPS': poes_str,
            'NUMBER_OF_LOGIC_TREE_SAMPLES': oqparams.realizations},
        'RISK': {
            'CONDITIONAL_LOSS_POE': poes_str}}

    return params


class JobConfigWriter(object):
    """
    The class provides functionality for generating an OpenQuake job config
    file by reading job information from the OpenQuake DB.

    This class makes use of the :py:module:`ConfigParser` to structure and
    populate the output file.
    """

    CONFIG_FILE_NAME = 'config.gem'
    DEFAULT_PARAMS_MAP = {
        'classical': CLASSICAL_DEFAULTS,
        'event_based': None,
        'deterministic': None}
    INPUT_PARAMS_MAP = {
        'classical': CLASSICAL_INPUT,
        'event_based': None,
        'deterministic': None}
    USER_PARAMS_MAP = {
        'classical': get_classical_user_params,
        'event_based': None,
        'deterministic': None}

    def __init__(self, job_id):
        """
        :param job_id: ID of a job stored in the uiapi.oq_job table for which
            we want to generate a job config file.
        :type job_id: int
        """
        self.job_id = job_id

        # this will be used to build the config file
        self.cfg_parser = ConfigParser()

    def serialize(self):
        """
        Write all parameters to the specified config file.

        :returns: path of the output file
        """

        def load_job_data():
            """
            Load the relevent oqjob, oqparams, and upload records from the
            db.

            :returns: 3-tuple of:
                (:py:class:`geonode.mtapi.models.OqJob`,
                 :py:class:`geonode.mtapi.models.OqParams`,
                 :py:class:`geonode.mtapi.models.Upload`)
            """
            oqjob = models.OqJob.objects.filter(id=self.job_id)[0]

            oqparams = models.OqParams.objects.filter(id=oqjob.oq_params_id)[0]

            upload = models.Upload.objects.filter(id=oqparams.upload_id)[0]

            return oqjob, oqparams, upload

        oqjob, oqparams, upload = load_job_data()

        # Set the default, input, and user-speficied param maps for this job
        # type.
        default_params = \
            self.DEFAULT_PARAMS_MAP.get(oqparams.job_type, None)
        input_params = \
            self.INPUT_PARAMS_MAP.get(oqparams.job_type, None)

        # We'll need to call specific function to extract user-specified
        # parameters from the OqParams object.
        # Each calculation mode requires slightly different parameters, so
        # we'll use different functions to extract what we need.
        user_params_fn = \
            self.USER_PARAMS_MAP.get(oqparams.job_type, None)

        # explicit failure if something is wrong, such as an expected job type
        if not all([default_params, input_params, user_params_fn]):
            error = "Unsupported calculation mode: %s" % oqparams.job_type
            raise ValueError(error)

        user_params = user_params_fn(oqparams)

        # prepare the output file
        output_path = os.path.join(oqjob.path, self.CONFIG_FILE_NAME)
        output_fh = open(output_path, 'w')

        # first, write the default params for this job type
        self._write_params(default_params)

        # then write the params specified by the user
        # (read from the OqParams object)
        self._write_params(user_params)

        # now write params associated with input files for the job upload
        self._write_input_params(upload, input_params)

        # write and close
        self.cfg_parser.write(output_fh)
        output_fh.close()

        return output_path

    def _write_params(self, params):
        """
        Given a dict of section names and param/value pairs, write them to the
        output config file. If a section does not yet exist, it will be
        created.

        Note: All parameter values will be cast as strings before they are
        written.

        :param params: A dict of params with the following structure::
            {'general': {
                'REGION_GRID_SPACING': 0.1,
                ... },
             'HAZARD': {'MINIMUM_MAGNITUDE': 5.0,
                ... },
             'RISK': {'CONDITIONAL_LOSS_POE': '0.01 0.10'}}
        """
        for section in params.keys():
            if not self.cfg_parser.has_section(section):
                self.cfg_parser.add_section(section)

            for key, val in params[section].items():
                self.cfg_parser.set(section, key, str(val))

    def _write_input_params(self, upload, input_params):
        """
        Read input file information from the OpenQuake DB (given a
        'uiapi.upload' record) and write the parameters associated with the
        input files to the config file.

        For example, if we have the input file 'vulnerability.xml' which
        represents a vulnerability model, we would write the following to the
        config file:
            VULNERABILITY = vulnerability.xml

        :param upload: :py:class:`geonode.mtapi.models.Upload` instance
        :param input_params: A dict (organized by config file sections)
            containing param/'input type' pairs. (The 'input type' corresponds
            to the value of the 'uiapi.input.input_type' column in the
            OpenQuake DB.) Example::
                {'HAZARD': {
                    'SOURCE_MODEL_LOGIC_TREE_FILE': 'lt_source',
                    'GMPE_LOGIC_TREE_FILE': 'lt_gmpe'},
                 'RISK': {
                    'EXPOSURE': 'exposure',
                    'VULNERABILITY': 'vulnerability'}}
        """
        inputs = upload.input_set.all().order_by("id")

        for section in input_params.keys():
            if not self.cfg_parser.has_section(section):
                self.cfg_parser.add_section(section)

            for key, input_type in input_params[section].items():
                input_file = inputs.filter(input_type=input_type)[0]

                file_name = os.path.basename(input_file.path)
                self.cfg_parser.set(section, key, file_name)
