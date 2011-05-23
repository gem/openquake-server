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
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from geonode.mtapi.models import OqUser, Upload, Input
from geonode.mtapi import views


class PrepareResultTest(TestCase):
    """Tests for geonode.mtapi.views.prepare_upload_result()."""

    def test_prepare_result_with_pending_upload(self):
        """
        The json for pending uploads contains no `files` array.
        """
        user = OqUser.objects.filter(user_name="openquake")[0]
        upload = Upload(owner=user, path="/a/1", status="pending", job_pid=0)
        Input(upload=upload, owner=upload.owner, size=11,
              path=upload.path + "/a", input_type="source")
        self.assertEqual("", views.prepare_upload_result(upload))
