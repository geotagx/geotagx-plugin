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
from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound

blueprint = Blueprint("geotagx-blog", __name__)


@blueprint.route("/", defaults={"page": 1})
@blueprint.route("/page/<int:page>")
def index(page):
    """Renders the blog page with the specified number.

    Args:
        page (int): A page number.

    Returns:
        unicode: The page's rendered HTML.
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


@blueprint.route("/post/<int:id>", endpoint="post")
def render_post(id):
    """Renders the blog post with the specified identifier.

    Args:
        id (int): A blog post's unique identifier.

    Returns:
        unicode: The page's rendered HTML.
    """
    try:
        return render_template("blog/post.html", post=_get_post(id))
    except TemplateNotFound:
        abort(404)


def _get_post(id):
    """Returns the blog post with the specified id.

    Args:
        id (int): A blog post's unique identifier.

    Returns:
        Blogpost | None: If found, an instance of the post with the specified id, None otherwise.
    """
    from pybossa.core import blog_repo
    return blog_repo.get(id)


def _find_cover_image(body):
    """Attempts to find a cover image to use for a summarized blog post.

    The cover image will be the first image found in the specified body.
    Because the body is written in markdown format, the algorithm works by
    looking for the pattern "![<label>](<URL>)" where <label> is an image
    label and <URL> is the URL to the image. If an occurrence of the
    aforementioned pattern is found, <URL> is returned.

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


def _summarize(body):
    """Summarizes the specified blog post's body.

    This function will extract the first paragraph from the specified body.
    While the function does a reasonable job, it is far from robust as it does not cover
    a few corner-cases of the markdown format. A better solution would be to introduce
    a 'summary' field to the Blogpost class, allowing authors to write their own summaries.

    Args:
        body (str): A blog post's body.

    Returns:
        str: A summary of the specified body.
    """
    summary = ""
    if body:
        # The first summary is at least a quarter of the original body's length.
        # Note that body is truncated after a paragraph.
        summary = body[:body.find("\r\n", len(body)/4)]

        # Remove all images from the summary since the cover image is already in use.
        from re import findall
        for image in findall('(!\[.*\]\(.*\))', summary):
            summary = summary.replace(image, "")

        # With the images removed, get rid of any leading whitespace that may have been introduced.
        summary = summary.lstrip()

        markdown_delimiters = set(["*", "#", "_"])
        limit = 0

        if summary[0] in markdown_delimiters:
            delimiter = summary[0]
            delimiter_length = 1
            while summary[delimiter_length] == delimiter:
                delimiter_length += 1

            delimiter *= delimiter_length
            limit = summary.find(delimiter, delimiter_length + 1) + delimiter_length
        else:
            minimum_length = 200
            limit = 0
            while limit < minimum_length:
                k = summary.find("\r\n", limit + 1)
                if k < limit:
                    break
                else:
                    limit = k

    return summary[:limit]
