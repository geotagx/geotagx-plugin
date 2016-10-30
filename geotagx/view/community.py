# -*- coding: utf-8 -*-
#
# This module is part of the GeoTag-X PyBossa plugin.
#
# Author: Jeremy Othieno (j.othieno@gmail.com)
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
from flask import Blueprint, render_template, abort, current_app
from flask.ext.login import current_user
from pybossa.feed import get_update_feed
from pybossa.cache import users as cached_users
from pybossa.util import Pagination

blueprint = Blueprint("geotagx-community", __name__)


@blueprint.route("/", defaults={"page": 1})
@blueprint.route("/page/<int:page>")
def index(page):
    """Renders the community page with the specified page number.

    Args:
        page (int): A page number.

    Returns:
        unicode: The page's rendered HTML.
    """
    per_page = 24
    total = cached_users.get_total_active_users()
    users = cached_users.get_users_page(page, per_page)
    if not users and page != 1:
        abort(404)
    pagination = Pagination(page, per_page, total)
    return render_template("community/index.html", users=users, total=total, pagination=pagination)


@blueprint.route("/leaderboard/", endpoint="leaderboard")
def render_leaderboard():
    """Renders the leaderboard page.

    Returns:
        unicode: The page's rendered HTML.
    """
    user_id = current_user.id if current_user.is_authenticated() else None
    users = cached_users.get_leaderboard(current_app.config["LEADERBOARD"], user_id=user_id)
    return render_template("/community/leaderboard.html", users=users)
