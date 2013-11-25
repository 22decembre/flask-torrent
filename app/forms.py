# -*- coding: utf-8 -*-

from flask.ext.wtf import Form
from wtforms.fields.html5 import DecimalField
from wtforms import TextField, BooleanField, FileField, SelectField, HiddenField, PasswordField
from wtforms.validators import Required

class LoginForm(Form):
    username = TextField("username")
    password = PasswordField("password", validators = [Required()])
    remember_me = BooleanField('remember_me', default = False)

class Torrent(Form):
	hidden = HiddenField('hidden')
	ratiolimit 	= DecimalField("ratio")
	downloadlimit 	= DecimalField("down")
	uploadlimit 	= DecimalField("up")
	bandwidthpriority = SelectField(u'Torrent priority', choices=[( -1,'low'),(0,'normal'),(1,'high')])

class TorrentFileDetails(Form):
	#selected = BooleanField('selected')
	priority = SelectField(u'File priority',choices=[('off','off'),('low','low'),('normal','normal'),('high','high')])

class TorrentSeedForm(Form):
    torrentseed_url = TextField('torrentseed_url', validators = [Required()])