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
from flask import Blueprint, request, url_for, redirect, session
from flask import jsonify, current_app, render_template
from flask.ext.login import current_user
from pybossa.core import db
from pybossa.cache import users as cached_users

blueprint = Blueprint("geotagx-survey", __name__)


@blueprint.route('/status')
def get_geotagx_survey_status():
    """ Get geotagx survey status  """
    """ Used by client side javascript code to determine rendering of the different surveys """
    if not current_user.is_anonymous():
        result = {}
        if "geotagx_survey_status" in current_user.info.keys():
            rank_and_score = cached_users.rank_and_score(current_user.id)
            result['geotagx_survey_status'] = current_user.info['geotagx_survey_status']
            result['task_runs'] = rank_and_score['score']
            result['final_survey_task_requirements'] = current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS']
        else:
            result['geotagx_survey_status'] = "RESPONSE_NOT_TAKEN"

        return jsonify(result)
    else:
        return jsonify({'result':' -_- STOP SNOOPING AROUND -_- '})

@blueprint.route('/update-status')
def update_geotagx_survey_status():
    """ Updates Geotagx Survey Status for the current user """
    """ Used by client side javascript code to update surveys states for the current_user """
    previous_state = request.args.get('previous_geotagx_survey_state')
    new_state = request.args.get('new_geotagx_survey_state')
    if not current_user.is_anonymous():
        valid_options = ["RESPONSE_NOT_TAKEN", "AGREE_TO_PARTICIPATE", "DENY_TO_PARTICIPATE", "DENY_TO_PARTICIPATE_IN_FINAL_SURVEY", "ALL_SURVEYS_COMPLETE" ]
        # Check if both the parameters are indeed valid options
        if (new_state in valid_options) and (previous_state in valid_options) :
            # and ((previous_state == current_user.info['geotagx_survey_status']) or (previous_state == "RESPONSE_NOT_TAKEN"))
            current_user.info['geotagx_survey_status'] = new_state
            db.session.commit()
            return jsonify({'result':True})
        else:
            return jsonify({'result':' -_- STOP SNOOPING AROUND -_- '})
    else:
        return jsonify({'result':' -_- STOP SNOOPING AROUND -_-'})

@blueprint.route('/')
def render_survey():
    """ Renders appropriate survey for current user or redirects to home page if surveys are not applicable """
    if not current_user.is_anonymous():
        rank_and_score = cached_users.rank_and_score(current_user.id)
        survey_type = "INITIAL"
        if rank_and_score['score'] > current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS'] and "geotagx_survey_status" in current_user.info.keys() and current_user.info['geotagx_survey_status'] == "AGREE_TO_PARTICIPATE" :
            survey_type = "FINAL"

        if "geotagx_survey_status" in current_user.info.keys() and current_user.info['geotagx_survey_status'] in ["DENY_TO_PARTICIPATE", "DENY_TO_PARTICIPATE_IN_FINAL_SURVEY", "ALL_SURVEYS_COMPLETE"]:
            survey_type = "NONE"

        return render_template('/geotagx/surveys/surveys.html', survey_type = survey_type, GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS = current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS'])
    else:
        return redirect(url_for('home.home'))
