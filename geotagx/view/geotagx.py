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
""" Custom Geotagx functionalities for Pybossa"""
from flask import Blueprint, request, url_for, flash, redirect, session, \
  current_app, render_template, abort, request
from pybossa.model.user import User
from pybossa.model.task_run import TaskRun
from pybossa.model.task import Task
from pybossa.model.project import Project
from pybossa.model.category import Category
from pybossa.util import Pagination, pretty_date, admin_required, UnicodeWriter
from pybossa.auth import ensure_authorized_to
from pybossa.core import db, task_repo, user_repo, sentinel, mail
from pybossa.cache import users as cached_users
from pybossa.cache import projects as cached_projects
from pybossa.view import projects as projects_view
from flask_oauthlib.client import OAuthException
from flask.ext.login import login_required, login_user, logout_user, current_user
from wtforms import Form, IntegerField, DecimalField, TextField, BooleanField, \
    SelectField, validators, TextAreaField, PasswordField, FieldList, SubmitField
from flask.ext.mail import Message
from pybossa.util import admin_required, UnicodeWriter
from flask import jsonify, Response
from StringIO import StringIO
import json
import re
import datetime
import math
import base64, hashlib, random
import markdown

blueprint = Blueprint('geotagx', __name__)


def setup_geotagx_config_default_params():
	""" Sets up default values for geotagx specific config params """
	if "GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS" not in current_app.config.keys():
		current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS'] = 30

	if "GEOTAGX_NEWSLETTER_DEBUG_EMAIL_LIST" not in current_app.config.keys():
		current_app.config['GEOTAGX_NEWSLETTER_DEBUG_EMAIL_LIST'] = []

@blueprint.route('/get_geotagx_survey_status')
def get_geotagx_survey_status():
	""" Get geotagx survey status  """
	""" Used by client side javascript code to determine rendering of the different surveys """
	if not current_user.is_anonymous():
		result = {}
		if "geotagx_survey_status" in current_user.info.keys():
			rank_and_score = cached_users.rank_and_score(current_user.id)
			result['geotagx_survey_status'] = current_user.info['geotagx_survey_status']
			result['task_runs'] = rank_and_score['score']
			setup_geotagx_config_default_params()
			result['final_survey_task_requirements'] = current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS']
		else:
			result['geotagx_survey_status'] = "RESPONSE_NOT_TAKEN"

		return jsonify(result)
	else:
		return jsonify({'result':' -_- STOP SNOOPING AROUND -_- '})

@blueprint.route('/update_geotagx_survey_status')
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

@blueprint.route('/survey')
def render_survey():
	""" Renders appropriate survey for current user or redirects to home page if surveys are not applicable """
	if not current_user.is_anonymous():
		rank_and_score = cached_users.rank_and_score(current_user.id)
		survey_type = "INITIAL"
		setup_geotagx_config_default_params()
		if rank_and_score['score'] > current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS'] and "geotagx_survey_status" in current_user.info.keys() and current_user.info['geotagx_survey_status'] == "AGREE_TO_PARTICIPATE" :
			survey_type = "FINAL"

		if "geotagx_survey_status" in current_user.info.keys() and current_user.info['geotagx_survey_status'] in ["DENY_TO_PARTICIPATE", "DENY_TO_PARTICIPATE_IN_FINAL_SURVEY", "ALL_SURVEYS_COMPLETE"]:
			survey_type = "NONE"

		return render_template('/geotagx/surveys/surveys.html', survey_type = survey_type, GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS = current_app.config['GEOTAGX_FINAL_SURVEY_TASK_REQUIREMENTS'])
	else:
		return redirect(url_for('home.home'))

