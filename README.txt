This is the OpenQuake django application that will be utilised by the OpenGeo UI.

Dependencies
------------

 * django
 * psycopg2
 * nose (for running tests)

Package Structure
-----------------

Code for OQ-Server is organized in the following manner:

 * bin
 * geonode  (code for the OQ-Server Django application; for Django code only!)
   - mtapi  (mtapi is a Django application for the geonode project)
 * oqrunner (contains code for running the OpenQuake engine)
 * tests


Running the OQ-Server
---------------------

You can try the "input_upload" API endpoint as follows:

 * terminal window 1:
  - cd geonode
  - python manage.py runserver --pythonpath="(cd ..; pwd)"

 * terminal window 2:
  - cd <openquake>/smoketests/classical_psha_simple
  - curl -F "input_files=@gmpe_logic_tree.xml" -F "input_files=@small_exposure.xml" -F "input_files=@source_model1.xml" http://127.0.0.1:8000/mtapi/input_upload/

The response should be something along the lines of:
    {"msg": "Model upload successful", "status": "success", "upload": 4,
     "files": [{"name": "source_model1.xml", "id": 21}]}

Run the psql tool to check:

    $ psql -U postgres -d openquake -c "SELECT * FROM uiapi.upload WHERE id=4"
     id | owner_id |              path              |        last_update         
    ----+----------+--------------------------------+----------------------------
      4 |        1 | /var/spool/openquake/tmpT_xmbo | 2011-05-08 04:32:34.287716
    (1 row)

    $ psql -U postgres -d openquake -c "SELECT id, path, input_type, size FROM uiapi.input WHERE upload_id=4"
     id |                        path                        | input_type | size  
    ----+----------------------------------------------------+------------+-------
     19 | /var/spool/openquake/tmpT_xmbo/gmpe_logic_tree.xml | ltree      |   819
     20 | /var/spool/openquake/tmpT_xmbo/small_exposure.xml  | exposure   | 82510
     21 | /var/spool/openquake/tmpT_xmbo/source_model1.xml   | source     | 10092
    (3 rows)

***
***

For more detail on the API please see: https://github.com/gem/openquake/wiki/demo-client-API

Please note that for the purpose of deployment a symbolic link (pointing to this application) needs to be created in the geonode directory e.g.:

    gemsun02 geonode $ pwd
    /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode
    gemsun02 geonode $ sudo ln -s ~muharem/oqapi/geonode/mtapi

The following entry needs to be added to /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode/urls.py

    (r'^mtapi/', include('geonode.mtapi.urls')),

Also, the following lines need to be added to /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode/local_settings.py

    NRML_RUNNER_PATH="/home/muharem/oqsrv/bin/nrml_runner.py"
    OQ_DB_HOST = "127.0.0.1"
    OQ_DB_NAME = "geonode"
    OQ_DB_USER = "oq_uiapi_writer"
    OQ_DB_PASSWORD = "s3cr3t"
    OQ_UPLOAD_DIR = "/usr/openquake/spool"
    import sys
    sys.path.append("/home/muharem/lars")
    sys.path.append("/usr/lib/python2.7/dist-packages")
    sys.path.append("/usr/local/lib/python2.7/dist-packages")
    sys.path.append("/usr/lib/pymodules/python2.7")
    NRML_RUNNER_PYTHONPATH=":".join([seg for seg in sys.path if seg.find("geonode") < 0])
    NRML_RUNNER_PYTHONPATH += ":/home/muharem/oqsrv"
    import os
    os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-6-openjdk"
