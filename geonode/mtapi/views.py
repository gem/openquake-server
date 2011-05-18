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
Views for the OpenQuake API endpoint, please see
    https://github.com/gem/openquake/wiki/demo-client-API
for details.
"""

import os
import pprint
import re
import simplejson
import subprocess

from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from geonode.mtapi.models import Upload, Input
from geonode.mtapi import utils


@csrf_exempt
def input_upload_result(request, upload_id):
    """This allows the GUI to poll for upload processing status.

    The request must be a HTTP GET. If the upload processing is in progress we
    return a 404. In case of succes and failure we return a 200 and a 500
    status code respectively.

    Here's an example of the json data retuned in case of success:

        {"msg": "All uploaded files processed", "status": "success", "id": 4,
         "files": [{"name": "simpleFaultModel.xml", "id": 6}]}

    :param request: the :py:class:`django.http.HttpRequest` object
    :param integer upload_id: the database key of the associated upload record
        (see also :py:class:`geonode.mtapi.models.Upload`)
    :returns: a :py:class:`django.http.HttpResponse` object with status code
        `200` and `500` if the upload processing succeeded and failed
        respectively.
    :raises Http404: when the processing of the uploaded source model files is
        still in progress or if the request is not a HTTP GET request.
    """
    print("upload_id: %s" % upload_id)
    if request.method == "GET":
        [upload] = Upload.objects.using(utils.dbn()).filter(id=int(upload_id))
        if upload.status == "running":
            processor_is_alive = utils.is_process_running(
                upload.job_pid, settings.NRML_RUNNER_PATH)
            if processor_is_alive:
                print "Upload processing in progress.."
                raise Http404
            else:
                upload.status = "failed"
                upload.save(using=utils.dbn())
                result = prepare_result(upload)
                print "Upload processing failed, process not found.."
                return HttpResponse(result, status=500, mimetype="text/html")
        else:
            result = prepare_result(upload)
            if upload.status == "failed":
                print "Upload processing failed.."
                return HttpResponse(result, status=500, mimetype="text/html")
            else:
                print "Upload processing succeeded.."
                return HttpResponse(result, mimetype="text/html")
    else:
        raise Http404


@csrf_exempt
def input_upload(request):
    """This handles a collection of input files uploaded by the GUI user.

    The request must be a HTTP POST.

    :param request: the :py:class:`django.http.HttpRequest` object
    :returns: a :py:class:`django.http.HttpResponse` object with status code
        `200` after starting an external NRML loader program that will process
        the uploaded source model files.
    :raises Http404: if the request is not a HTTP POST request.
    """
    print("request.FILES: %s\n" % pprint.pformat(request.FILES))
    if request.method == "POST":
        upload = utils.prepare_upload()
        for uploaded_file in request.FILES.getlist('input_files'):
            handle_uploaded_file(upload, uploaded_file)
        load_source_files(upload)
        return HttpResponse(prepare_result(upload, status="success"),
                            mimetype="text/html")
    else:
        raise Http404


def prepare_result(upload, status=None):
    """Prepare the result dictionary that is to be returned in json form.

    :param upload: the :py:class:`geonode.mtapi.models.Upload` instance
        associated with this upload.
    :param string status: if set overrides the `status` property of the passed
        `upload` parameter
    """
    status_translation = dict(failed="failure", succeeded="success",
                              running="running", pending="pending")
    msg = dict(upload.UPLOAD_STATUS_CHOICES)[upload.status]
    status = status_translation[upload.status] if status is None else status
    result = dict(status=status, msg=msg, id=upload.id)
    if upload.status == "succeeded":
        files = []
        srcs = upload.input_set.using(utils.dbn()).filter(input_type="source")
        for src in srcs:
            files.append(dict(id=src.id, name=os.path.basename(src.path)))
        if files:
            result['files'] = files

    return simplejson.dumps(result)


def handle_uploaded_file(upload, uploaded_file):
    """Store a single uploaded file on disk and in the database.

    :param upload: the :py:class:`geonode.mtapi.models.Upload` instance
        associated with this upload.
    :param uploaded_file: an uploaded file from the POST request
    :returns: the resulting :py:class:`geonode.mtapi.models.Input` instance
    """
    size = 0
    chunk_counter = 0
    input_type = None
    path = "%s/%s" % (upload.path, uploaded_file.name)
    destination = open(path, "wb+")
    for chunk in uploaded_file.chunks():
        destination.write(chunk)
        size += len(chunk)
        chunk_counter += 1
        if chunk_counter == 1:
            input_type = detect_input_type(chunk)
    destination.close()
    source = Input(upload=upload, owner=upload.owner, size=size, path=path,
                   input_type=input_type)
    source.save(using=utils.dbn())
    print(source)
    return source


def detect_input_type(chunk):
    """Detect and return the input file type.

    :param string chunk: the first chunk of an uploaded input file.
    :returns: one of the following strings:
        "source", "vulnerability", "exposure", "ltree" or "unknown"
    """
    gmpe_re = re.compile('<logicTreeBranchSet[^>]+uncertaintyType="gmpeModel"')
    tags = ("<sourceModel", "<vulnerabilityModel", "<exposurePortfolio")
    types = ("source", "vulnerability", "exposure")
    type_dict = dict(zip(tags, types))
    for key, value in type_dict.iteritems():
        if chunk.find(key) >= 0:
            return value
    if gmpe_re.search(chunk):
        return "lt_gmpe"
    if chunk.find("<logicTreeBranchSet") >= 0:
        return "lt_source"
    return "unknown"


def load_source_files(upload):
    """Load the source model files into the database.

    This starts an external NRML loader program in a separate process that
    loads the model data into the database in asynchronous fashion.

    :param upload: the :py:class:`geonode.mtapi.models.Upload` instance
        associated with this upload.
    :returns: the integer process ID (pid) of the child process that is running
        the NRML loader program.
    """
    config = settings.DATABASES['openquake']
    host = config["HOST"] if config["HOST"] else "localhost"
    args = [settings.NRML_RUNNER_PATH, "--db", config["NAME"],
            "-U", config["USER"], "-W", config["PASSWORD"],
            "-u", str(upload.id), "--host", host]
    print("nrml loader args: %s\n" % pprint.pformat(args))
    env = os.environ
    env["PYTHONPATH"] = settings.NRML_RUNNER_PYTHONPATH
    pprint.pprint(env)
    pid = subprocess.Popen(args, env=env).pid
    upload.status = "running"
    upload.job_pid = pid
    upload.save(using=utils.dbn())
    print "pid = %s" % pid
    return pid


@csrf_exempt
def run_oq_job(request):
    """Starts an OpenQuake engine job with the user supplied parameters.

    The request must be a HTTP POST.

    :param request: the :py:class:`django.http.HttpRequest` object
    :raises Http404: if the request is not a HTTP POST request.
    """
    print("request: %s\n" % pprint.pformat(request))
    if request.method == "POST":
        return HttpResponse(
            {"status": "success", "msg": "Calculation started", "id": 123})
    else:
        raise Http404
