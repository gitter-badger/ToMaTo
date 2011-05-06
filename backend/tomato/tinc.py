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

from django.db import models

import dummynet, generic, config, os, subprocess, shutil, fault, util

# Interesting: http://minerva.netgroup.uniroma2.it/fairvpn
class TincConnector(generic.Connector):
	def upcast(self):
		return self
		
	def tincname(self, con):
		return "tinc_%s" % con.id

	def get_start_tasks(self):
		import tasks
		taskset = generic.Device.get_start_tasks(self)
		for con in self.connection_set_all():
			taskset.addTaskSet("connection-%s" % con, con.upcast().get_start_tasks())
		return taskset

	def get_stop_tasks(self):
		import tasks
		taskset = generic.Device.get_stop_tasks(self)
		for con in self.connection_set_all():
			taskset.addTaskSet("connection-%s" % con, con.upcast().get_stop_tasks())
		return taskset
		
	def get_prepare_tasks(self):
		import tasks
		taskset = generic.Device.get_stop_tasks(self)
		for con in self.connection_set_all():
			taskset.addTaskSet("connection-%s" % con, con.upcast().get_prepare_tasks())
		taskset.addTask(tasks.Task("created-host-files", depends=["connection-%s-create-host-file" % con for con in self.connection_set_all()]))
		return taskset

	def get_destroy_tasks(self):
		import tasks
		taskset = generic.Device.get_stop_tasks(self)
		for con in self.connection_set_all():
			taskset.addTaskSet("connection-%s" % con, con.upcast().get_destroy_tasks())
		return taskset

	def configure(self, properties):
		generic.Connector.configure(self, properties)
	
	def connections_add(self, iface_name, properties):
		iface = self.topology.interfaces_get(iface_name)
		if self.state == generic.State.STARTED or self.state == generic.State.PREPARED:
			raise fault.Fault(fault.INVALID_TOPOLOGY_STATE_TRANSITION, "Cannot add connections to started or prepared connector: %s -> %s" % (iface_name, self.name) )
		if iface.device.state == generic.State.STARTED:
			raise fault.Fault(fault.INVALID_TOPOLOGY_STATE_TRANSITION, "Cannot add connections to running device: %s -> %s" % (iface_name, self.name) )
		if iface.is_connected():
			raise fault.Fault(fault.INVALID_TOPOLOGY_STATE_TRANSITION, "Cannot add connections to connected interface: %s -> %s" % (iface_name, self.name) )
		con = TincConnection ()
		con.connector = self
		con.interface = iface
		con.configure(properties)
		con.save()

	def connections_configure(self, iface_name, properties):
		iface = self.topology.interfaces_get(iface_name)
		con = self.connection_set_get(iface)
		con.configure(properties)
		con.save()	
	
	def connections_delete(self, iface_name): #@UnusedVariable, pylint: disable-msg=W0613
		iface = self.topology.interfaces_get(iface_name)
		if self.state == generic.State.STARTED or self.state == generic.State.PREPARED:
			raise fault.Fault(fault.INVALID_TOPOLOGY_STATE_TRANSITION, "Cannot delete connections to started or prepared connector: %s -> %s" % (iface_name, self.name) )
		if iface.device.state == generic.State.STARTED:
			raise fault.Fault(fault.INVALID_TOPOLOGY_STATE_TRANSITION, "Cannot delete connections to running devices: %s -> %s" % (iface_name, self.name) )
		con = self.connection_set_get(iface)
		con.delete()

	def get_resource_usage(self):
		if self.state == generic.State.CREATED:
			disk = 0
		else:
			disk = 10000   
		if self.state == generic.State.STARTED:
			ports = len(self.connection_set_all())
			memory = ( 1200 + 250 * ports ) * 1024
		else:
			memory = 0
			ports = 0
		traffic = 0
		for con in self.connection_set_all():
			dev = con.interface.device
			if dev.host:
				br = self.bridge_name(con.interface)
				try:
					traffic += int(dev.host.execute("[ -f /sys/class/net/%s/statistics/rx_bytes ] && cat /sys/class/net/%s/statistics/rx_bytes || echo 0" % (br, br) ))
					traffic += int(dev.host.execute("[ -f /sys/class/net/%s/statistics/tx_bytes ] && cat /sys/class/net/%s/statistics/tx_bytes || echo 0" % (br, br) ))
				except:
					traffic = -1
		return {"disk": disk, "memory": memory, "ports": ports, "traffic": traffic}		


