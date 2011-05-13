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


CLASSICAL_DEFAULTS = {
    'general': {},  # there are no default params in general
    'HAZARD': {
        'HAZARD_CALCULATION_MODE': 'Classical',
        'SOURCE_MODEL_LT_RANDOM_SEED': 23,
        'GMPE_LT_RANDOM_SEED': 5,
        'MAXIMUM_DISTANCE': 200.0,
        'WIDTH_OF_MDF_BIN': 0.1,
        'DAMPING': 5.0,
        'REFERENCE_DEPTH_TO_2PT5KM_PER_SEC_PARAM': 5.0,
        'SADIGH_SITE_TYPE': 'Rock',
        'INCLUDE_AREA_SOURCES': 'true',
        'TREAT_AREA_SOURCE_AS': 'Point Sources',
        'AREA_SOURCE_DISCRETIZATION': 0.1,
        'AREA_SOURCE_MAGNITUDE_SCALING_RELATIONSHIP': 'W&C 1994 Mag-Length Rel.',
        'INCLUDE_GRID_SOURCES': 'true',
        'TREAT_GRID_SOURCE_AS': 'Point Sources',
        'GRID_SOURCE_MAGNITUDE_SCALING_RELATIONSHIP': 'W&C 1994 Mag-Length Rel.',
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
        'SUBDUCTION_FAULT_MAGNITUDE_SCALING_RELATIONSHIP': 'Wells & Coppersmith (1994)',
        'SUBDUCTION_FAULT_MAGNITUDE_SCALING_SIGMA': 0.0,
        'SUBDUCTION_RUPTURE_ASPECT_RATIO': 1.5,
        'SUBDUCTION_RUPTURE_FLOATING_TYPE': 'Along strike and down dip',
        'QUANTILE_LEVELS': '0.25 0.50, 0.75',
        'COMPUTE_MEAN_HAZARD_CURVE': 'true'},
    'RISK': {
        'LOSS_CURVES_OUTPUT_PREFIX': 'classical-demo',
        'LOSS_MAP': 'loss_map.tiff',
        'LOSS_RATIO_MAP': 'loss_ratio_map.tiff',
        'RISK_CELL_SIZE': 0.0005,
        'AGGREGATE_LOSS_CURVE': 1}}


class JobConfigWriter(object):

    PARAMS_MAP = {
        'classical': CLASSICAL_DEFAULTS,
        'event-based': None,
        'deterministic': None}

    def __init__(self, path, oq_params):
        """
        
        :param path: Desired output path, including file name. Example:
            '/tmp/config.gem'

        :type oq_params: :py:class:`geonode.mtapi.models.OqParams`
        """
        self.path = path
        self.oq_params = oq_params
        self.default_params = self.PARAMS_MAP[self.oq_params.job_type]
        if self.default_params is None:
            raise ValueError("Unsupported calclulation mode: '%s'" % self.oq_params.job_type)
        

    def write(self):
        """
        write the params to a config.gem,
        return the path to the file
        """
        return self.path
