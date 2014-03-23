# -*- coding: utf-8 -*-

from app 	import app, db
from flask.ext.login import login_user, UserMixin
import ldap

class Torrent(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	user = db.Column(db.String(64), index = True)
	hashstring = db.Column(db.String(200), index = True, unique = True)

class User(UserMixin):
	# ident can be : stephane (name), or stephane@22...(mail) or...
	# the attribute correspond to the variable LDAP_ID
	def __init__(self, ident=None, password=None):
			
		# intialisation
		self.active = False
		self.admin = False
		
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
		self.dl_dir = self.home + '/torrents/'
		
		if result[0][1].has_key('mail') and result[0][1]['mail'] is not None:
			self.mail = result[0][1]['mail'][0]
		else:
			self.mail = self.name
			
		for i in app.config['ADMINS']:
			if self.name == i:
				self.admin = 1
	
	def is_active(self):
		return self.active
	
	def is_admin(self):
		return self.admin
	
	def is_authenticated(self):
		return self.active

	def get_id(self):
		return self.name

	def __repr__(self):
		return self.name