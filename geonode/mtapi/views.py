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
from urlparse import urljoin

import num_utils
import utils

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from geonode.mtapi.models import Input, OqJob, OqParams, Upload


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
        [upload] = Upload.objects.filter(id=int(upload_id))
        if upload.status == "running":
            processor_is_alive = utils.is_process_running(
                upload.job_pid, settings.NRML_RUNNER_PATH)
            if processor_is_alive:
                print "Upload processing in progress.."
                raise Http404
            else:
                upload.status = "failed"
                upload.save()
                result = prepare_upload_result(upload)
                print "Upload processing failed, process not found.."
                return HttpResponse(result, status=500, mimetype="text/html")
        else:
            result = prepare_upload_result(upload)
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
        return HttpResponse(prepare_upload_result(upload, status="success"),
                            mimetype="text/html")
    else:
        raise Http404


def prepare_upload_result(upload, status=None):
    """Prepare the result dictionary that is to be returned in json form.

    :param upload: the :py:class:`geonode.mtapi.models.Upload` instance
        associated with this upload.
    :param string status: if set overrides the `status` property of the passed
        `upload` parameter
    """
    status_translation = dict(failed="failure", succeeded="success",
                              running="running", pending="pending")
    msg = dict(upload.UPLOAD_STATUS_CHOICES)[upload.status]
    status = status if status else status_translation[upload.status]
    result = dict(status=status, msg=msg, id=upload.id)
    if upload.status == "succeeded":
        files = []
        srcs = upload.input_set.filter(input_type="source")
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
    source.save()
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
    config = settings.DATABASES['default']
    host = config["HOST"] if config["HOST"] else "localhost"
    args = [settings.NRML_RUNNER_PATH, "--db", config["NAME"],
            "-U", config["USER"], "-W", config["PASSWORD"],
            "-u", str(upload.id), "--host", host]
    env = os.environ
    env["PYTHONPATH"] = settings.APIAPP_PYTHONPATH
    pid = subprocess.Popen(args, env=env).pid
    upload.status = "running"
    upload.job_pid = pid
    upload.save()
    print "pid = %s" % pid
    return pid


@csrf_exempt
def run_oq_job(request):
    """Starts an OpenQuake engine job with the user supplied parameters.

    The request must be a HTTP POST.

    :param request: the :py:class:`django.http.HttpRequest` object
    :raises Http404: if the request is not a HTTP POST request.
    """
    print("request: %s\n" % pprint.pformat(request.POST))
    if request.method == "POST":
        params = request.POST
        params = simplejson.loads(params.keys().pop())
        job = prepare_job(params)
        start_job(job)
        return HttpResponse(simplejson.dumps({
            "status": "success", "msg": "Calculation started", "id": job.id}))
    else:
        raise Http404


def start_job(job):
    """Start the OpenQuake engine in order to perform a calculation.

    The OpenQuake engine run may take a while and is hence started
    asynchronously in a separate process.

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance in question
    :returns: the integer process ID (pid) of the child process that is running
        the oqrunner.py tool.
    """
    print "> start_job"
    env = os.environ
    env["PYTHONPATH"] = settings.APIAPP_PYTHONPATH
    args = [settings.OQRUNNER_PATH, "-j", str(job.id)]
    proc = subprocess.Popen(args, env=env)
    job.job_pid = proc.pid
    job.save()
    print "< start_job"
    return proc.pid


def prepare_job(params):
    """Create a job with the associated upload and the given parameters.

    :param dict params: the parameters will look as follows:
        {"model":"openquake.calculationparams",
         "upload": 23,
         "fields":
             {"job_type": "classical",
              "region_grid_spacing": 0.1,
              "min_magnitude": 5,
              "investigation_time": 50,
              "component": "average",
              "imt": "pga",
              "period": 1,
              "truncation_type": "none",
              "truncation_level": 3,
              "reference_v30_value": 800,
              "imls": [0.2,0.02,0.01],
              "poes": [0.2,0.02,0.01],
              "realizations": 6,
              "histories": 1,
              "gm_correlated": False,
              "region":"POLYGON((
                 16.460737205888 41.257786872643,
                 16.460898138429 41.257786872643,
                 16.460898138429 41.257923984376,
                 16.460737205888 41.257923984376,
                 16.460737205888 41.257786872643))"}}

        Please see the "hazard_risk_calc" section of
        https://github.com/gem/openquake/wiki/demo-client-API for details on
        the parameters.

    :returns: a :py:class:`geonode.mtapi.models.OqJob` instance
    """
    print "> prepare_job"

    upload = params.get("upload")
    if not upload:
        print "No upload database key supplied"

    upload = Upload.objects.get(id=upload)
    if not upload:
        print "No upload record found"
    else:
        print upload

    oqp = OqParams(upload=upload)
    trans_tab = dict(reference_v30_value="reference_vs30_value")
    value_trans_tab = {
        "truncation_type": {
            "1-sided": "onesided",
            "2-sided": "twosided"}}
    param_names = (
        "job_type", "region_grid_spacing", "min_magnitude",
        "investigation_time", "component", "imt", "period", "truncation_type",
        "truncation_level", "reference_v30_value", "imls", "poes",
        "realizations", "histories", "gm_correlated")

    ignore = dict(
        classical=set(["period", "histories", "gm_correlated"]),
        deterministic=set(), event_based=set())

    job_type = params["fields"]["job_type"]
    assert job_type in ("classical", "deterministic", "event_based"), \
        "invalid job type: '%s'" % job_type

    for param_name in param_names:
        if param_name == "region" or param_name in ignore[job_type]:
            continue
        # Take care of differences in property names.
        property_name = trans_tab.get(param_name, param_name)
        value = params["fields"].get(param_name)
        if value:
            # Is there a need to translate the value?
            trans = value_trans_tab.get(property_name)
            if trans:
                value = trans.get(value, value)
            setattr(oqp, property_name, value)

    region = params["fields"].get("region")

    if region:
        oqp.region = GEOSGeometry(region)

    oqp.save()
    print oqp

    job = OqJob(oq_params=oqp, owner=upload.owner,
                job_type=params["fields"]["job_type"])
    job.save()
    print job

    print "< prepare_job"
    return job


