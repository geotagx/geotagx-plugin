# -*- coding: utf-8 -*-
#
# This module is part of the GeoTag-X PyBossa plugin.
# It contains implementations for custom filters.
#
# Authors:
# - S. P. Mohanty (sp.mohanty@cern.ch)
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
from flask import Blueprint, current_app, jsonify

blueprint = Blueprint("geotagx-geojson-exporter", __name__)


@blueprint.route("/project/category/<string:category_short_name>/export-geojson")
def export_category_results(category_short_name):
    """Renders the specified category's results in GeoJSON format.

    Args:
        category_short_name (str): A category's unique short name.

    Returns:
        str: A GeoJSON formatted-string containing the specified category's results.
    """
    return _export_category_results_as_geoJSON(category_short_name)


def _export_category_results_as_geoJSON(category_name):
    from pybossa.cache import projects as cached_projects
    from pybossa.exporter.json_export import JsonExporter
    import json
    import pandas as pd
    import numpy as np

    geotagx_json_exporter = JsonExporter()

    max_number_of_exportable_projects = 15
    projects_in_category = cached_projects.get(category_name, page=1, per_page=max_number_of_exportable_projects)
    task_runs = []
    task_runs_info = []
    project_name_id_mapping = {}
    project_id_name_mapping = {}

    project_question_type_mapping = {}
    project_question_question_text_mapping = {}

    for project in projects_in_category:
        short_name = project['short_name']

        project_id_name_mapping[project['id']] = project['short_name']
        project_name_id_mapping[project['short_name']] = project['id']

        # Check if it a supported geotagx project whose schema we know
        if 'GEOTAGX_SUPPORTED_PROJECTS_SCHEMA' in current_app.config.keys() \
            and short_name in current_app.config['GEOTAGX_SUPPORTED_PROJECTS_SCHEMA'].keys():

            ##Read the project schema and store the respective questions and their types
            for _question in current_app.config['GEOTAGX_SUPPORTED_PROJECTS_SCHEMA'][short_name]['questions']:
                project_question_type_mapping[unicode(short_name+"::"+_question['answer']['saved_as'])] = _question['type']
                project_question_question_text_mapping[unicode(short_name+"::"+_question['answer']['saved_as']+"::question_text")] = _question['title']

            #Only export results of known GEOTAGX projects that are created with `geotagx-project-template`
            task_runs_generator = geotagx_json_exporter.gen_json("task_run", project['id'])
            _task_runs = ""
            for task_run_c in task_runs_generator:
                _task_runs += task_run_c

            task_runs = task_runs + json.loads(_task_runs)

    def extract_geotagx_info(json):
        """Returns a list of only info objects of the task_run"""
        exploded_json = []
        for item in json:
            item['info']['project_id'] = item['project_id']
            exploded_json.append(item['info'])
        return exploded_json

    def _summarize_geolocations(geolocation_responses):
        """
            TODO :: Add different geo-summarization methods (ConvexHull, Centroid, etc)
        """
        responses = []

        for response in geolocation_responses:
            if type(response) == type([]):
                responses.append(response)

        return responses

    """
        Changes projection to WGS84 projection  from WebMercator projection
        so that most geojson renderers support it out of the box
        Inspired by : http://www.gal-systems.com/2011/07/convert-coordinates-between-web.html
    """
    def _project_coordinate_from_webmercator_toWGS84(coordinates):
        print coordinates
        mercatorX_lon = coordinates[0]
        mercatorY_lat = coordinates[1]

        if math.fabs(mercatorX_lon) < 180 and math.fabs(mercatorY_lat) < 90:
            return False, False

        if ((math.fabs(mercatorX_lon) > 20037508.3427892) or (math.fabs(mercatorY_lat) > 20037508.3427892)):
            return False, False

        x = mercatorX_lon
        y = mercatorY_lat
        num3 = x / 6378137.0
        num4 = num3 * 57.295779513082323
        num5 = math.floor(float((num4 + 180.0) / 360.0))
        num6 = num4 - (num5 * 360.0)
        num7 = 1.5707963267948966 - (2.0 * math.atan(math.exp((-1.0 * y) / 6378137.0)));
        mercatorX_lon = num6
        mercatorY_lat = num7 * 57.295779513082323

        return mercatorX_lon, mercatorY_lat

    """
        Changes the projection of the multi_polygon object to WGS84 from WebMercator
    """
    def _project_geosummary_from_webmercator_to_WGS84(multi_polygon):
        _multi_polygon = []
        for polygon in multi_polygon:
            _polygon = []
            for coordinates in polygon:
                try:
                    _x, _y = _project_coordinate_from_webmercator_toWGS84(coordinates)
                    if _x and _y:
                        _polygon.append([_x, _y])
                except:
                    pass # Pass Silentily if there is some error in the input
            _multi_polygon.append(_polygon)
        return _multi_polygon

    def _build_geo_json(geolocation_responses):
        geoJSON = {}
        geoJSON['type'] = "FeatureCollection"
        geoJSON['features'] = []
        for response in geolocation_responses:
            if response['_geotagx_geolocation_key']:
                geo_summary = response[response['_geotagx_geolocation_key']]
                _feature = {}
                _feature['type'] = "Feature"
                _feature['geometry'] = {}

                _feature['geometry']['type'] = "MultiPolygon"
                _feature['geometry']['coordinates'] = \
                    [_project_geosummary_from_webmercator_to_WGS84(geo_summary['geo_summary'])]

                del response[response['_geotagx_geolocation_key']]
                del response['_geotagx_geolocation_key']
                _feature['properties'] = response

                #Neglect responses with no coordinate labels
                if _feature['geometry']['coordinates'] != [[]]:
                    geoJSON['features'].append(_feature)

        return geoJSON

    task_runs_info = extract_geotagx_info(task_runs)
    task_runs_info = pd.read_json(json.dumps(task_runs_info))

    summary_dict = {}
    for img_url in task_runs_info['img'].unique():
        per_url_data = task_runs_info[task_runs_info['img'] == img_url]

        for project_id in np.unique(per_url_data['project_id'].values):

            per_summary_dict = {}
            per_summary_dict['_geotagx_geolocation_key'] = False

            if img_url in summary_dict.keys():
                per_summary_dict = summary_dict[img_url]

            per_summary_dict['GEOTAGX_IMAGE_URL'] = img_url
            per_url_data_project_slice = per_url_data[per_url_data['project_id'] == project_id]

            for key in per_url_data_project_slice.keys():
                namespaced_key = project_id_name_mapping[project_id]+"::"+key
                if key not in ['img', 'isMigrated', 'son_app_id', 'task_id', 'project_id']:
                    if namespaced_key in project_question_type_mapping.keys():
                        if project_question_type_mapping[namespaced_key] == u"geotagging":
                            per_summary_dict['_geotagx_geolocation_key'] = namespaced_key
                            per_summary_dict[namespaced_key] = {'geo_summary' : _summarize_geolocations(per_url_data_project_slice[key].values)}
                        else:
                            per_summary_dict[namespaced_key] = {'answer_summary':dict(per_url_data_project_slice[key].value_counts())}
                        per_summary_dict[namespaced_key]['question_text'] = project_question_question_text_mapping[unicode(namespaced_key+"::question_text")]

                elif key == u"img":
                    per_summary_dict[project_id_name_mapping[project_id]+"::GEOTAGX_TOTAL"] = len(per_url_data_project_slice)

            summary_dict[img_url] = per_summary_dict

    geo_json = _build_geo_json(summary_dict.values())
    return jsonify(geo_json)
