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
from flask import Blueprint, url_for, flash, redirect, current_app, render_template, abort
from pybossa.model.task_run import TaskRun
from pybossa.model.task import Task
from pybossa.auth import ensure_authorized_to
from pybossa.core import db, task_repo
from pybossa.cache import projects as cached_projects
from pybossa.view import projects as projects_view
from flask.ext.login import current_user

blueprint = Blueprint('geotagx', __name__)


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


@blueprint.route('/map-summary/<string:category_short_name>')
def map_summary(category_short_name):
    from pybossa.core import project_repo
    category = project_repo.get_category_by(short_name=category_short_name)
    return render_template("/geotagx/map_summary/summary.html", active_cat=category)
