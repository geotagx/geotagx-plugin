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
from flask.ext.plugins import Plugin

__plugin__  = "GeoTagX"
__version__ = "0.0.1"


class GeoTagX(Plugin):
    def setup(self):
        """Initializes the GeoTag-X plugin.
        """
        from flask import current_app as app
        from view.admin import blueprint as admin_blueprint
        from view.blog import blueprint as blog_blueprint
        from view.community import blueprint as community_blueprint
        from filter import blueprint as filter_blueprint
        from view.geojson_exporter import blueprint as geojson_exporter_blueprint
        from view.feedback import blueprint as feedback_blueprint
        from view.geotagx import blueprint as geotagx_blueprint
        from view.survey import blueprint as survey_blueprint

        # The plugin's default configuration.
        default_configuration = {
            "GEOTAGX_NEWSLETTER_DEBUG_EMAIL_LIST": [],
        }
        for key in default_configuration:
            if app.config.get(key, None) is None:
                app.config[key] = default_configuration[key]

        # A list of blueprint <handle, URL prefix> pairs.
        blueprints = [
            (admin_blueprint, "/admin"),
            (blog_blueprint, "/blog"),
            (community_blueprint, "/community"),
            (filter_blueprint, None),
            (feedback_blueprint, "/feedback"),
            (geojson_exporter_blueprint, None),
            (geotagx_blueprint, "/geotagx"),
        ]
        for (handle, url_prefix) in blueprints:
            app.register_blueprint(handle, url_prefix=url_prefix)

        setup_survey(app)
        setup_sourcerer(app)
        setup_project_browser(app)
        setup_helper_functions(app)


def setup_default_configuration(app, default_configuration):
    """Sets up the specified application's default configuration.

    This function will only modify an application's configuration entry
    if it does not already contain a value.

    Args:
        app (werkzeug.local.LocalProxy): The application's instance.
        default_configuration (dict): The default configuration.
    """
    if default_configuration and isinstance(default_configuration, dict):
        for key in default_configuration:
            if app.config.get(key, None) is None:
                app.config[key] = default_configuration[key]


def setup_survey(app, url_prefix="/survey"):
    """Sets up the participation survey.

    Args:
        app (werkzeug.local.LocalProxy): The current application's instance.
        url_prefix (str): The blueprint's URL prefix.
    """
    from view.survey import blueprint

    setup_default_configuration(app, {
        "GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS": 30,
    })
    app.register_blueprint(blueprint, url_prefix=url_prefix)


def setup_sourcerer(app, url_prefix="/sourcerer"):
    """Sets up the sourcerer.

    Args:
        app (werkzeug.local.LocalProxy): The current application's instance.
        url_prefix (str): The blueprint's URL prefix.
    """
    from view.sourcerer import blueprint

    app.register_blueprint(blueprint, url_prefix=url_prefix)


def setup_project_browser(app, url_prefix="/browse"):
    """Sets up the project browser blueprint.

    Args:
        app (werkzeug.local.LocalProxy): The current application's instance.
        url_prefix (str): The blueprint's URL prefix.
    """
    from view.project_browser import blueprint

    app.register_blueprint(blueprint, url_prefix=url_prefix)


def setup_helper_functions(app):
    """Sets up the helper functions.

    Args:
        app (werkzeug.local.LocalProxy): The current application's instance.
    """
    import helper
    functions = {
        "get_project_category": helper.get_project_category,
    }
    app.jinja_env.globals.update(**functions)
