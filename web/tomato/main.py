# -*- coding: utf-8 -*-

# ToMaTo (Topology management software) 
# Copyright (C) 2010 Dennis Schwerdel, University of Kaiserslautern
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render_to_response

from lib import *
import xmlrpclib, settings

def index(request):
	return render_to_response("main/start.html")

@wrap_rpc
def error_list(api, request):
	errors = api.errors_all()
	return render_to_response("admin/error_list.html", {'errors': errors})

@wrap_rpc
def error_remove(api, request, error_id):
	api.errors_remove(error_id)
	return error_list(request)

@wrap_rpc
def task_list(api, request):
	tasks = api.task_list()
	return render_to_response("admin/task_list.html", {'tasks': tasks})

@wrap_rpc
def task_status(api, request, task_id):
	task = api.task_status(task_id)
	backurl=""
	if request.REQUEST.has_key("backurl"):
		backurl=request.REQUEST["backurl"]
	return render_to_response("main/task.html", {'task': task, 'backurl': backurl})

@wrap_rpc
def physical_links(api, request):
	links = api.physical_links_get_all()
	for l in links:
		l["loss"] = l["loss"] * 100.0
	return render_to_response("admin/physical_links.html", {"links": links})

@wrap_rpc
def resource_usage_by_topology(api, request):
	usage_by_top = api.resource_usage_by_topology()
	usage=[(user, usage_by_top[user]) for user in usage_by_top]
	return render_to_response("admin/resource_usage.html", {"usage": usage})

@wrap_rpc
def resource_usage_by_user(api, request):
	usage_by_user = api.resource_usage_by_user()
	usage=[(user, usage_by_user[user]) for user in usage_by_user]
	return render_to_response("admin/resource_usage.html", {"by_user": True, "usage": usage})

def help(request, page=""):
	return HttpResponseRedirect(settings.help_url % page)

def ticket(request, page=""):
	return HttpResponseRedirect(settings.ticket_url % page)