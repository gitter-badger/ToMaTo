from models import *
DATABASE = 'test'
connect(DATABASE)

def loadDumpData(file):
	import ujson as json
	print "loading dump..."
	with open(file) as fp:
		data = json.load(fp)
	return data

def convertData(data):
	import ujson as json
	print "converting data..."
	db = {}
	for entry in data:
		model = entry['model']
		if model.startswith('tomato.'):
			model = model[7:]
		if not model in db:
			db[model] = {}
		table = db[model]
		pk = entry['pk']
		dat = entry['fields']
		if 'attrs' in dat:
			attrs = json.loads(dat['attrs'])
			dat.update(attrs)
			del dat['attrs']
		dat['id'] = pk
		table[pk] = dat
	del db['south.migrationhistory']
	return db

def fixKeys(data):
	if isinstance(data, dict):
		for k, v in data.items():
			if '.' in k:
				del data[k]
				k = k.replace('.', '_')
			data[k] = fixKeys(v)
	elif isinstance(data, list):
		data = map(fixKeys, data)
	return data

def getData():
	data = loadDumpData('dump.json')
	data = convertData(data)
	return data

def modifyDict(data, rename=None, remove=None, emptyToNone=False):
	data = dict(data)
	if not remove:
		remove = []
	if not rename:
		rename = {}
	for old, new in (rename.items() if isinstance(rename, dict) else rename):
		if old in data:
			data[new] = data[old]
			del data[old]
	for name in remove:
		if name in data:
			del data[name]
	if emptyToNone:
		for key, value in data.items():
			if value == '':
				data[key] = None
	return data

