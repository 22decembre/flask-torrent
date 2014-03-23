# -*- coding: utf-8 -*-

from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField, file_allowed
from wtforms.fields.html5 import DecimalField
from wtforms import TextField, BooleanField, SelectField, HiddenField, PasswordField, FormField, FieldList, StringField
from wtforms.validators import Required

class LoginForm(Form):
    username = TextField("username")
    password = PasswordField("password", validators = [Required()])
    remember_me = BooleanField('remember_me', default = False)

# each individual file in the torrent have its own priority, thus, we need to manage them individually !
class TorrentFileDetails(Form):
	key	 = HiddenField('key')
	filename = HiddenField('filename')
	size	 = HiddenField('size')
	completed = HiddenField('completed')
	selected = BooleanField('selected')
	priority = SelectField(u'File priority',choices=[('low','low'),('normal','normal'),('high','high')])
	
	# we desactivate the csrf cause this particular form is within the TorretForm, so it can't be several csrf at the same time !
	def __init__(self, *args, **kwargs):
		kwargs['csrf_enabled'] = False
		super(TorrentFileDetails, self).__init__(*args, **kwargs)

class TorrentForm(Form):
	csrf 		= HiddenField('hidden')
	ratiolimit 	= DecimalField("ratio")
	ratiomode	= SelectField(u'Ratio mode', choices=[('0','Global ratio limit'),('1','Individual ratio limit'),('2','Unlimited seeding')])
	downloadlimit 	= DecimalField("down")
	uploadlimit 	= DecimalField("up")
	bandwidthpriority = SelectField(u'Torrent priority', choices=[( '-1','low'),('0','normal'),('1','high')])
	
	# we append each individual file form to this, as we don't know how many there is in each torrent !
	files 		= FieldList(FormField(TorrentFileDetails))

class TorrentSeedForm(Form):
    torrentseed_url = TextField('torrentseed_url')
    torrentseed_file = FileField('torrentseed_file')

class TorrentBandwidth(Form):
	tor_id = HiddenField('tor_id')
	bandwidthpriority = SelectField(u'Torrent priority', choices=[( '-1','low'),('0','normal'),('1','high')])
	#bandwidthpriority = SelectField(u'Torrent priority', choices=[( 'low','low'),('normal','normal'),('high','high')])
	def __init__(self, *args, **kwargs):
		kwargs['csrf_enabled'] = False
		super(TorrentBandwidth, self).__init__(*args, **kwargs)
		
class Torrents(Form):
	#b_priority = SelectField(u'Torrent priority', choices=[( '-1','low'),('0','normal'),('1','high')])
	torrents = FieldList(FormField(TorrentBandwidth))