@blueprint.route('/users/delete/<name>/<confirmed>', methods = ['GET'])
@blueprint.route('/users/delete/<name>', defaults={'confirmed':'unconfirmed'}, methods = ['GET'])
def delete_user(name, confirmed):
	"""
	Deletes a user on pybossa
	- Only admins will be able to delete other users.
	- Does not let delete admin users.
		Admin users will have to remove the user from the admin lists before they can delete then
	- Marks all the task_runs of the specific user as anonymous
	- Changes the ownership of all the projects owned by the user to the current_user
	TODO: Clean this feature up and push this feature to pybossa core
	"""

	"""
	Get the user object and contributed projects object from cache to enable
	global helper functions to render it in a uniform way.
	But Obtain the results from the non-memoized functions to get the latest state
	"""
	target_user = cached_users.get_user_summary(name)
	if current_user.admin and target_user != None and current_user.id != target_user['id'] :

		user_page_redirect = request.args.get('user_page_redirect')
		if not user_page_redirect:
			user_page_redirect = 1

		if confirmed == "unconfirmed":
			published_projects = cached_users.published_projects(target_user['id'])
			draft_projects = cached_users.draft_projects(target_user['id'])
			hidden_projects = cached_users.hidden_projects(target_user['id'])
			owned_projects = published_projects + draft_projects + hidden_projects

			return render_template('geotagx/users/delete_confirmation.html', \
														target_user = target_user,
														owned_projects = owned_projects,
														user_page_redirect=user_page_redirect
														)
		elif confirmed == "confirmed":
			"""
				Retrieval of the User object necessary as the target_user object
				obtained from `cached_users.get_user_summary` doesnot expose
				the `admin` check that is necessary to prevent the user from
				deleting other admin users, and also the SQLAlchemy `delete`
				function
			"""
			user_object = User.query.filter_by(id=target_user['id']).first()
			if user_object.admin:
				# It is not allowed to delete other admin users
				abort(404)

			"""
				Mark all task runs by the user as anonymous
				Mark the user_ip field in the task_run by the username instead
				to retain user identity for analytics
			"""
			task_runs = TaskRun.query.filter_by(user_id=target_user['id']).all()
			for task_run in task_runs:
				task_run.user_id = None
				task_run.user_ip = "deleted_user_"+target_user['name']
				db.session.commit()

			"""
				Change the ownership of all projects owned by the target user
				to that of the current user
			"""
			projects = Project.query.filter_by(owner_id=target_user['id']).all()
			for project in projects:
				project.owner_id = current_user.id
				db.session.commit()
				"""
					Clean cached data about the project
				"""
				cached_projects.clean_project(project.id)

			"""
				Delete the user from the database
			"""
			db.session.delete(user_object)
			db.session.commit()

			"""
				Clean user data from the cache
				Force Update current_user's data in the cache
			"""
			cached_users.delete_user_summary(target_user['id'])
			cached_users.delete_user_summary(current_user.id)

			flash("User <strong>"+target_user['name']+"</strong> has been successfully deleted, and all the projects owned by the user have been transferred to you.", 'success')
			return redirect(url_for('geotagx.users_page', page=user_page_redirect))
		else:
			abort(404)
	else:
		abort(404)

@blueprint.route('/users/', defaults={'page': 1})
@blueprint.route('/users/page/<int:page>')
def users_page(page):
    """
    Admin page for all PyBossa registered users.
    Returns a Jinja2 rendered template with the users.

    Note ::
    This would be an admin only page, hence, rendering cached data
    not necessary. Instead the admin would rather want the most updated data
    """
    per_page = 24
    pagination = User.query.paginate(page, per_page, False)
    accounts = pagination.items
    count = pagination.total

    """
    Normalize accounts for it to be rendered by the global helper functions we use in the theme
    """
    for k in accounts:
		k.n_task_runs = len(k.task_runs)
		k.registered_ago = pretty_date(k.created)

    if not accounts and page !=1 and not current_user.admin:
        abort(404)

    if current_user.is_authenticated():
        user_id = current_user.id
    else:
        user_id = 'anonymous'
    return render_template('geotagx/users/index.html', accounts = accounts,
                           total = count, pagination_page = str(page),
                           title = "Community", pagination = pagination)


