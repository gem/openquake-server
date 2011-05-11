#!/usr/bin/env python
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
Source model loading tool, writes the contents of NRML files to the
pshai schema tables in the database.

  -h | --help       : prints this help string
       --host H     : database host machine name [default: localhost]
  -d | --db D       : database to use [default: openquake]
  -u | --uploadid u : database key of the associated upload record
  -U | --user U     : database user to use [default: oq_pshai_etl]
  -W | --password W : password for the database user
"""

import getopt
import pprint
import sys

from geonode.mtapi.models import Upload, Input

from openquake.utils import db
from openquake.utils.db import loader



def load_source(config, path, input_id):
    """Load a single model source from file, write to database.

    :param dict config: the configuration to use: database, host, user, path.
    :param str path: the full path of the model source file
    :param int input_id: the database key of the associated input record
    :returns: `False` on failure, `True` on success
    """
    try:
        engine = db.create_engine(
            config["db"], config["user"], config["password"])
        src_loader = loader.SourceModelLoader(path, engine, input_id=input_id)
        results = src_loader.serialize()
        src_loader.close()
        print("Total sources inserted: %s" % len(results))
    except Exception, e:
        print(e)
        return False
    else:
        return True


def load_sources(config):
    """Load a model sources for an upload, write their content to database.

    :param dict config: the configuration to use: database, host, user, path.
    """
    error_occurred = False
    [upload] = Upload.objects.filter(id=config["uploadid"])
    sources = Input.objects.filter(upload=3, input_type="source")
    print("number of sources: %s" % len(sources))
    for source in sources:
        error_occurred = not load_source(config, source.path, source.id)
        if error_occurred:
            break

    upload.status = "failed" if error_occurred else "succeeded"
    upload.save()


def main(cargs):
    """Run the NRML loader."""
    def strip_dashes(arg):
        return arg.split('-')[-1]

    config = dict(db="openquake", host="localhost", user="postgres",
                  password=None, uploadid=None)
    longopts = ["%s" % k if isinstance(v, bool) else "%s=" % k
                for k, v in config.iteritems()] + ["help"]
    # Translation between short/long command line arguments.
    s2l = dict(d="db", h="host", U="user", W="password", u="uploadid")

    try:
        opts, args = getopt.getopt(cargs[1:], "hd:U:W:u:", longopts)
    except getopt.GetoptError, e:
        print e
        print __doc__
        sys.exit(101)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print __doc__
            sys.exit(0)
        opt = strip_dashes(opt)
        if opt not in config:
            opt = s2l[opt]
        config[opt] = arg if arg else not config[opt]

    if len(cargs) < 2:
        print __doc__
        sys.exit(102)

    print("config = %s" % pprint.pprint(config))
    load_sources(config)


if __name__ == '__main__':
    main(sys.argv)
