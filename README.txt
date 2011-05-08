This is the OpenQuake django application that will be utilised by the OpenGeo UI.

You can try the "input_upload" API endpoint as follows:

 * terminal window 1:
  - cd geonode
  - python manage.py runserver --pythonpath="(cd ..; pwd)"

 * terminal window 2:
  - cd <openquake>/smoketests/classical_psha_simple
  - curl -F "file=@gmpe_logic_tree.xml" -F "file=@small_exposure.xml" -F "file=@source_model1.xml" http://127.0.0.1:8000/openquake/input_upload

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


For more detail on the API please see: https://github.com/gem/openquake/wiki/demo-client-API

Please note that for the purpose of deployment a symbolic link (pointing to this application) needs to be created in the geonode directory e.g.:

    gemsun02 geonode $ pwd
    /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode
    gemsun02 geonode $ sudo ln -s /home/muharem/oqapi openquake

Also, the following entry needs to be added to /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode/urls.py

    (r'^openquake/', include('geonode.openquake.urls')),
