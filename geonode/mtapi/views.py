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
import pprint
import simplejson
import subprocess
import tempfile

from django.http import HttpResponse, Http404, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from geonode.mtapi.models import OqUser, Upload, Input


@csrf_exempt
def input_upload_result(request, upload_id):
    """This handles a collection of input files uploaded by the GUI user."""
    print("upload_id: %s\n" % upload_id)
    if request.method == "GET":
        [upload] = Upload.objects.filter(id=int(upload_id))
        if upload.status == "in-progress":
            raise Http404
        else:
            result = prepare_result(upload)
            if upload.status == "failed":
                return HttpResponse(result, status=500, mimetype="text/html")
            else:
                return HttpResponse(result, mimetype="text/html")
    else:
        raise Http404


@csrf_exempt
def input_upload(request):
    """This handles a collection of input files uploaded by the GUI user."""
    print("request.FILES: %s\n" % pprint.pformat(request.FILES))
    if request.method == "POST":
        upload = handle_upload()
        for f in request.FILES.getlist('input_files'):
            handle_uploaded_file(upload, f)
        load_source_files(upload)
        return HttpResponse(prepare_result(upload), mimetype="text/html")
    else:
        raise Http404


def prepare_result(upload):
    """Prepare the result dictionary that is to be returned in json form."""
    status_translation = dict(failed="failure", succeeded="success")
    msg = dict(upload.UPLOAD_STATUS_CHOICES)[upload.status]
    result = dict(status=status_translation[upload.status], msg=msg,
                  upload=upload.id)
    return simplejson.dumps(result)


def handle_upload():
    """Create a directory for the files, return `Upload` object."""
    user = OqUser.objects.filter(user_name="openquake")[0]
    path = tempfile.mkdtemp(dir=settings.OQ_UPLOAD_DIR)
    os.chmod(path, 0777)
    upload = Upload(owner=user, path=path, status="created", job_pid=0)
    upload.save()
    return upload


def handle_uploaded_file(upload, f):
    """Store a single uploaded file on disk and in the database."""
    size = 0
    chunk_counter = 0
    input_type = None
    path = "%s/%s" % (upload.path, f.name)
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
    print(input)
    return input


def detect_input_type(chunk):
    """Detect and return the input file type."""
    tags = ("<sourceModel", "<vulnerabilityModel", "<exposurePortfolio",
            "<logicTreeSet")
    types = ("source", "vulnerability", "exposure", "ltree")
    type_dict = dict(zip(tags, types))
    for k, v in type_dict.iteritems():
        if chunk.find(k) >= 0:
            return v
    return "unknown"


def load_source_files(upload):
    """Load the source files into the database."""
    args = [settings.NRML_RUNNER_PATH, "--db", settings.OQ_DB_NAME,
            "-U", settings.OQ_DB_USER, "-W", settings.OQ_DB_PASSWORD,
            "-u", str(upload.id), "--host", settings.OQ_DB_HOST]
    print("nrml loader args: %s\n" % pprint.pformat(args))
    pid = subprocess.Popen(args).pid
    upload.status = "in-progress"
    upload.job_pid = pid
    upload.save()


@csrf_exempt
def run_oq_job(request):
    """
    This starts an OpenQuake engine job with the user supplied parameters.
    """
    print("name = %s" % __name__)
    print("request: %s\n" % pprint.pformat(request))
    if request.method == "POST":
        return HttpResponse(
            {"status": "success", "msg": "Calculation started", "id": 123})
    else:
        raise Http404