@blueprint.route('/project/<project_short_name>/flush_task_runs', defaults={'confirmed':'unconfirmed'})
@blueprint.route('/project/<project_short_name>/flush_task_runs/<confirmed>')
def flush_task_runs(project_short_name, confirmed):
	project = cached_projects.get_project(project_short_name)
	if current_user.admin or project.owner_id == current_user.id:
		if confirmed == "confirmed":
			associated_task_runs = TaskRun.query.filter_by(project_id=project.id).all()
			for task_run in associated_task_runs:
				db.session.delete(task_run)
				pass
			db.session.commit()

			# Iterate over all tasks associated with the project, and mark them as 'ongoing'
			# Some tasks might be marked as 'completed' if enough task_runs were done
			associated_tasks = Task.query.filter_by(project_id=project.id).all()
			for task in associated_tasks:
				if task.state != u"ongoing":
					task.state = u"ongoing"
					db.session.commit()

			# Reset project data in the cache
			cached_projects.clean_project(project.id)
			# Note: The cache will hold the old data about the users who contributed
			# to the tasks associated with this projects till the User Cache Timeout.
			# Querying the list of contributors to this project, and then individually updating
			# their cache after that will be a very expensive query, hence we will avoid that
			# for the time being.
			flash('All Task Runs associated with this project have been successfully deleted.', 'success')
			return redirect(url_for('project.task_settings', short_name = project_short_name))
		elif confirmed == "unconfirmed":
			# Obtain data required by the project profile renderer
		    (project, owner, n_tasks, n_task_runs,
		     overall_progress, last_activity, n_results) = projects_view.project_by_shortname(project_short_name)
		    return render_template('geotagx/projects/delete_task_run_confirmation.html',
		                           project=project,
		                           owner=owner,
		                           n_tasks=n_tasks,
		                           n_task_runs=n_task_runs,
		                           overall_progress=overall_progress,
		                           last_activity=last_activity,
		                           n_results=n_results,
		                           n_completed_tasks=cached_projects.n_completed_tasks(project.id),
		                           n_volunteers=cached_projects.n_volunteers(project.id))
		else:
			abort(404)
	else:
		abort(404)

@blueprint.route('/visualize/<short_name>/<int:task_id>')
def visualize(short_name, task_id):
  """Return a file with all the TaskRuns for a given Task"""
  # Check if it a supported geotagx project whose schema we know
  if 'GEOTAGX_SUPPORTED_PROJECTS_SCHEMA' in current_app.config.keys() \
		and short_name in current_app.config['GEOTAGX_SUPPORTED_PROJECTS_SCHEMA'].keys():
	  # Check if the project exists
	  (project, owner, n_tasks, n_task_runs,
	   overall_progress, last_activity) = projects_view.project_by_shortname(short_name)

	  ensure_authorized_to('read', project)
	  redirect_to_password = projects_view._check_if_redirect_to_password(project)
	  if redirect_to_password:
	      return redirect_to_password

	  # Check if the task belongs to the project and exists
	  task = task_repo.get_task_by(project_id=project.id, id=task_id)
	  if task:
	      taskruns = task_repo.filter_task_runs_by(task_id=task_id, project_id=project.id)
	      results = [tr.dictize() for tr in taskruns]
	      return render_template('geotagx/projects/task_runs_visualize.html',
			                           project=project,
			                           owner=owner,
			                           n_tasks=n_tasks,
			                           n_task_runs=n_task_runs,
			                           overall_progress=overall_progress,
			                           last_activity=last_activity,
			                           n_completed_tasks=cached_projects.n_completed_tasks(project.id),
			                           n_volunteers=cached_projects.n_volunteers(project.id),
			                           task_info = task.info,
			                           task_runs_json = results,
			                           geotagx_project_template_schema = \
			                           	current_app.config['GEOTAGX_SUPPORTED_PROJECTS_SCHEMA'][short_name])
	  else:
	      return abort(404)
  else:
  	return abort(404)


