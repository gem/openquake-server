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
from django.utils.encoding import smart_str


class Organization(models.Model):
    name = models.TextField()
    address = models.TextField(null=True)
    url = models.TextField(null=True)
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    def __str__(self):
        return smart_str(":organization: %s" % self.name)
    class Meta:
        db_table = 'admin\".\"organization'


class OqUser(models.Model):
    user_name = models.TextField()
    full_name = models.TextField()
    organization = models.ForeignKey(Organization)
    data_is_open = models.BooleanField()
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    def __str__(self):
        return smart_str(":oq_user: %s (%s)" % (self.full_name, self.user_name))
    class Meta:
        db_table = 'admin\".\"oq_user'


class Upload(models.Model):
    owner = models.ForeignKey(OqUser)
    path = models.TextField(unique=True)
    UPLOAD_STATUS_CHOICES = (
        (u"pending", u"Files saved to disk, upload/input records "
                     u"added to database"),
        (u"running", u"Upload processing started"),
        (u"failed", u"Processing of uploaded files failed"),
        (u"succeeded", u"All uploaded files processed"),
    )
    status = models.TextField(choices=UPLOAD_STATUS_CHOICES)
    job_pid = models.PositiveIntegerField()
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    def __str__(self):
        return smart_str(":upload %s: (%s)" % (self.id, self.path))
    class Meta:
        db_table = 'uiapi\".\"upload'


class Input(models.Model):
    owner = models.ForeignKey(OqUser)
    upload = models.ForeignKey(Upload)
    path = models.TextField(unique=True)
    INPUT_TYPE_CHOICES = (
        (u"unknown", u"Source model file"),
        (u"source", u"Source model file"),
        (u"ltree", u"GMPE logic tree"),
        (u"exposure", u"Exposure file"),
        (u"vulnerability", u"Vulnerability file"),
    )
    input_type = models.TextField(choices=INPUT_TYPE_CHOICES)
    size = models.PositiveIntegerField()
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    def __str__(self):
        return smart_str(
            ":input: %s, %s, %s" % (self.input_type, self.path, self.size))
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
    job_type = models.TextField(choices=JOB_TYPE_CHOICES)
    upload = models.ForeignKey(Upload)
    region_grid_spacing = models.FloatField()
    min_magnitude = models.FloatField(null=True)
    investigation_time = models.FloatField(null=True)
    COMPONENT_CHOICES = (
        (u"average", u"Average horizontal"),
        (u"gmroti50", u"Average horizontal (GMRotI50)"),
    )
    component = models.TextField(choices=COMPONENT_CHOICES)
    IMT_CHOICES = (
        (u"pga", u"Peak ground acceleration"),
        (u"sa", u"Spectral acceleration"),
        (u"pgv", u"Peak ground velocity"),
        (u"pgd", u"Peak ground displacement"),
    )
    imt = models.TextField(choices=IMT_CHOICES)
    period = models.FloatField(null=True)
    TRUNCATION_TYPE_CHOICES = (
        (u"none", u"None"),
        (u"1-sided", u"One-sided"),
        (u"2-sided", u"Two-sided"),
    )
    truncation_type = models.TextField(choices=TRUNCATION_TYPE_CHOICES)
    truncation_level = models.FloatField()
    reference_vs30_value = models.FloatField()
    imls = FloatArrayField(null=True, verbose_name="Intensity measure levels")
    poes = FloatArrayField(
        null=True, verbose_name="Probabilities of exceedence")
    realizations = models.PositiveIntegerField(
        null=True, verbose_name="Number of logic tree samples")
    histories = models.PositiveIntegerField(
        null=True, verbose_name="Number of seismicity histories")
    gm_correlated = models.NullBooleanField(
        null=True, verbose_name="Ground motion correlation flag")

    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    region = models.PolygonField()
    class Meta:
        db_table = 'uiapi\".\"oq_params'


class OqJob(models.Model):
    owner = models.ForeignKey(OqUser)
    description = models.TextField()
    JOB_TYPE_CHOICES = (
        (u"classical", u"Classical PSHA calculation"),
        (u"probabilistic", u"Probabilistic calculation"),
        (u"deterministic", u"Deterministic calculation"),
    )
    job_type = models.TextField(choices=JOB_TYPE_CHOICES)
    JOB_STATUS_CHOICES = (
        (u"pending", u"OpenQuake engine input data saved"),
        (u"running", u"Calculation started"),
        (u"failed", u"Calculation failed"),
        (u"succeeded", u"Calculation succeeded"),
    )
    status = models.TextField(choices=JOB_STATUS_CHOICES)
    duration = models.PositiveIntegerField()
    job_pid = models.PositiveIntegerField()
    oq_params = models.ForeignKey(OqParams)
    last_update = models.DateTimeField(editable=False, default=datetime.utcnow)
    class Meta:
        db_table = 'uiapi\".\"oq_job'
