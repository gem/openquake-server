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


import decimal
import math


def round_float(value):
    """
    Takes a float and rounds it to a fixed number of decimal places.

    This function makes uses of the built-in
    :py:method:`decimal.Decimal.quantize` to limit the precision.

    The 'round-half-even' algorithm is used for rounding.

    This should give us what can be considered 'safe' float values for
    geographical coordinates (to side-step precision and rounding errors).

    :type value: float

    :returns: the input value rounded to a hard-coded fixed number of decimal
    places
    """
    FLOAT_DECIMAL_PLACES = 7
    QUANTIZE_STR = '0.' + '0' * FLOAT_DECIMAL_PLACES

    return float(
        decimal.Decimal(str(value)).quantize(
            decimal.Decimal(QUANTIZE_STR),
            rounding=decimal.ROUND_HALF_EVEN))


def log_scale(lower_bound, upper_bound, n):
    """
    Generate a logarithmic scale with n elements. The input lower_bound and
    upper_bound values will be the first and last values (respectively) in the
    scale.

    NOTE: The final scale values will be rounded to a fixed number of decimal
    digits using the :py:function:`utils.round_float`.

    :param lower_bound: This will be the first value in the generated scale.
        lower_bound must be:
            * Greater than 0.0
    :param float upper_bound: This will be the last value in the generated
        scale. upper_bound must be:
            * Greater than 0.0
            * Greater than lower_bound
    :param int n: Number of elements in the scale. n must be at least 2.

    :returns: Logarithmic scale of n values starting with lower_bound and
        ending with upper_bound.
    """

    assert lower_bound > 0.0, "Lower bound must be > 0.0"
    assert upper_bound > 0.0, "Upper bound must be > 0.0"
    assert upper_bound > lower_bound, "Upper bound must be > lower_bound"
    assert n >= 2, "Scale must have at least 2 elements"

    delta = (1.0 / (n - 1)) * math.log10(upper_bound / lower_bound)

    return [round_float(lower_bound * math.pow(10, i * delta)) for i in xrange(n)]
