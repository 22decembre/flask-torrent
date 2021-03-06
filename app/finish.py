#!/usr/bin/python
# -*- coding: utf-8 -*-
# script pour quand le torrent est fini.

from flask.ext.mail import Mail
from app import app, db, lm, client
from config import basedir
from models import User, Torrent
import transmissionrpc as tr
import sys, os, base64

mail = Mail(app)

torrent_fini = client.get_torrent(TR_TORRENT_HASH)
query = Torrent.query.filter_by(hashString = unicode(torrent_fini)).all()
user = User(ident=query.user)

msg = Message('torrent fini', sender = 'torrents@22decembre.eu', recipients = user.mail)
msg.body = torrent_fini.name
#msg.html = '<b>HTML</b> body'
#with app.app_context():
mail.send(msg)

app.logger.info('%(torrent_fini)% de %(user)% terminé.')
# mail
# déplacer les fichiers dans le dossier de l'utilisateur