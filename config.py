# -*- coding: utf-8 -*-
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = 'BeishudFiwokshyocdum'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

LDAP_HOST='blackblock.22decembre.eu'
LDAP_PORT=''
LDAP_ID ='uid'
LDAP_BASE='ou=users,dc=22decembre,dc=eu'
LDAP_SSL=0

TRANSMISSION_HOST='192.168.87.2'
TRANSMISSION_PORT=9091
TRANSMISSION_PASS='transmission'
TRANSMISSION_USER='transmission'

DEST_DL='torrents'