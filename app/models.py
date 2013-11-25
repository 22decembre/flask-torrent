# -*- coding: utf-8 -*-

from app import app
from flask.ext.login import login_user, UserMixin
import ldap

class User(UserMixin):
	# ident can be : stephane (name), or stephane@22...(mail) or...
	# the attribute correspond to the variable LDAP_ID
	def __init__(self, ident=None, password=None):
			
		# intialisation
		self.active = False
		#self.password=password
		
		# ldap_id : uid=stephane
		self.ldap_id = app.config['LDAP_ID']+'='+ ident
		
		# dn = ldid + basedn : uid=stephane,ou=users,dc=22...
		self.dn = self.ldap_id + ',' + app.config['LDAP_BASE']
		
		ldapuri = 'ldap://' + app.config['LDAP_HOST']
		try:
			l = ldap.initialize(ldapuri)
		except ldap.LDAPError, e:
			print e.message['info']
			if type(e.message) == dict and e.message.has_key('desc'):
				print e.message['desc']
			else:
				print e
			sys.exit()
			
			self.active = False
		if password is not None:
			l.bind_s(self.dn, password)
		
		result = l.search_s(self.dn,ldap.SCOPE_BASE)
		self.active = True
		self.name = result[0][1]['uid'][0]
		self.home = result[0][1]['homeDirectory'][0]
		if result[0][1]['mail'] is not None:
			self.mail = result[0][1]['mail'][0]
		else:
			self.mail = self.name
	
	def is_active(self):
		return self.active
	
	def is_authenticated(self):
		return self.active

	def get_id(self):
		return self.name

	def __repr__(self):
		return self.name