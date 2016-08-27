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
