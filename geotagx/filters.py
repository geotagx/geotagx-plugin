# -*- coding: utf-8 -*-
#
# This module is part of the GeoTag-X PyBossa plugin.
# It contains implementations for custom filters.
#
# Authors:
# - S. P. Mohanty
# - Jeremy Othieno (j.othieno@gmail.com)
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
from flask import Blueprint

blueprint = Blueprint("geotagx-filters", __name__)


@blueprint.app_template_filter("geotagx_md5")
def get_md5_digest(arg):
    """Returns the MD5 digest of the specified argument.

    The digest is a string containing only hexadecimal digits.

    Args:
        arg (string): The string to hash.
    """
    import hashlib
    return hashlib.md5(arg).hexdigest()


@blueprint.app_template_filter()
def geotagx_blog_image(body, default_image):
    # Note : The body is supposed to be in MarkDown
    import re
    links = re.findall('!\[.*\]\((.*)\)', body)
    if len(links) == 0:
        return default_image
    else:
        # Return the first image link if there are indeed multiple images in the body
        return links[0]


@blueprint.app_template_filter()
def geotagx_blog_trim_body(body):
    CHARACTERS_IN_SHORT_DESCRIPTION = 400
    if len(body) < CHARACTERS_IN_SHORT_DESCRIPTION :
        return body
    else:
        return body[:CHARACTERS_IN_SHORT_DESCRIPTION]+"..."


@blueprint.app_template_filter()
def geotagx_remove_images_from_markdown(body):
    import re
    links = re.findall('(!\[.*\]\(.*\))', body)
    for _link in links:
        body = body.replace(_link, '')
    return body


def setup_custom_filters(app):
    # FIXME
    # Load custom template filters as/if defined by the theme writer
    try:
        import os, imp, inspect

        here = os.path.abspath(os.path.dirname(__file__))
        theme_path = os.path.join(here, 'themes', app.config.get('THEME'))
        custom_filter_path = os.path.join(theme_path, app.config.get('THEME_CUSTOM_FILTERS'))
        pybossa_custom_filters = imp.load_source('pybossa_custom_filters', custom_filter_path)

        for (filter_name, filter_object) in inspect.getmembers(pybossa_custom_filters):
            # Ignore internal functions which start with '__'
            if not filter_name.startswith("__"):
                app.jinja_env.filters[filter_name] = filter_object
                log_message = 'Loading Custom Filter : "%s" form file %s' % (filter_name, custom_filter_path)
                app.logger.info(log_message)
    except IOError as inst:
        log_message = 'Custom Filter definition file not available : %s' % str(inst)
        app.logger.error(log_message)