@blueprint.route('/users/export')
@login_required
@admin_required
def export_users():
    """Export Users list in the given format, only for admins."""
    exportable_attributes = ('id', 'name', 'fullname', 'email_addr',
                             'created', 'locale', 'admin')

    def respond_json():
        tmp = 'attachment; filename=all_users.json'
        res = Response(gen_json(), mimetype='application/json')
        res.headers['Content-Disposition'] = tmp
        return res

    def gen_json():
        users = user_repo.get_all()
        json_users = []
        for user in users:
          json_datum = dictize_with_exportable_attributes(user)
          if 'geotagx_survey_status' in user.info.keys():
            json_datum['geotagx_survey_status'] = user.info['geotagx_survey_status']
          else:
            json_datum['geotagx_survey_status'] = "RESPONSE_NOT_TAKEN"

          # Append total task_runs to json export data
          json_datum['task_runs'] = len(TaskRun.query.filter(TaskRun.user_id == user.id).all())
          json_users.append(json_datum)
        return json.dumps(json_users)

    def dictize_with_exportable_attributes(user):
        dict_user = {}
        for attr in exportable_attributes:
            dict_user[attr] = getattr(user, attr)
        return dict_user

    def respond_csv():
        out = StringIO()
        writer = UnicodeWriter(out)
        tmp = 'attachment; filename=all_users.csv'
        res = Response(gen_csv(out, writer, write_user), mimetype='text/csv')
        res.headers['Content-Disposition'] = tmp
        return res

    def gen_csv(out, writer, write_user):
        add_headers(writer)
        for user in user_repo.get_all():
            write_user(writer, user)
        yield out.getvalue()

    def write_user(writer, user):
        values = [getattr(user, attr) for attr in sorted(exportable_attributes)]
        if 'geotagx_survey_status' in user.info.keys():
          values.append(user.info['geotagx_survey_status'])
        else:
          values.append('RESPONSE_NOT_TAKEN')

        # Add total task_runs by the user
        values.append(len(TaskRun.query.filter(TaskRun.user_id == user.id).all()))
        writer.writerow(values)

    def add_headers(writer):
        writer.writerow(sorted(exportable_attributes) + ['geotagx_survey_status', 'task_runs'])

    export_formats = ["json", "csv"]

    fmt = request.args.get('format')
    if not fmt:
        return redirect(url_for('.index'))
    if fmt not in export_formats:
        abort(415)
    return {"json": respond_json, "csv": respond_csv}[fmt]()

"""
	Basic implementation of the geotagx-sourcerer-proxy which ingests images from multiple sources
"""
@blueprint.route('/sourcerer-proxy', methods = ['GET', 'POST'])
def sourcerer_proxy():
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
def sourcerer_categories():
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
@blueprint.route('/sourcerer/dashboard')
@login_required
@admin_required
def sourcerer_dashboard():
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

@blueprint.route('/sourcerer/commands', methods = ['POST'])
@login_required
@admin_required
def sourcerer_dashboard_commands():
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

"""
	Form class for Newsletter form
"""
class NewsletterForm(Form):
  subject = TextField("Subject")
  debug_mode = BooleanField("Debug Mode")
  message = TextAreaField("Message")
  submit = SubmitField("Send")

"""
	Endpoint to send newsletter to all subscribersIL
"""
EMAIL_REGEX = "([^@|\s]+@[^@]+\.[^@|\s]+)"
@blueprint.route('/newsletter', methods=['GET', 'POST'])
@login_required
@admin_required
def newsletter():
	form = NewsletterForm()
	if request.method == "POST":
		try:
			if request.form.get('debug_mode'):
				SUBJECT = "DEBUG :: "+request.form['subject']
				EMAIL_LIST = current_app.config['GEOTAGX_NEWSLETTER_DEBUG_EMAIL_LIST']
			else:
				SUBJECT = request.form['subject']
				user_list = User.query.with_entities(User.email_addr).filter(User.subscribed==True).all()
				EMAIL_LIST = []

				for _user_email in user_list:
					if re.match(EMAIL_REGEX, _user_email[0]):
						EMAIL_LIST.append(_user_email[0])

			mail_dict = dict(
					subject=SUBJECT,
					html=markdown.markdown(request.form['message']),
					# recipients=['geotagx@cern.ch'],#The "To" field of the email always points to the geotagx e-group. Also helps in archiving.
				)
			for _email in EMAIL_LIST:
				mail_dict['recipients'] = [_email]
				message = Message(**mail_dict)
				mail.send(message)
			flash("Newsletter sent successfully", 'success')
		except:
			flash("Unable to send newsletter. Please contact the systems administrator.", 'error')

	debug_emails = current_app.config['GEOTAGX_NEWSLETTER_DEBUG_EMAIL_LIST']
	return render_template("/geotagx/newsletter/newsletter.html", form=form, debug_emails=debug_emails )

@blueprint.route('/map-summary/<category_name>')
def map_summary(category_name):
       return render_template("/geotagx/map_summary/summary.html", category_name=category_name)
