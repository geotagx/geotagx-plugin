# -*- coding: utf-8 -*-
#
# This module is part of the GeoTag-X PyBossa plugin. It implements a view that
# offers an alternative approach to browsing projects.
#
# Author: Jeremy Othieno (j.othieno@gmail.com)
#
# Copyright (c) 2017 UNITAR/UNOSAT
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
from flask import Blueprint, render_template

blueprint = Blueprint("geotagx-project-browser", __name__, url_prefix="/browse")
"""The view's blueprint."""


def setup(application):
    """Sets up the view.

    Args:
        application (werkzeug.local.LocalProxy): The current Flask application's instance.
    """
    application.register_blueprint(blueprint)


@blueprint.route("/")
def index():
    """Renders the project browser's index page.

    Returns:
        unicode: The page's rendered HTML.
    """
    return render_template("projects/browse.html", categories=_get_cached_categories())


def _get_cached_categories():
    """Returns all cached categories.

    Returns:
        list: A list of all cached categories.
    """
    from flask.ext.login import current_user
    from pybossa.cache import categories as cached_categories
    from pybossa.cache import projects as cached_projects

    categories = cached_categories.get_used()

    if not (current_user.is_authenticated() and current_user.admin):
        restricted_categories = {
            "underdevelopment",
        }
        categories = filter(lambda c: c["short_name"] not in restricted_categories, categories)

    for category in categories:
        category["projects"] = cached_projects.get_all(category["short_name"])

    return categories
