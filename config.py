# -*- coding: utf-8 -*-
import os
basedir = os.path.abspath(os.path.dirname(__file__))
LOG = os.path.join(basedir, 'torrent.log')

CSRF_ENABLED = True
SECRET_KEY = 'BeishudFiwokshyocdum'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

MAIL_SERVER = 'blackblock'
MAIL_PORT = 25
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_USERNAME = None
MAIL_PASSWORD = None

LDAP_HOST='blackblock.22decembre.eu'
LDAP_PORT=''
LDAP_ID ='uid'
LDAP_BASE='ou=users,dc=22decembre,dc=eu'
LDAP_SSL=0

TRANSMISSION_HOST='localhost'
TRANSMISSION_PORT=9091
TRANSMISSION_PASS='transmission'
TRANSMISSION_USER='transmission'

DEST_DL='torrents'
ADMINS = ['stephane']

