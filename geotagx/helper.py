# -*- coding: utf-8 -*-
#
# This module is part of the GeoTag-X PyBossa plugin.
# It contains helper functions that can be used in Jinja templates.
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
def get_project_category(category_id):
    """Returns the project category instance with the specified identifier.

    Args:
        category_id (int): A project category's unique identifier.

    Raises:
        TypeError: If the 'category_id' argument is not an integer.

    Returns:
        pybossa.model.category.Category: A project category object with the specified identifier.
    """
    if not isinstance(category_id, int):
        raise TypeError("get_project_category expects 'int' but got '{}'.".format(type(category_id).__name__))

    from pybossa.core import project_repo
    return project_repo.get_category(category_id)


def get_blurred_cover_image_path(project):
    """Returns the URL to the blurred cover image for the project with the specified id.

    If a project does not have a blurred cover image, a blur operation is performed
    on its original cover image. If, however, the project does not have a cover
    image, no operation is performed and empty string is returned instead.

    Args:
        project (dict): A set of project attributes.

    Raises:
        TypeError: If the 'project' argument is not a dictionary.

    Returns:
        unicode: A URL to the blurred cover image or an empty string if no blurred image
            was found or could be created.
    """
    if not isinstance(project, dict):
        raise TypeError("get_blurred_cover_image_path expects 'dict' but got '{}'.".format(type(project).__name__))

    from flask import current_app
    from os.path import join, splitext, isfile


    upload_folder = current_app.config["UPLOAD_FOLDER"]
    info = project["info"]

    # Not all projects have a cover image assigned to them. Make sure this one does before continuing.
    container = info.get("container")
    if not container:
        return ""

    # A path in URL terms (does not include the upload folder).
    thumbnail_path = join(container, info["thumbnail"])
    [filename, extension] = splitext(thumbnail_path)
    blurred_thumbnail_path = filename + "_blurred" + extension

    # The actual filename of both images.
    thumbnail_filename = join(upload_folder, thumbnail_path)
    blurred_thumbnail_filename = join(upload_folder, blurred_thumbnail_path)

    # If the blurred image does not exist, try and generate a new one.
    if not isfile(blurred_thumbnail_filename):
        if isfile(thumbnail_filename):
            from cv2 import imread, GaussianBlur, imwrite
            thumbnail = imread(thumbnail_filename)
            blurred_thumbnail = GaussianBlur(thumbnail, (7, 7), 0)
            imwrite(blurred_thumbnail_filename, blurred_thumbnail)

            # TODO Handle read/write errors!
            # If there was an error writing the blurred cover image but the
            # original exists, return the path to the original.
            # blurred_thumbnail_path = thumbnail_path
        else:
            blurred_thumbnail_path = "" # The image could not be created since an original does not exist.

    return blurred_thumbnail_path
