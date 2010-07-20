# -*- coding: utf-8 -*-

from xml.dom import minidom

from openvz_device import *
from dhcpd_device import *
from tinc_connector import *
from real_network_connector import *
from config import *

import shutil

class Topology(object):
  
	def __init__ (self, file):
		self.devices={}
		self.connectors={}
		self.load_from(file)
		
	def add_device ( self, device ):
		device.topology = self
		self.devices[device.id] = device
		
	def add_connector ( self, connector ):
		connector.topology = self
		self.connectors[connector.id] = connector
		
	def load_from ( self, file ):
		dom = minidom.parse ( file )
		x_top = dom.getElementsByTagName ( "topology" )[0]
		if x_top.hasAttribute("id"):
			self.id = x_top.getAttribute("id")
		else:
			self.id = str(ResourceStore.topology_ids.take())
		for x_dev in x_top.getElementsByTagName ( "device" ):
			Type = { "openvz": OpenVZDevice, "dhcpd": DhcpdDevice }[x_dev.getAttribute("type")]
			self.add_device ( Type ( self, x_dev ) )
		for x_con in x_top.getElementsByTagName ( "connector" ):
			Type = { "hub": TincConnector, "switch": TincConnector, "router": TincConnector, "real": RealNetworkConnector }[x_con.getAttribute("type")]
			self.add_connector ( Type ( self, x_con ) )
			
	def save_to ( self, file ):
		dom = minidom.Document()
		x_top = dom.createElement ( "topology" )
		x_top.setAttribute("id", str(self.id))
		dom.appendChild ( x_top )
		for dev in self.devices.values():
			x_dev = dom.createElement ( "device" )
			dev.encode_xml ( x_dev, dom )
			x_top.appendChild ( x_dev )
		for con in self.connectors.values():
			x_con = dom.createElement ( "connector" )
			con.encode_xml ( x_con, dom )
			x_top.appendChild ( x_con )
		fd = open ( file, "w" )
		dom.writexml(fd, indent="", addindent="\t", newl="\n", encoding="")
		fd.close()

	def take_resources ( self ):
		for dev in self.devices.values():
			dev.take_resources()
		for con in self.connectors.values():
			con.take_resources()

	def free_resources ( self ):
		for dev in self.devices.values():
			dev.free_resources()
		for con in self.connectors.values():
			con.free_resources()

	def affected_hosts (self):
		hosts=set()
		for dev in self.devices.values():
			hosts.add(dev.host)
		return hosts

	def get_deploy_dir(self,host_name):
		return Config.local_deploy_dir+"/"+host_name

	def get_deploy_script(self,host_name,script):
		return self.get_deploy_dir(host_name)+"/"+script+".sh"

	def deploy(self):
		self.write_deploy_scripts()
		self.upload_deploy_scripts()
	
	def write_deploy_scripts(self):
		if Config.local_deploy_dir and os.path.exists(Config.local_deploy_dir):
			shutil.rmtree(Config.local_deploy_dir)
		for host in self.affected_hosts():
			dir=self.get_deploy_dir(host.name)
			if not os.path.exists(dir):
				os.makedirs(dir)
		for dev in self.devices.values():
			dev.write_deploy_script()
		for con in self.connectors.values():
			con.write_deploy_script()

	def upload_deploy_scripts(self):
		for host in affected_hosts():
			src = self.get_deploy_dir(host.name)
			dst = "root@%s:%s/%s" % ( host.name, Config.remote_deploy_dir, self.id )
			subprocess.check_call (["rsync",  "-Pav",  src, dst])
	
	def exec_script(self, script):
		script = "%s/%s/%s.sh" % ( Config.remote_deploy_dir, self.id, script )
		for host in affected_hosts():
			subprocess.check_call (["ssh",  "root@%s" % host.name, script ])

	def start(self):
		self.exec_script("start")

	def stop(self):
		self.exec_script("stop")

	def create(self):
		self.exec_script("create")

	def destroy(self):
		self.exec_script("destroy")

	def output(self):
		for device in self.devices.values():
			print "Device %s on host %s type %s" % ( device.id, device.host_id, device.type )
			for interface in device.interfaces.values():
				print "\t Interface %s" % interface.id
		for connector in self.connectors.values():
			print "Connector %s type %s" % ( connector.id, connector.type )
			for connection in connector.connections:
				print "\t Interface %s.%s" % ( connection.interface.device.id, connection.interface.id )
