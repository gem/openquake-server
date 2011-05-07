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


import logging
import os
import pprint
import simplejson
import tempfile

from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from openquake.models import OqUser, Upload, Input


logging.basicConfig(level=logging.DEBUG)


@csrf_exempt
def input_upload(request):
    """This handles a collection of input files uploaded by the GUI user."""
    pprint.pprint(request.FILES)
    if request.method == "POST":
        upload = handle_upload()
        for f in request.FILES.getlist('file'):
            handle_uploaded_file(upload, f)
        return HttpResponse(prepare_result(upload))
    else:
        raise Http404


def prepare_result(upload):
    """Prepare the result dictionary that is to be returned in json form."""
    result = dict(status="success", msg="Model upload successful",
                  upload=upload.id)
    files = []
    for input in upload.input_set.all():
        files.append(dict(id=input.id, name=os.path.basename(input.path)))
    result['files']=files
    return simplejson.dumps(result)


def handle_upload():
    """Create a directory for the files, return `Upload` object."""
    user = OqUser.objects.filter(user_name='openquake')[0]
    path = tempfile.mkdtemp(dir="/var/spool/openquake")
    os.chmod(path, 0777)
    upload = Upload(owner=user, path=path)
    upload.save()
    return upload


def handle_uploaded_file(upload, f):
    """Store a single uploaded file on disk and in the database."""
    size = 0
    chunk_counter = 0
    input_type = None
    path = "%s/%s" % (upload.path, f.name)
    logging.debug(path)
    destination = open(path, "wb+")
    for chunk in f.chunks():
        destination.write(chunk)
        size += len(chunk)
        chunk_counter += 1
        if chunk_counter == 1:
            input_type = detect_input_type(chunk)
    destination.close()
    input = Input(upload=upload, owner=upload.owner, size=size, path=path,
                  input_type=input_type)
    input.save()
    return input


def detect_input_type(chunk):
    """Detect and return the input file type."""
    tags = ("<sourceModel", "<vulnerabilityModel", "<exposurePortfolio",
            "<logicTreeSet")
    types = ("source", "vulnerability", "exposure", "lt-source")
    type_dict = dict(zip(tags, types))
    for k, v in type_dict.iteritems():
        if chunk.find(k) >= 0:
            return v
