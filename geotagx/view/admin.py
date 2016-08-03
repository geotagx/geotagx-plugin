# -*- coding: utf-8 -*-
#
# This module is part of the GeoTag-X PyBossa plugin.
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
from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask import current_app, jsonify, Response
from flask.ext.login import login_required, current_user
from flask.ext.mail import Message
from pybossa.core import db, user_repo, mail
from pybossa.cache import users as cached_users
from pybossa.model.project import Project
from pybossa.model.task_run import TaskRun
from pybossa.model.user import User
from pybossa.util import Pagination, pretty_date, admin_required, UnicodeWriter
from StringIO import StringIO
import re
import json
import markdown

blueprint = Blueprint("geotagx-admin", __name__)


@blueprint.route("/send-newsletter", methods=["GET", "POST"])
@login_required
@admin_required
def send_newsletter():
    """
        Endpoint to send newsletter to all subscribersIL
    """
    from ..model.form.newsletter import NewsletterForm

    form = NewsletterForm()
    if request.method == "POST":
        try:
            if request.form.get('debug_mode'):
                SUBJECT = "DEBUG :: "+request.form['subject']
                EMAIL_LIST = current_app.config['GEOTAGX_NEWSLETTER_DEBUG_EMAIL_LIST']
            else:
                EMAIL_REGEX = "([^@|\s]+@[^@]+\.[^@|\s]+)"
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
            flash("Newsletter sent successfully", "success")
        except:
            flash("Unable to send newsletter. Please contact the systems administrator.", "error")

    debug_emails = current_app.config["GEOTAGX_NEWSLETTER_DEBUG_EMAIL_LIST"]
    return render_template("/geotagx/newsletter/newsletter.html", form=form, debug_emails=debug_emails)


@blueprint.route("/manage-users/", defaults={"page": 1})
@blueprint.route("/manage-users/page/<int:page>")
@login_required
@admin_required
def manage_users(page):
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


@blueprint.route("/export-users")
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



@blueprint.route('/delete-user/<name>/<confirmed>', methods = ['GET'])
@blueprint.route('/delete-user/<name>', defaults={'confirmed':'unconfirmed'}, methods = ['GET'])
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
            owned_projects = published_projects + draft_projects

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
            return redirect(url_for('geotagx-admin.manage_users', page=user_page_redirect))
        else:
            abort(404)
    else:
        abort(404)
