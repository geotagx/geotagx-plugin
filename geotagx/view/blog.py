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
from pybossa.core import blog_repo
from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound

blueprint = Blueprint("geotagx-blog", __name__)


@blueprint.route("/", defaults={"page": 1})
@blueprint.route("/page/<int:page>")
def index(page):
    """Renders the blog page with the specified number.

    Args:
        page (int): A page number.
    """
    from pybossa.model.blogpost import Blogpost
    from sqlalchemy import desc
    from pybossa.util import Pagination

    page = 1 if page < 1 else page
    POSTS_PER_PAGE = 20
    pagination = Pagination(page, POSTS_PER_PAGE, Blogpost.query.count())

    posts_from = (page - 1) * POSTS_PER_PAGE
    if posts_from > pagination.total_count:
        abort(404)

    posts_to = posts_from + POSTS_PER_PAGE
    posts = Blogpost.query.order_by(desc(Blogpost.created)).slice(posts_from, posts_to).all()
    for p in posts:
        p.cover_image = _find_cover_image(p.body) # _find_cover_image must be called before the body is truncated by _summarize.
        p.body = _summarize(p.body)

    try:
        return render_template("blog/index.html", posts=posts, pagination=pagination)
    except TemplateNotFound:
        abort(404)


def _find_cover_image(body):
    """Attempts to find a cover image to use for a summarized blog post.

    The cover image will be the first image found in the specified body.
    Because the body is written in markdown format, the algorithm works by
    looking for the pattern "![<label>](<URL>)" where <label> is an image
    label and <URL> is the URL to the image.

    Args:
        body (str): A blog post's body.

    Returns:
        str | None: A URL to an image if successful, None otherwise.
    """
    from re import search

    result = None
    match = search("!\[.*\]\((.*)\)", body)
    if match:
        result = match.group(1)

    return result


def _summarize(body, minimum_length=200):
    """Summarizes the specified blog post's body.

    Args:
        body (str): A blog post's body.
        minimum_length (int): The minimum number of characters (including whitespace) of the returned summary.

    Returns:
        str: A summary of the specified body.
    """
    return body[:body.find("\r\n")]
