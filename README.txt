This is the OpenQuake django application that will be utilised by the OpenGeo UI.

For more detail on the API please see: https://github.com/gem/openquake/wiki/demo-client-API

Please note that for the purpose of deployment a symbolic link (pointing to this application) needs to be created in the geonode directory e.g.:

    gemsun02 geonode $ pwd
    /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode
    gemsun02 geonode $ sudo ln -s /home/muharem/oqapi openquake

Also, the following entry needs to be added to /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode/urls.py

    (r'^openquake/', include('geonode.openquake.urls')),
