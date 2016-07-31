# -*- coding: utf-8 -*-
#
# This module is part of the GeoTag-X PyBossa plugin.
#
# Copyright (c) 2016 UNITAR/UNOSAT
#
# The MIT License (MIT)
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.
from flask import current_app as app
from flask.ext.plugins import Plugin

__plugin__  = "GeoTagX"
__version__ = "0.0.1"


class GeoTagX(Plugin):
    def setup(self):
        """Initializes the GeoTag-X plugin.
        """
        from view.blog import blueprint as blog_blueprint
        from filter import blueprint as filter_blueprint
        from view.geotagx import blueprint as geotagx_blueprint

        # A list of blueprint <handle, URL prefix> pairs.
        blueprints = [
            (blog_blueprint, "/blog"),
            (filter_blueprint, None),
            (geotagx_blueprint, "/geotagx"),
        ]

        for (handle, url_prefix) in blueprints:
            app.register_blueprint(handle, url_prefix=url_prefix)