@csrf_exempt
def oq_job_result(request, job_id):
    """This allows the GUI to poll for OpenQuake job status.

    The request must be a HTTP GET. If the OpenQuake job is in progress we
    return a 404. In case of succes and failure we return a 200 and a 500
    status code respectively.

    Here's an example of the json data retuned in case of success:

    { "status": "success", "msg": "Calculation succeeded", "id": 123,
      "files": [{
        "id": 77, "name": "loss-map-0fcfdbc7.xml", "type": "loss map",
        "min": 2.718281, "max": 3.141593,
        "layer": {
            "ows": "http://gemsun02.ethz.ch/geoserver-geonode-dev/ows"
            "layer": "geonode:77-loss-map-0fcfdbc7"}}, {
        "id": 78, "name": "hazardmap-0.01-mean.xml", "type": "hazard map",
        "min": 0.060256, "max": 9.780226
        "layer": {
            "ows": "http://gemsun02.ethz.ch/geoserver-geonode-dev/ows"
            "layer": "geonode:78-hazardmap-0-01-mean"}}]}

    :param request: the :py:class:`django.http.HttpRequest` object
    :param integer job_id: the database key of the associated oq_job record
        (see also :py:class:`geonode.mtapi.models.OqJob`)
    :returns: a :py:class:`django.http.HttpResponse` object with status code
        `200` and `500` if the OpenQuake job succeeded and failed
        respectively.
    :raises Http404: when the OpenQuake job is still in progress or if the
        request is not a HTTP GET request.
    """
    print("job_id: %s" % job_id)
    if request.method == "GET":
        job = OqJob.objects.get(id=int(job_id))
        if job.status == "running":
            oqrunner_is_alive = utils.is_process_running(
                job.job_pid, settings.OQRUNNER_PATH)
            if oqrunner_is_alive:
                print "OpenQuake job in progress.."
                raise Http404
            else:
                job.status = "failed"
                job.save()
                result = simplejson.dumps(prepare_job_result(job))
                print "OpenQuake job failed, process not found.."
                return HttpResponse(result, status=500, mimetype="text/html")
        else:
            result = simplejson.dumps(prepare_job_result(job))
            if job.status == "failed":
                print "OpenQuake job failed.."
                return HttpResponse(result, status=500, mimetype="text/html")
            else:
                print "OpenQuake job succeeded.."
                return HttpResponse(result, mimetype="text/html")
    else:
        return HttpResponse(
            "Wrong HTTP request type, use a GET for this API endpoint",
            status=500, mimetype="text/html")


def prepare_job_result(job):
    """Prepare the result dictionary that is to be returned in json form.

    :param job: the :py:class:`geonode.mtapi.models.OqJob` instance
        associated with this job.
    """
    status_translation = dict(failed="failure", succeeded="success",
                              running="running", pending="pending")
    msg = dict(job.JOB_STATUS_CHOICES)[job.status]
    status = status_translation[job.status]
    result = dict(status=status, msg=msg, id=job.id)
    if job.status == "succeeded":
        files = []
        for output in job.output_set.all().order_by("id"):
            if output.shapefile_path:
                files.append(prepare_map_result(output))
        result['files'] = files

    print("result: %s\n" % pprint.pformat(result))
    return result


def prepare_map_result(output):
    """Prepare a json fragment for a single hazard/loss map.

    The desired json fragment should look as follows:

        {"id": 77, "name": "loss-map-0fcfdbc7.xml", "type": "loss map",
         "min": 2.718281, "max": 3.141593,
         "layer": {
            "ows": "http://gemsun02.ethz.ch/geoserver-geonode-dev/ows"
            "layer": "geonode:77-loss-map-0fcfdbc7"}}

    :param output: the :py:class:`geonode.mtapi.models.Output` instance
        in question
    :returns: a dictionary with data needed to produce the json above.
    """
    layer_name, _ = os.path.splitext(os.path.basename(output.shapefile_path))
    map_type = dict(output.OUTPUT_TYPE_CHOICES)[output.output_type].lower()
    ows = urljoin(settings.GEOSERVER_BASE_URL, "ows")
    result = dict(
        id=output.id, name=os.path.basename(output.path),
        type=map_type, min=num_utils.round_float(output.min_value),
        max=num_utils.round_float(output.max_value),
        layer=dict(ows=ows, layer="geonode:%s" % layer_name))
    return result