class TincConnection(dummynet.EmulatedConnection):
	def upcast(self):
		return self
	
	def configure(self, properties):
		if "gateway4" in properties or "gateway6" in properties:
			assert self.connector.state == generic.State.CREATED, "Cannot change gateways on prepared or started router: %s" % self
		dummynet.EmulatedConnection.configure(self, properties)
		if self.connector.type == "router":
			if not self.attributes["gateway4"]:
				self.attributes["gateway4"] = "10.0.0.254/24" 
			if not self.attributes["gateway6"]:
				self.attributes["gateway6"] = "fd01:ab1a:b1ab:0:0:FFFF:FFFF:FFFF/80" 
			if not len(self.attributes["gateway4"].split("/")) == 2:
				self.attributes["gateway4"] = self.attributes["gateway4"] + "/24"
			if not len(self.attributes["gateway6"].split("/")) == 2:
				self.attributes["gateway6"] = self.attributes["gateway6"] + "/80"
		
	def _start_tinc(self):
		host = self.interface.device.host
		connector = self.connector.upcast()
		tincname = connector.tincname(self)
		host.free_port(self.attributes["tinc_port"])		
		host.execute ( "tincd --net=%s" % tincname)
		if not config.remote_dry_run:
			assert host.interface_exists(tincname), "Tinc deamon did not start"
		host.execute ( "ifconfig %s 0.0.0.0 up" %  tincname)

	def _setup_routing(self):
		host = self.interface.device.host
		connector = self.connector.upcast()
		tincname = connector.tincname(self)
		host.execute ("sysctl -q -w net.ipv6.conf.all.forwarding=1");
		host.execute ("sysctl -q -w net.ipv4.conf.all.forwarding=1");
		table_in = 1000 + 2 * self.id
		table_out = 1000 + 2 * self.id + 1 
		host.execute ( "ip addr add %s dev %s" % (self.attributes["gateway4"], self.bridge_name()))
		host.execute ( "ip addr add %s dev %s" % (self.attributes["gateway6"], self.bridge_name()))
		host.execute ( "ip link set up dev %s" % self.bridge_name())
		host.execute ( "grep '^%s ' /etc/iproute2/rt_tables || echo \"%s %s\" >> /etc/iproute2/rt_tables" % ( table_in, table_in, table_in ))
		host.execute ( "grep '^%s ' /etc/iproute2/rt_tables || echo \"%s %s\" >> /etc/iproute2/rt_tables" % ( table_out, table_out, table_out ))
		host.execute ( "iptables -t mangle -A PREROUTING -i %s -j MARK --set-mark %s" % ( tincname, table_in ))
		host.execute ( "iptables -t mangle -A PREROUTING -i %s -j MARK --set-mark %s" % ( self.bridge_name(), table_out ))
		host.execute ( "ip rule add fwmark %s table %s" % ( hex(table_in), table_in ))
		host.execute ( "ip rule add fwmark %s table %s" % ( hex(table_out), table_out ))
		host.execute ( "ip route add table %s default dev %s" % ( table_in, self.bridge_name() ))
		host.execute ( "ip route add table %s default dev %s" % ( table_out, tincname ))

	def _connect_bridge(self):
		host = self.interface.device.host
		tincname = self.connector.upcast().tincname(self)
		host.bridge_connect(self.bridge_name(), tincname)
		
	def get_start_tasks(self):
		import tasks
		taskset = dummynet.EmulatedConnection.get_start_tasks(self)
		taskset.addTask(tasks.Task("start-tinc", self._start_tinc))
		if self.connector.type == "router":
			taskset.addTask(tasks.Task("setup-routing", self._setup_routing, depends="start-tinc"))
		else:
			taskset.addTask(tasks.Task("connect-bridge", self._connect_bridge, depends="start-tinc"))
		return taskset
		
	def _teardown_routing(self):
		host = self.interface.device.host
		connector = self.connector.upcast()
		tincname = connector.tincname(self)
		table_in = 1000 + 2 * self.id
		table_out = 1000 + 2 * self.id + 1
		host.execute ( "iptables -t mangle -D PREROUTING -i %s -j MARK --set-mark %s" % ( tincname, table_in ))
		host.execute ( "iptables -t mangle -D PREROUTING -i %s -j MARK --set-mark %s" % ( self.bridge_name(), table_out ))
		host.execute ( "ip rule del fwmark %s table %s" % ( hex(table_in), table_in ))
		host.execute ( "ip rule del fwmark %s table %s" % ( hex(table_out), table_out ))
		host.execute ( "ip route del table %s default dev %s" % ( table_in, self.bridge_name() ))
		host.execute ( "ip route del table %s default dev %s" % ( table_out, tincname ))
		
	def _stop_tinc(self):
		host = self.interface.device.host
		connector = self.connector.upcast()
		tincname = connector.tincname(self)
		host.execute ( "tincd --net=%s -k" % tincname)		
		
	def get_stop_tasks(self):
		import tasks
		taskset = dummynet.EmulatedConnection.get_stop_tasks(self)
		if self.interface.device.host:
			taskset.addTask(tasks.Task("stop-tinc", self._stop_tinc))
			if self.connector.type == "router":
				taskset.addTask(tasks.Task("teardown-routing", self._teardown_routing))

	def _assign_bridge_id(self):
		if not self.attributes["bridge_id"]:
			self.attributes["bridge_id"] = self.interface.device.host.next_free_bridge()		
			self.save()

	def _assign_tinc_port(self):
		if not self.attributes["tinc_port"]:
			self.attributes["tinc_port"] = self.interface.device.host.next_free_port()
			self.save()

	def _create_host_file(self):
		host = self.interface.device.host
		connector = self.connector.upcast()
		tincname = connector.tincname(self)
		tincport = self.attributes["tinc_port"] 
		path = connector.topology.get_control_dir(host.name) + "/" + tincname
		if not os.path.exists(path+"/hosts"):
			os.makedirs(path+"/hosts")
		subprocess.check_call (["openssl",  "genrsa",  "-out",  path + "/rsa_key.priv"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		self_host_fd = open(path+"/hosts/"+tincname, "w")
		self_host_fd.write("Address=%s\n" % host.name)
		self_host_fd.write("Port=%s\n" % tincport )
		self_host_fd.write("Cipher=none\n" )
		self_host_fd.write("Digest=none\n" )
		if connector.type == "router":
			self_host_fd.write("Subnet=%s\n" % util.calculate_subnet4(self.attributes["gateway4"]))
			self_host_fd.write("Subnet=%s\n" % util.calculate_subnet6(self.attributes["gateway6"]))
		subprocess.check_call (["openssl",  "rsa", "-pubout", "-in",  path + "/rsa_key.priv", "-out",  path + "/hosts/" + tincname + ".pub"], stderr=subprocess.PIPE)
		self_host_pub_fd = open(path+"/hosts/"+tincname+".pub", "r")
		shutil.copyfileobj(self_host_pub_fd, self_host_fd)
		self_host_fd.close()
		self_host_pub_fd.close()
		
	def _create_config_file(self):
		host = self.interface.device.host
		connector = self.connector.upcast()
		tincname = connector.tincname(self)
		path = connector.topology.get_control_dir(host.name) + "/" + tincname
		tinc_conf_fd = open(path+"/tinc.conf", "w")
		tinc_conf_fd.write ( "Mode=%s\n" % connector.type )
		tinc_conf_fd.write ( "Name=%s\n" % tincname )
		tinc_conf_fd.write ( "AddressFamily=ipv4\n" )
		for con2 in connector.connection_set_all():
			tincname2 = connector.tincname(con2)
			if not tincname == tincname2:
				tinc_conf_fd.write ( "ConnectTo=%s\n" % tincname2 )
		tinc_conf_fd.close()

	def _collect_host_files(self):
		host = self.interface.device.host
		connector = self.connector.upcast()
		tincname = connector.tincname(self)
		path = connector.topology.get_control_dir(host.name) + "/" + tincname
		for con2 in connector.connection_set_all():
			if self == con2:
				continue
			host2 = con2.interface.device.host
			tincname2 = connector.tincname(con2)
			path2 = connector.topology.get_control_dir(host2.name) + "/" + tincname2
			shutil.copy(path2+"/hosts/"+tincname2, path+"/hosts/"+tincname2)

	def _upload_files(self):
		host = self.interface.device.host
		connector = self.connector.upcast()
		tincname = connector.tincname(self)
		path = connector.topology.get_control_dir(host.name) + "/" + tincname + "/"
		host.file_put(path, "/etc/tinc/" + tincname)

	def get_prepare_tasks(self):
		import tasks
		taskset = dummynet.EmulatedConnection.get_prepare_tasks(self)
		taskset.addTask(tasks.Task("assign-bridge-id", self._assign_bridge_id))
		taskset.addTask(tasks.Task("assign-tinc-port", self._assign_tinc_port))
		taskset.addTask(tasks.Task("create-host-file", self._create_host_file, depends=["assign-bridge-id", "assign-tinc-port"]))
		taskset.addTask(tasks.Task("create-config-file", self._create_config_file, depends=["assign-bridge-id", "assign-tinc-port"]))
		taskset.addTask(tasks.Task("collect-host-files", self._collect_host_files, depends="created-host-files"))
		taskset.addTask(tasks.Task("upload-files", self._upload_files, depends=["collect-host-files", "create-config-file"]))
		return taskset
		
	def _unassign_bridge_id(self):
		del self.attributes["bridge_id"]

	def _unassign_tinc_port(self):
		del self.attributes["tinc_port"]

	def _delete_files(self):
		host = self.interface.device.host
		connector = self.connector.upcast()
		tincname = connector.tincname(self)
		host.file_delete ( "/etc/tinc/%s" % tincname, recursive=True)
		
	def get_destroy_tasks(self):
		import tasks
		taskset = dummynet.EmulatedConnection.get_destroy_tasks(self)
		if self.interface.device.host:
			taskset.addTask(tasks.Task("delete-files", self._delete_files))
		taskset.addTask(tasks.Task("unassign-bridge-id", self._unassign_bridge_id))
		taskset.addTask(tasks.Task("unassign-tinc-port", self._unassign_tinc_port))
		return taskset

	def to_dict(self, auth):
		res = dummynet.EmulatedConnection.to_dict(self, auth)	
		if not auth:
			del res["attrs"]["tinc_port"]	
			del res["attrs"]["bridge_id"]	
		return res
