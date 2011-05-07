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


from datetime import datetime
from django.contrib.gis.db import models


class Organization(models.Model):
    name = models.CharField()
    address = models.CharField(null=True)
    url = models.CharField(null=True)
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    class Meta:
        db_table = 'admin\".\"organization'


class OqUser(models.Model):
    user_name = models.CharField()
    full_name = models.CharField()
    organization = models.ForeignKey(Organization)
    data_is_open = models.BooleanField()
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    class Meta:
        db_table = 'admin\".\"oq_user'


class Upload(models.Model):
    owner = models.ForeignKey(OqUser)
    path = models.CharField()
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    class Meta:
        db_table = 'uiapi\".\"upload'


class Input(models.Model):
    owner = models.ForeignKey(OqUser)
    upload = models.ForeignKey(Upload)
    path = models.CharField()
    INPUT_TYPE_CHOICES = (
        (u"source", u"Source model file"),
        (u"lt-source", u"Source logic tree"),
        (u"lt-gmpe", u"GMPE logic tree"),
        (u"exposure", u"Exposure file"),
        (u"vulnerability", u"Vulnerability file"),
    )
    input_type = models.CharField(choices=INPUT_TYPE_CHOICES)
    size = models.PositiveIntegerField()
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    class Meta:
        db_table = 'uiapi\".\"input'


class FloatArrayField(models.Field):
    """This field models a postgres `float` array."""

    def db_type(self, connection):
        return 'float[]'

    def get_prep_value(self, value):
        return "{" + ', '.join(str(v) for v in value) + "}"


class OqParams(models.Model):
    JOB_TYPE_CHOICES = (
        (u"classical", u"Classical PSHA calculation"),
        (u"probabilistic", u"Probabilistic calculation"),
        (u"deterministic", u"Deterministic calculation"),
    )
    job_type = models.CharField(choices=JOB_TYPE_CHOICES)
    upload = models.ForeignKey(Upload)
    region_grid_spacing = models.FloatField()
    min_magnitude = models.FloatField(null=True)
    investigation_time = models.FloatField(null=True)
    COMPONENT_CHOICES = (
        (u"average", u"Average horizontal"),
        (u"gmroti50", u"Average horizontal (GMRotI50)"),
    )
    component = models.CharField(choices=COMPONENT_CHOICES)
    IMT_CHOICES = (
        (u"pga", u"Peak ground acceleration"),
        (u"sa", u"Spectral acceleration"),
        (u"pgv", u"Peak ground velocity"),
        (u"pgd", u"Peak ground displacement"),
    )
    imt = models.CharField(choices=IMT_CHOICES)
    period = models.FloatField(null=True)
    TRUNCATION_TYPE_CHOICES = (
        (u"none", u"None"),
        (u"1-sided", u"One-sided"),
        (u"2-sided", u"Two-sided"),
    )
    truncation_type = models.CharField(choices=TRUNCATION_TYPE_CHOICES)
    truncation_level = models.FloatField()
    reference_vs30_value = models.FloatField()
    imls = FloatArrayField(null=True, verbose_name="Intensity measure levels")
    poes = FloatArrayField(
        null=True, verbose_name="Probabilities of exceedence")
    realizations = models.PositiveIntegerField(
        null=True, verbose_name="Number of logic tree samples")
    histories = models.PositiveIntegerField(
        null=True, verbose_name="Number of seismicity histories")
    gm_correlated = models.BooleanField(
        null=True, verbose_name="Ground motion correlation flag")

    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    region = models.PolygonField()
    class Meta:
        db_table = 'uiapi\".\"oq_params'


class OqJob(models.Model):
    owner = models.ForeignKey(OqUser)
    description = models.CharField()
    JOB_TYPE_CHOICES = (
        (u"classical", u"Classical PSHA calculation"),
        (u"probabilistic", u"Probabilistic calculation"),
        (u"deterministic", u"Deterministic calculation"),
    )
    job_type = models.CharField(choices=JOB_TYPE_CHOICES)
    STATUS_TYPE_CHOICES = (
        (u"created", u"OpenQuake engine job has not started yet"),
        (u"in-progress", u"OpenQuake engine job is in progress"),
        (u"failed", u"OpenQuake engine job has failed"),
        (u"succeeded", u"OpenQuake engine job ran successfully"),
    )
    status_type = models.CharField(choices=STATUS_TYPE_CHOICES)
    duration = models.IntegerField()
    oq_params = models.ForeignKey(OqParams)
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    class Meta:
        db_table = 'uiapi\".\"oq_job'
