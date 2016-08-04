# -*- coding: utf-8 -*-
#
# This module is part of the GeoTag-X PyBossa plugin.
#
# Author: S.P. Mohanty (sp.mohanty@cern.ch)
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
from flask import Blueprint, request, current_app, render_template, jsonify
from flask.ext.login import login_required
from pybossa.model.task import Task
from pybossa.model.project import Project
from pybossa.model.category import Category
from pybossa.util import admin_required
from pybossa.core import db, sentinel
import json
import datetime
import base64, hashlib, random

blueprint = Blueprint("geotagx-sourcerer", __name__)


"""
    Basic implementation of the geotagx-sourcerer-proxy which ingests images from multiple sources
"""
@blueprint.route('/proxy', methods = ['GET', 'POST'])
def proxy():
    data = request.args.get('sourcerer-data')
    try:
        data = base64.b64decode(data)
        data = json.loads(data)
        data['timestamp'] = str(datetime.datetime.utcnow())
        image_url = data['image_url']

        # The "GEOTAGX-SOURCERER-HASH" key represents the overall knowledge of GeoTagX about all the images collected via sourcerers
        hsetnx_response = sentinel.slave.hsetnx("GEOTAGX-SOURCERER-HASH", image_url, json.dumps(data))
        if hsetnx_response == 1: # Case when the image_url has not yet been seen
            # Save it into a "Queue" modelled as a hash, where it waits until the admin approves or rejects it
            sentinel.slave.hsetnx("GEOTAGX-SOURCERER-HASHQUEUE", image_url, json.dumps(data))


        response = {}
        response['state'] = "SUCCESS"
        response['data'] = data
        return jsonify(response)

    except Exception as e:

        response = {}
        response['state'] = "ERROR"
        response['message'] = str(e)
        return jsonify(response)

"""
    End point to get meta data about Categories for which data is being collected via
    geotagx-sourcerers
"""
@blueprint.route('/sourcerer/categories.json')
def categories():
    try:
        categories = current_app.config['GEOTAGX_SOURCERER_CATEGORIES']
    except:
        categories = []
    return jsonify(categories)


"""
    Implements the Dashboard for GeoTag-X Sourcerer
    which lets admins push contributed images directly into the projects
    (via the GeoTag-X Sourcerer Sink Daemon)
"""
@blueprint.route('/settings')
@login_required
@admin_required
def dashboard():
    queue = sentinel.slave.hgetall("GEOTAGX-SOURCERER-HASHQUEUE")
    #TODO : Handle Exception
    queue_object = {}
    for _key in queue.keys():
        _obj = json.loads(queue[_key])
        _m = hashlib.md5()
        _m.update(_obj['image_url'])
        _obj['id'] = _m.hexdigest()
        queue_object[_key] = _obj
    return render_template('geotagx/sourcerer/dashboard.html', queue = queue_object)

@blueprint.route('/commands', methods = ['POST'])
@login_required
@admin_required
def dashboard_commands():
    try:
        commands = request.form['commands']
        commands = json.loads(base64.b64decode(commands))

        approve = []
        if "approve" in commands.keys():
            approve = commands['approve']
        reject = []
        if "reject" in commands.keys():
            reject = commands['reject']

        # Deal with Approved Items
        for _item in approve:
            _categories = _item['categories']
            IMAGE_URL = _item['image_url']
            SOURCE_URI = _item['source_uri']

            for _category in _categories:
                category_objects = Category.query.filter(Category.short_name == _category)
                for category_object in category_objects:
                    related_projects = Project.query.filter(Project.category == category_object)
                    for related_project in related_projects:
                        # Start building Task Object
                        _task_object = Task()
                        _task_object.project_id = related_project.id

                        # Build Info Object from whatever data we have
                        _info_object = {}
                        _info_object['image_url'] = IMAGE_URL
                        _info_object['source_uri'] = SOURCE_URI
                        _info_object['id'] = SOURCE_URI + "_" + \
                                            ''.join(random.choice('0123456789ABCDEF') for i in range(16))

                        _task_object.info = _info_object
                        print _task_object
                        print _info_object

                        db.session.add(_task_object)
                        db.session.commit()
            # Delete from GEOTAGX-SOURCERER-HASHQUEUE
            sentinel.slave.hdel("GEOTAGX-SOURCERER-HASHQUEUE", IMAGE_URL)

        # Deal with rejected items
        for _item in reject:
            #Directly delete from GEOTAGX-SOURCERER-HASHQUEUE
            IMAGE_URL = _item['image_url']
            sentinel.slave.hdel("GEOTAGX-SOURCERER-HASHQUEUE", IMAGE_URL)

        _result = {
            "result" : "SUCCESS"
        }
        return jsonify(_result)
    except Exception as e:
        _result = {
            "result" : "ERROR",
        }
        return jsonify(_result)
