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


import os

from ConfigParser import ConfigParser
from geonode.mtapi import utils
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
        'STANDARD_DEVIATION_TYPE': 'Total'},  # FIXME (LB): this needs to be specified in the db, not in defaults!!!!!
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
CLASSICAL_PARAM_TRNSLTN = {
    'average': 'Average Horizontal',
    'gmroti50': 'Average Horizontal (GMRotI50)',
    'pga': 'PGA',
    'sa': 'SA',
    'pgv': 'PGV',
    'pgd': 'PGD',
    'none': 'None',
    '1-sided': '1 Sided',
    '2-sided': '2 Sided',
    }

def polygon_to_coord_string(polygon):
    """
    Derive a correctly formatted 'REGION_VERTEX' string from a
    :py:class:`django.contrib.gis.geos.polygon.Polygon`.

    This function formats a string

    :type polygon: :py:class:`django.contrib.gis.geos.polygon.Polygon`

    :returns: String of coordinate points, in the order of lon, lat. Example::
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


class JobConfigWriter(object):

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
        'classical': {'foo': 'bar'},
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

        # These two will be assigned values once job data is read from the
        # database (when 'write' is called)
        self.default_params = None
        self.input_params = None
        self.user_params = None
        self.output_path = None
        self.output_fh = None

    def write(self):
        """
        Write all parameters to the specified config file.

        In order for the write to complete, you must call :py:meth:`close` to
        flush and close the output file handle.

        :returns: path of the output file
        """

        def load_job_params_upload():
            """
            Load the relevent oq_job, oq_params, and upload records from the
            db.

            :returns: 3-tuple of:
                (:py:class:`geonode.mtapi.models.OqJob`,
                 :py:class:`geonode.mtapi.models.OqParams`,
                 :py:class:`geonode.mtapi.models.Upload`)
            """ 
            # get the relevant oq_job, oq_params, and upload records
            oq_job = models.OqJob.objects.using(
                utils.dbn()).filter(id=self.job_id)[0]
            oq_params = models.OqParams.objects.using(
                utils.dbn()).filter(id=oq_job.oq_params_id)[0]
            upload = models.Upload.objects.using(
                utils.dbn()).filter(id=oq_params.upload_id)[0]

            return oq_job, oq_params, upload

        oq_job, oq_params, upload = load_job_params_upload()

        # Set the default, input, and user-speficied param maps for this job
        # type.
        self.default_params = \
            self.DEFAULT_PARAMS_MAP.get(oq_params.job_type, None)
        self.input_params = \
            self.INPUT_PARAMS_MAP.get(oq_params.job_type, None)
        self.user_params = self.USER_PARAMS_MAP.get(oq_params.job_type, None)

        # explicit failure if something is wrong
        if not all([self.default_params, self.input_params, self.user_params]):
            error = "Unsupported calculation mode: %s" % oq_params.job_type
            raise ValueError(error)

        # prepare the output file
        self.output_path = os.path.join(
            upload.path, str(oq_job.id), self.CONFIG_FILE_NAME)
        self.output_fh = open(self.output_path, 'w')

        # first, write the default params for this job type
        self._write_default_params()

        # now write params associated with input files for the job upload
        self._write_input_params(upload)

        # now write the user-specified params
        self._write_input_params(oq_params)
        if oq_params.job_type == 'classical':
            self._write_classical_user_params(oq_params)
        elif oq_param.job_type == 'event_based':
            pass
        elif oq_params.job_type == 'deterministic':
            pass
        else:
            raise ValueError("Unknown calculation mode %s" % oq_params.job_type)

        # finally, write the the output file handle
        self.cfg_parser.write(self.output_fh)

        return self.output_path

    def _write_default_params(self):
        """
        Given a job type, write the default parameters to the config file. It
        assumed that self.default_params is set prior to this method being
        called.
        """
        for section in self.default_params.keys():
            if not self.cfg_parser.has_section(section):
                self.cfg_parser.add_section(section)

            section_dict = self.default_params[section]

            for key, val in section_dict.items():
                self.cfg_parser.set(section, key, val)

    def _write_input_params(self, upload):
        """
        Write the parameters associated with input files. It is assumed that
        self.input_params is set prior to this method being called.

        For example, if we have the input file 'vulnerability.xml' which
        a vulnerability model, we would write the following to the config file:
            VULNERABILITY = vulnerability.xml

        :param upload: :py:class:`geonode.mtapi.models.Upload` instance
        """
        for section in self.input_params.keys():
            if not self.cfg_parser.has_section(section):
                self.cfg_parser.add_section(section)

            section_dict = self.input_params[section]

            for key, input_type in section_dict.items():
                pass
            # FIXME (LB): I cannot for the life of me figure out why
            # I have to specify upload=upload.id, rather than
            # upload_id=upload.id, which is the case with all of the other
            # models.
            # For some reason, this works. WTF?
            input_file = models.Input.objects.using(utils.dbn()).filter(
                upload=upload.id, input_type=input_type)[0]

            file_name = os.path.basename(input_file.path)
            self.cfg_parser.set(section, key, file_name)

    def _write_user_params(self, oqparams):
        """
        Write attributes from an OqParams object to the config file. It is
        assumed that self.TODO is set prior to this method being called.

        :param oqparams: :py:class:`geonode.mtapi.models.OqParams` instance
        """

    def _write_classical_user_params(self, oqp):
        """
        Write the params specified by the user/ui.

        TODO(LB): This is super ugly and hack-ish. It's just the first take
        so I can get it working. I'll clean this up later, I promise.
        """
        sec = 'general'
        cp = self.cfg_parser
        cp.set(sec, 'REGION_GRID_SPACING', oqp.region_grid_spacing)
        cp.set(sec, 'REGION_VERTEX', polygon_to_coord_string(oqp.region))

        sec = 'HAZARD'
        cp.set(sec, 'MINIMUM_MAGNITUDE', oqp.min_magnitude)
        cp.set(sec, 'INVESTIGATION_TIME', oqp.investigation_time)
        cp.set(sec, 'COMPONENT', CLASSICAL_PARAM_TRNSLTN[oqp.component])
        cp.set(sec, 'INTENSITY_MEASURE_TYPE', CLASSICAL_PARAM_TRNSLTN[oqp.imt])
        cp.set(sec, 'GMPE_TRUNCATION_TYPE', CLASSICAL_PARAM_TRNSLTN[oqp.truncation_type])
        cp.set(sec, 'TRUNCATION_LEVEL', int(oqp.truncation_level))  # FIXME: need to change this to an int in the db
        cp.set(sec, 'REFERENCE_VS30_VALUE', oqp.reference_vs30_value)

        # TODO: make this a module-level util function
        float_list_to_str = lambda flt_list, sep: sep.join([str(x) for x in flt_list])

        cp.set(sec, 'INTENSITY_MEASURE_LEVELS', float_list_to_str(oqp.imls, ', '))
        cp.set(sec, 'POES_HAZARD_MAPS', float_list_to_str(oqp.poes, ' '))
        cp.set(sec, 'NUMBER_OF_LOGIC_TREE_SAMPLES', oqp.realizations)

        sec = 'RISK'
        # this one is the same as POES_HAZARD_MAPS
        cp.set(sec, 'CONDITIONAL_LOSS_POE', float_list_to_str(oqp.poes, ' '))

    def close(self):
        """
        Close the output file handle.
        """
        if self.output_fh is not None:
            self.output_fh.close()