def importData(data):
	print "importing objects..."
	print "\tUsage..."
	usages = {}
	for key, entry in data['usage'].items():
		entry = modifyDict(entry, remove=['id'])
		usages[key] = Usage(**entry)
	print "\tUsage statistics..."
	UsageStatistics.objects.delete()
	usagestatistics = {}
	for key, entry in data['usagestatistics'].items():
		obj = UsageStatistics()
		obj.save()
		usagestatistics[key] = obj
	print "\tUsage records..."
	usagerecords = {}
	for key, entry in data['usagerecord'].items():
		stats = usagestatistics.get(entry['statistics'])
		if not stats:
			print "\t\tInvalid reference: UsageRecord[%d] -> Statistics[%d]" % (key, entry['statistics'])
			continue
		usage = usages.get(entry['usage'])
		if not usage:
			print "\t\tInvalid reference: UsageRecord[%d] -> Usage[%d]" % (key, entry['usage'])
			continue
		entry = modifyDict(entry, remove=['id', 'usage', 'statistics'])
		obj = UsageRecord(usage=usage, **entry)
		usagerecords[key] = obj
		stats.records.append(obj)
	for stats in usagestatistics.values():
		stats.save()
	print "\tQuotas..."
	quotas = {}
	for key, entry in data['quota'].items():
		monthly = usages.get(entry['monthly'])
		if not monthly:
			print "\t\tInvalid reference: Quota[%d] -> Usage[%d]" % (key, entry['monthly'])
		used = usages.get(entry['used'])
		if not used:
			print "\t\tInvalid reference: Quota[%d] -> Usage[%d]" % (key, entry['used'])
		entry = modifyDict(entry, rename={'used_time': 'usedTime', 'continous_factor': 'continousFactor'},
			remove=['id', 'used', 'monthly'])
		obj = Quota(monthly=monthly, used=used, **entry)
		quotas[key] = obj
	print "\tOrganizations..."
	Organization.objects().delete()
	organizations = {}
	for key, entry in data['organization'].items():
		totalUsage = usagestatistics.get(entry['totalUsage'])
		if not totalUsage:
			print "\t\tInvalid reference: Organization[%d] -> UsageStatistics[%d]" % (key, entry['totalUsage'])
		entry = modifyDict(entry, rename=(('description', 'label'), ('description_text', 'description'),
			('homepage_url', 'homepageUrl'), ('image_url', 'imageUrl')), remove=['id', 'totalUsage'], emptyToNone=True)
		obj = Organization(totalUsage=totalUsage, **entry)
		obj.save()
		organizations[key] = obj
	print "\tSites..."
	Site.objects.delete()
	sites = {}
	for key, entry in data['site'].items():
		orga = organizations.get(entry['organization'])
		if not orga:
			print "\t\tInvalid reference: Site[%d] -> Organization[%d]" % (key, entry['organization'])
		entry = modifyDict(entry, rename=(('description', 'label'), ('description_text', 'description')),
			remove=['id', 'organization'], emptyToNone=True)
		entry['geolocation'] = (entry['geolocation']['latitude'], entry['geolocation']['longitude'])
		site = Site(organization=orga, **entry)
		site.save()
		sites[key] = site
	print "\tUsers..."
	User.objects.delete()
	users = {}
	for key, entry in data['user'].items():
		orga = organizations.get(entry['organization'])
		if not orga:
			print "\t\tInvalid reference: User[%d] -> Organization[%d]" % (key, entry['organization'])
		totalUsage = usagestatistics.get(entry['totalUsage'])
		if not totalUsage:
			print "\t\tInvalid reference: User[%d] -> UsageStatistics[%d]" % (key, entry['totalUsage'])
		quota = quotas.get(entry['quota'])
		if not quota:
			print "\t\tInvalid reference: User[%d] -> Quota[%d]" % (key, entry['quota'])
		entry = modifyDict(entry, rename=(('password_time', 'passwordTime'), ('last_login', 'lastLogin')),
			remove=['id', 'organization', 'totalUsage', 'quota'])
		obj = User(organization=orga, totalUsage=totalUsage, quota=quota, **entry)
		obj.save()
		users[key] = obj
	print "\tPermissions..."
	permissions = {}
	for key, entry in data['permissions'].items():
		permissions[key] = []
	for key, entry in data['permissionentry'].items():
		user = users.get(entry['user'])
		if not user:
			print "\t\tInvalid reference: PermissionEntry[%d] -> User[%d]" % (key, entry['user'])
			continue
		permission = permissions.get(entry['set'])
		if permission is None:
			print "\t\tInvalid reference: PermissionEntry[%d] -> Permission[%d]" % (key, entry['set'])
			continue
		entry = modifyDict(entry, remove=['id', 'user'])
		obj = Permission(user=user, **entry)
		permission.append(obj)
	print "\tErrorgroups..."
	ErrorGroup.objects.delete()
	errorgroups = {}
	for key, entry in data['errorgroup'].items():
		entry = modifyDict(entry, rename={'id': 'groupId', 'removed_dumps': 'removedDumps'})
		obj = ErrorGroup(**entry)
		obj.save()
		errorgroups[key] = obj
	print "\tErrordumps..."
	import ujson as json
	for key, entry in data['errordump'].items():
		group = errorgroups.get(entry['group'])
		entry['description'] = json.loads(entry['description'])
		if not group:
			print "\t\tInvalid reference: Error[%s] -> Errorgroup[%s]" % (key, entry['group'])
			continue
		entry = modifyDict(entry, rename={'dump_id': 'dumpId', 'data_available': 'dataAvailable',
			'software_version': 'softwareVersion'}, remove=['group'])
		obj = ErrorDump(**entry)
		group.dumps.append(obj)
	for obj in errorgroups.values():
		obj.save()
	print "\tHosts..."
	Host.objects.delete()
	hosts = {}
	for key, entry in data['host'].items():
		totalUsage = usagestatistics.get(entry['totalUsage'])
		if not totalUsage:
			print "\t\tInvalid reference: Host[%d] -> UsageStatistics[%d]" % (key, entry['totalUsage'])
		site = sites.get(entry['site'])
		if not site:
			print "\t\tInvalid reference: Host[%d] -> Site[%d]" % (key, entry['site'])
			continue
		entry = modifyDict(entry, rename={'info': 'hostInfo', 'problem_mail_time': 'problemMailTime',
			'element_types': 'elementTypes', 'info_timestamp': 'hostInfoTimestamp',
			'last_resources_sync': 'lastResourcesSync', 'connection_types': 'connectionTypes',
			'accounting_timestamp': 'accountingTimestamp', 'dump_last_fetch': 'dumpLastFetch',
			'problem_age': 'problemAge', 'description_text': 'description'},
			remove=['id', 'site', 'totalUsage', 'templates', 'networks'])
		obj = Host(site=site, totalUsage=totalUsage, **entry)
		obj.save()
		hosts[key] = obj
	print "\tNetworks..."
	Network.objects.delete()
	networks = {}
	for key, entry in data['network'].items():
		entry = modifyDict(entry, remove=['id'])
		obj = Network(**entry)
		obj.save()
		networks[key] = obj
	print "\tNetwork instances..."
	NetworkInstance.objects.delete()
	networkinstances = {}
	for key, entry in data['networkinstance'].items():
		host = hosts.get(entry['host'])
		if not host:
			print "\t\tInvalid reference: NetworkInstance[%d] -> Host[%d]" % (key, entry['host'])
			continue
		network = networks.get(entry['network'])
		if not network:
			print "\t\tInvalid reference: NetworkInstance[%d] -> Network[%d]" % (key, entry['network'])
			continue
		entry = modifyDict(entry, remove=['id', 'host', 'network'])
		obj = NetworkInstance(host=host, network=network, **entry)
		obj.save()
		networkinstances[key] = obj
	print "\tProfiles..."
	Profile.objects.delete()
	profiles = {}
	for key, entry in data['profile'].items():
		entry = modifyDict(entry, remove=['id'])
		obj = Profile(**entry)
		try:
			obj.save()
			profiles[key] = obj
		except:
			print "\t\tDuplicate object: %r" % entry
	print "\tTemplates..."
	Template.objects.delete()
	templates = {}
	for key, entry in data['template'].items():
		entry = modifyDict(entry, remove=['id'])
		obj = Template(**entry)
		obj.save()
		templates[key] = obj
	print "\tTemplates on hosts..."
	for key, entry in data['templateonhost'].items():
		host = hosts.get(entry['host'])
		if not host:
			print "\t\tInvalid reference: TemplateOnHost[%d] -> Host[%d]" % (key, entry['host'])
			continue
		template = templates.get(entry['template'])
		if not template:
			print "\t\tInvalid reference: TemplateOnHost[%d] -> Template[%d]" % (key, entry['template'])
			continue
		host.templates.append(template)
	for obj in hosts.values():
		obj.save()
	print "\tTopologies..."
	Topology.objects.delete()
	topologies = {}
	for key, entry in data['topology'].items():
		perms = permissions.get(entry['permissions'])
		if not perms:
			print "\t\tInvalid reference: Topology[%d] -> Permissions[%d]" % (key, entry['permissions'])
		totalUsage = usagestatistics.get(entry['totalUsage'])
		if not totalUsage:
			print "\t\tInvalid reference: Topology[%d] -> UsageStatistics[%d]" % (key, entry['totalUsage'])
		site = sites.get(entry['site'])
		if entry.get('site') and not site:
			print "\t\tInvalid reference: Topology[%d] -> Site[%d]" % (key, entry['site'])
		entry = modifyDict(entry, rename={'timeout_step': 'timeoutStep'}, remove=['id', 'site', 'permissions', 'totalUsage'])
		obj = Topology(permissions=perms, totalUsage=totalUsage, site=site, **entry)
		obj.save()
		topologies[key] = obj
	print "\tLink measurements..."
	LinkMeasurement.objects.delete()
	for key, entry in data['linkmeasurement'].items():
		siteA = sites.get(entry['siteA'])
		if not siteA:
			print "\t\tInvalid reference: LinkMeasurement[%d] -> Site[%d]" % (key, entry['siteA'])
		siteB = sites.get(entry['siteB'])
		if not siteB:
			print "\t\tInvalid reference: LinkMeasurement[%d] -> Site[%d]" % (key, entry['siteB'])
		entry = modifyDict(entry, remove=['id', 'siteA', 'siteB'])
		obj = LinkMeasurement(siteA=siteA, siteB=siteB, **entry)
		obj.save()
	print "\tHost elements..."
	HostElement.objects.delete()
	hostelements = {}
	hostelements_index = {}
	for key, entry in data['hostelement'].items():
		host = hosts.get(entry['host'])
		if not host:
			print "\t\tInvalid reference: HostElement[%d] -> Host[%d]" % (key, entry['host'])
			continue
		usageStatistics = usagestatistics.get(entry['usageStatistics'])
		if not usageStatistics:
			print "\t\tInvalid reference: HostElement[%d] -> UsageStatistics[%d]" % (key, entry['usageStatistics'])
		parent = hostelements_index.get((host.name, entry['parent']))
		if entry['parent'] and not parent:
			print "\t\tInvalid reference: HostElement[%d] -> HostElement[%s, %d]" % (key, host.name, entry['parent'])
		entry = modifyDict(entry, remove=['id', 'host', 'usageStatistics', 'topology_element', 'topology_connection',
			'connection', 'timeout', 'parent', 'children'])
		obj = HostElement(host=host, usageStatistics=usageStatistics, parent=parent, **entry)
		obj.save()
		hostelements[key] = obj
		hostelements_index[(host.name, obj.num)] = obj
	print "\tHost connections..."
	HostConnection.objects.delete()
	hostconnections = {}
	for key, entry in data['hostconnection'].items():
		host = hosts.get(entry['host'])
		if not host:
			print "\t\tInvalid reference: HostConnection[%d] -> Host[%d]" % (key, entry['host'])
			continue
		usageStatistics = usagestatistics.get(entry['usageStatistics'])
		if not usageStatistics:
			print "\t\tInvalid reference: HostConnection[%d] -> UsageStatistics[%d]" % (key, entry['usageStatistics'])
		elems = sorted(entry['elements'])
		entry = modifyDict(entry, remove=['id', 'host', 'usageStatistics', 'topology_element', 'topology_connection', 'elements'])
		obj = HostConnection(host=host, usageStatistics=usageStatistics, **entry)
		hostconnections[key] = obj
		hel1 = hostelements_index.get((host.name, elems[0]))
		if not hel1:
			print "\t\tInvalid reference: HostConnection[%d] -> HostElement[%s, %d]" % (key, host.name, elems[0])
			continue
		hel2 = hostelements_index.get((host.name, elems[1]))
		if not hel2:
			print "\t\tInvalid reference: HostConnection[%d] -> HostElement[%s, %d]" % (key, host.name, elems[1])
			continue
		obj.elementFrom = hel1
		obj.elementTo = hel2
		obj.save()
		hel1.connection = obj
		hel1.save()
		hel2.connection = obj
		hel2.save()
	print "\tElements..."
	Element.objects.delete()
	elements = {}
	elementConnections = {}
	def adaptElement(entry):
		entry = dict(entry)
		elemAttrs = data['element'].get(entry['id'])
		if not elemAttrs:
			print "\t\tElement information not found for element %d" % entry['id']
			return
		entry.update(elemAttrs)
		topology = topologies.get(entry['topology'])
		if not topology:
			print "\t\tInvalid reference: Element[%d] -> Topology[%d]" % (entry['id'], entry['topology'])
			return
		parent = elements.get(entry['parent'])
		if entry['parent'] and not parent:
			print "\t\tInvalid reference: Element[%d] -> Element[%d]" % (entry['id'], entry['parent'])
			return
		perms = permissions.get(entry['permissions'])
		if not perms:
			print "\t\tInvalid reference: Element[%d] -> Permission[%d]" % (entry['id'], entry['permissions'])
			return
		totalUsage = usagestatistics.get(entry['totalUsage'])
		if not totalUsage:
			print "\t\tInvalid reference: Element[%d] -> UsageStatistics[%d]" % (entry['id'], entry['totalUsage'])
			return
		entry.update(topology=topology, parent=parent, permissions=perms, totalUsage=totalUsage)
		con = entry['connection']
		elems = elementConnections.get(con, [])
		elems.append(entry['id'])
		elementConnections[con] = elems
		entry = modifyDict(entry, remove=['id', 'type', 'connection'])
		return entry
	def adaptVmElement(entry):
		entry = adaptElement(entry)
		if not entry:
			return
		elem = hostelements.get(entry['element'])
		if entry['element'] and not elem:
			print "\t\tInvalid reference: Element[%d] -> HostElement[%d]" % (entry['id'], entry['element'])
			return
		site = sites.get(entry['site'])
		if entry['site'] and not site:
			print "\t\tInvalid reference: Element[%d] -> Site[%d]" % (entry['id'], entry['site'])
			return
		profile = profiles.get(entry['profile'])
		if entry['profile'] and not profile:
			print "\t\tInvalid reference: Element[%d] -> Profile[%d]" % (entry['id'], entry['profile'])
			return
		template = templates.get(entry['template'])
		if entry['template'] and not template:
			print "\t\tInvalid reference: Element[%d] -> Template[%d]" % (entry['id'], entry['template'])
			return
		entry.update(element=elem, site=site, profile=profile, template=template)
		entry = modifyDict(entry, rename={'custom_template': 'customTemplate'})
		return entry
	def adaptVmInterface(entry):
		entry = adaptElement(entry)
		if not entry:
			return
		elem = hostelements.get(entry['element'])
		if entry['element'] and not elem:
			print "\t\tInvalid reference: Element[%d] -> HostElement[%d]" % (entry['id'], entry['element'])
			return
		entry.update(element=elem)
		return entry
	print "\tExternal networks..."
	for key, entry in data.get('external_network', {}).items():
		entry = adaptElement(entry)
		network = networks.get(entry['network'])
		if entry['network'] and not network:
			print "\t\tInvalid reference: ExternalNetwork[%d] -> Network[%d]" % (entry['id'], entry['nertwork'])
		entry = modifyDict(entry, remove=['id', 'type', 'network'])
		obj = ExternalNetwork(network=network, **entry)
		obj.save()
		elements[key] = obj
	print "\tExternal network endpoints..."
	for key, entry in data.get('external_network_endpoint', {}).items():
		entry = adaptElement(entry)
		network = networkinstances.get(entry['network'])
		if entry['network'] and not network:
			print "\t\tInvalid reference: ExternalNetworkEndpoint[%d] -> NetworkInstance[%d]" % (entry['id'], entry['nertwork'])
		elem = hostelements.get(entry['element'])
		if entry['element'] and not elem:
			print "\t\tInvalid reference: ExternalNetworkEndpoint[%d] -> HostElement[%d]" % (entry['id'], entry['element'])
			return
		entry = modifyDict(entry, remove=['id', 'type', 'network', 'element'])
		obj = ExternalNetworkEndpoint(element=elem, network=network, **entry)
		obj.save()
		elements[key] = obj
		if elem:
			elem.topologyElement = obj
			elem.save()
	print "\tKVM QM elements..."
	for key, entry in data.get('kvmqm', {}).items():
		entry = adaptVmElement(entry)
		entry = modifyDict(entry, rename={'last_sync': 'lastSync', 'next_sync': 'nextSync',
			'rextfv_last_started': 'rextfvLastStarted'}, remove=['id', 'type'])
		obj = KVMQM(**entry)
		obj.save()
		elements[key] = obj
		if obj.element:
			obj.element.topologyElement = obj
			obj.element.save()
	print "\tKVM QM interfaces..."
	for key, entry in data.get('kvmqm_interface', {}).items():
		entry = adaptVmInterface(entry)
		entry = modifyDict(entry, remove=['id', 'type'])
		obj = KVMQM_Interface(**entry)
		obj.save()
		elements[key] = obj
		if obj.element:
			obj.element.topologyElement = obj
			obj.element.save()
	print "\tOpenVZ elements..."
	for key, entry in data.get('openvz', {}).items():
		entry = adaptVmElement(entry)
		entry = modifyDict(entry, rename={'last_sync': 'lastSync', 'next_sync': 'nextSync',
			'rextfv_last_started': 'rextfvLastStarted'}, remove=['id', 'type'])
		obj = OpenVZ(**entry)
		obj.save()
		elements[key] = obj
		if obj.element:
			obj.element.topologyElement = obj
			obj.element.save()
	print "\tOpenVZ interfaces..."
	for key, entry in data.get('openvz_interface', {}).items():
		entry = adaptVmInterface(entry)
		entry = modifyDict(entry, remove=['id', 'type'])
		entry = modifyDict(entry, rename={'use_dhcp': 'useDhcp'})
		obj = OpenVZ_Interface(**entry)
		obj.save()
		elements[key] = obj
		if obj.element:
			obj.element.topologyElement = obj
			obj.element.save()
	print "\tRepy elements..."
	for key, entry in data.get('repy', {}).items():
		entry = adaptVmElement(entry)
		entry = modifyDict(entry, remove=['id', 'type'])
		obj = Repy(**entry)
		obj.save()
		elements[key] = obj
		if obj.element:
			obj.element.topologyElement = obj
			obj.element.save()
	print "\tRepy interfaces..."
	for key, entry in data.get('repy_interface', {}).items():
		entry = adaptVmInterface(entry)
		entry = modifyDict(entry, remove=['id', 'type'])
		obj = Repy_Interface(**entry)
		obj.save()
		elements[key] = obj
		if obj.element:
			obj.element.topologyElement = obj
			obj.element.save()
	print "\tTinc VPNs..."
	for key, entry in data.get('tinc_vpn', {}).items():
		entry = adaptElement(entry)
		entry = modifyDict(entry, remove=['id', 'type'])
		obj = TincVPN(**entry)
		obj.save()
		elements[key] = obj
	print "\tTinc endpoints..."
	for key, entry in data.get('tinc_endpoint', {}).items():
		entry = adaptElement(entry)
		elem = hostelements.get(entry['element'])
		if entry['element'] and not elem:
			print "\t\tInvalid reference: TincEndpoint[%d] -> HostElement[%d]" % (entry['id'], entry['element'])
			return
		entry = modifyDict(entry, remove=['id', 'type', 'element'])
		obj = TincEndpoint(element=elem, **entry)
		obj.save()
		elements[key] = obj
		if elem:
			elem.topologyElement = obj
			elem.save()
	print "\tUDP endpoints..."
	for key, entry in data.get('udp_endpoint', {}).items():
		entry = adaptElement(entry)
		elem = hostelements.get(entry['element'])
		if entry['element'] and not elem:
			print "\t\tInvalid reference: UDPEndpoint[%d] -> HostElement[%d]" % (entry['id'], entry['element'])
			return
		entry = modifyDict(entry, remove=['id', 'type', 'element'])
		obj = UDPEndpoint(element=elem, **entry)
		obj.save()
		elements[key] = obj
		if elem:
			elem.topologyElement = obj
			elem.save()
	print "\tConnections..."
	Connection.objects.delete()
	connections = {}
	for key, entry in data['connection'].items():
		perms = permissions.get(entry['permissions'])
		if not perms:
			print "\t\tInvalid reference: Connection[%d] -> Permissions[%d]" % (key, entry['permissions'])
		totalUsage = usagestatistics.get(entry['totalUsage'])
		if not totalUsage:
			print "\t\tInvalid reference: Connection[%d] -> UsageStatistics[%d]" % (key, entry['totalUsage'])
		topology = topologies.get(entry['topology'])
		if not topology:
			print "\t\tInvalid reference: Connection[%d] -> Topology[%d]" % (key, entry['topology'])
		hcon1 = hostconnections.get(entry['connection1'])
		if entry['connection1'] and not hcon1:
			print "\t\tInvalid reference: Connection[%d] -> HostConnection[%d]" % (key, entry['connection1'])
		hcon2 = hostconnections.get(entry['connection2'])
		if entry['connection2'] and not hcon2:
			print "\t\tInvalid reference: Connection[%d] -> HostConnection[%d]" % (key, entry['connection2'])
		hel1 = hostelements.get(entry['connectionElement1'])
		if entry['connectionElement1'] and not hel1:
			print "\t\tInvalid reference: Connection[%d] -> HostElement[%d]" % (key, entry['connectionElement1'])
		hel2 = hostelements.get(entry['connectionElement2'])
		if entry['connectionElement2'] and not hel2:
			print "\t\tInvalid reference: Connection[%d] -> HostElement[%d]" % (key, entry['connectionElement2'])
		elems = sorted(elementConnections[entry['id']])
		if not len(elems) == 2:
			print "\t\tInvalid connection: Connection[%d] has %d elements" % (key, len(elems))
		entry = modifyDict(entry, remove=['id', 'topology', 'permissions', 'totalUsage'])
		obj = Connection(permissions=perms, totalUsage=totalUsage, topology=topology, connectionFrom=hcon1,
			connectionTo=hcon2, connectionElementFrom=hel1, connectionElementTo=hel2, **entry)
		obj.elementFrom = elements[elems[0]]
		obj.elementTo = elements[elems[1]]
		obj.save()
		connections[key] = obj
		obj.elementFrom.connection = obj
		obj.elementTo.connection = obj
		obj.elementFrom.save()
		obj.elementTo.save()
		if hel1:
			hel1.topologyConnection = obj
			hel1.save()
		if hel2:
			hel2.topologyConnection = obj
			hel2.save()
		if hcon1:
			hcon1.topologyConnection = obj
			hcon1.save()
		if hcon2:
			hcon2.topologyConnection = obj
			hcon2.save()
	#TODO: hostElement/connection link to topologyElement/connection
	print "done."

	
def setProfiling(enabled=True, slowms=100):
	import pymongo
	mongodb = pymongo.MongoClient()
	db = mongodb[DATABASE]
	if enabled:
		db.set_profiling_level(0)
		db.system.profile.drop()
	db.set_profiling_level(enabled, slowms)
	
def getProfiling():
	import pymongo
	mongodb = pymongo.MongoClient()
	db = mongodb[DATABASE]
	return list(db.system.profile.find())
	
if __name__ == "__main__":
	data = loadDumpData('dump.json')
	data = convertData(data)
	importData(data)
