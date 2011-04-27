from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('geonode.openquake.views',
    (r'^$', 'openquake'),
    url(r'^upload$', 'upload'),
)

# Please note: the following line needs to be added to
# /var/www/geonode/wsgi/geonode/src/GeoNodePy/geonode
#
#       (r'^openquake/', include('geonode.openquake.urls')),

