# -*- coding: utf-8 -*-

from connector import *
from util import *

class RealNetworkConnector(Connector):

	def __init__(self, topology, dom):
		Connector.__init__(self, topology, dom)
		if not self.bridge_name:
			self.bridge_name = "vmbr0"
		for con in self.connections:
			con.bridge_name = self.bridge_name
	bridge_name=property(curry(Connector.get_attr,"bridge_name"),curry(Connector.set_attr,"bridge_name"))

	def retake_resources(self):
		pass

	def take_resources(self):
		pass

	def free_resources(self):
		pass

	def write_deploy_script(self):
		print "\tcreating scripts for real network %s ..." % ( self.id )
		# not invoking con.write_deploy_script()
		for con in self.connections:
			host = con.interface.device.host
			bridge_name=con.bridge_name
			start_fd=open(self.topology.get_deploy_script(host.name,"start"), "a")
			start_fd.close ()
			stop_fd=open(self.topology.get_deploy_script(host.name,"stop"), "a")
			stop_fd.close ()
