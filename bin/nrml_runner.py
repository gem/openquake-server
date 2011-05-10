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
  -I | --inputid  I : db key of the associated input file
  -n | --dryrun     : don't do anything just show what needs done
  -p | --path P     : path to the NRML file
  -U | --user U     : database user to use [default: oq_pshai_etl]
  -W | --password W : password for the database user
"""

import getopt
import logging
import sys

from openquake.utils import db
from openquake.utils.db import loader


logging.basicConfig(level=logging.INFO)


def load_nrml(config):
    """Load the NRML data from file, write to database.

    :param dict config: the configuration to use: database, host, user, path.
    """
    engine = db.create_engine(config["db"], config["user"], config["password"])
    src_loader = loader.SourceModelLoader(
        config["path"], engine, input_id=config["inputid"])
    results = src_loader.serialize()
    src_loader.close()
    print("Total sources inserted: %s" % len(results))
    print("Results: %s" % results)


def main(cargs):
    """Run the NRML loader."""
    def strip_dashes(arg):
        return arg.split('-')[-1]

    config = dict(db="openquake", user="postgres", path="db/schema/upgrades",
                  host="localhost", dryrun=False, password=None, inputid=None)
    longopts = ["%s" % k if isinstance(v, bool) else "%s=" % k
                for k, v in config.iteritems()] + ["help"]
    # Translation between short/long command line arguments.
    s2l = dict(d="db", p="path", n="dryrun", U="user", W="password",
               I="inputid")

    try:
        opts, args = getopt.getopt(cargs[1:], "hd:np:U:W:I:", longopts)
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

    load_nrml(config)


if __name__ == '__main__':
    main(sys.argv)
