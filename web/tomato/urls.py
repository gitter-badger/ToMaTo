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

from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
	(r'^$', 'tomato.main.index'),
	(r'^img/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'img'}),
	(r'^js/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'js'}),
	(r'^style/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'style'}),
	(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'static'}),
	(r'^help$', 'tomato.main.help'),
	(r'^help/(?P<page>.*)$', 'tomato.main.help'),
	(r'^ticket$', 'tomato.main.ticket'),
	(r'^project$', 'tomato.main.project'),
	(r'^logout$', 'tomato.main.logout'),
	(r'^topology/$', 'tomato.topology.index'),
	(r'^topology/(?P<id>\d+)$', 'tomato.topology.info'),
	(r'^topology/(?P<id>\d+)/usage$', 'tomato.topology.usage'),
	(r'^topology/create$', 'tomato.topology.create'),
	(r'^topology/import$', 'tomato.topology.import_form'),
	(r'^element/(?P<id>\d+)/usage$', 'tomato.element.usage'),
	(r'^element/(?P<id>\d+)/console$', 'tomato.element.console'),
	(r'^host/$', 'tomato.host.index'),
	(r'^host/add$', 'tomato.host.add'), #adapt path in input (buttons) in templates/admin/host/index.html
	(r'^host/remove$', 'tomato.host.remove'), #adapt path in script in templates/admin/host/index.html
	(r'^site/$', 'tomato.site.index'),
	(r'^site/add$', 'tomato.site.add'), #adapt path in input (buttons) in templates/admin/site/index.html
	(r'^site/remove$', 'tomato.site.remove'), #adapt path in script in templates/admin/site/index.html
	(r'^ajax/topology/(?P<id>\d+)/info$', 'tomato.ajax.topology_info'),
	(r'^ajax/topology/(?P<id>\d+)/action$', 'tomato.ajax.topology_action'),
	(r'^ajax/topology/(?P<id>\d+)/modify$', 'tomato.ajax.topology_modify'),
	(r'^ajax/element/(?P<id>\d+)/info$', 'tomato.ajax.element_info'),
	(r'^ajax/topology/(?P<topid>\d+)/create_element$', 'tomato.ajax.element_create'),
	(r'^ajax/element/(?P<id>\d+)/action$', 'tomato.ajax.element_action'),
	(r'^ajax/element/(?P<id>\d+)/modify$', 'tomato.ajax.element_modify'),
	(r'^ajax/element/(?P<id>\d+)/remove$', 'tomato.ajax.element_remove'),
	(r'^ajax/connection/(?P<id>\d+)/info$', 'tomato.ajax.connection_info'),
	(r'^ajax/connection/create$', 'tomato.ajax.connection_create'),
	(r'^ajax/connection/(?P<id>\d+)/action$', 'tomato.ajax.connection_action'),
	(r'^ajax/connection/(?P<id>\d+)/modify$', 'tomato.ajax.connection_modify'),
	(r'^ajax/connection/(?P<id>\d+)/remove$', 'tomato.ajax.connection_remove'),
)
