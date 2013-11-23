# -*- coding: utf-8 -*-
from flask import render_template, request
from app   import app
from forms import TorrentSeedForm, TorrentFileDetails, Torrent
import transmissionrpc as tr
import sys

# need to be variabilized
client = tr.Client(address='localhost',port=9091)

def start_stop_torrent(tor_id):
	torrent = client.get_torrent(tor_id)
	if torrent.status == 'stopped':
		torrent.start()
	else:
		torrent.stop()

@app.route('/torrent/<tor_id>', methods = ['GET','POST'])
def torrent(tor_id):
	torrent = client.get_torrent(tor_id)
	###
	#error = ''
	if torrent.error == 1:
		torrent.error = 'tracker warning'
	if torrent.error == 2:
		torrent.error = 'tracker error'
	if torrent.error == 3:
		torrent.error = 'local error'
	###
	if torrent.seedRatioMode == 0:
		torrent.seedRatioMode = 'Global ratio limit'
	if torrent.seedRatioMode == 1:
		torrent.seedRatioMode = 'Individual ratio limit'
	if torrent.seedRatioMode == 2:
		torrent.seedRatioMode = 'Unlimited seeding'
	###
	files = list()
	for f in torrent.files():
		fx = dict()
		fx['name'] = torrent.files()[f]['name']
		if torrent.files()[f]['selected'] == True:
			fx['priority'] = torrent.files()[f]['priority']
		else:
			fx['priority'] = 0
		fx['size'] = torrent.files()[f]['size']
		fx['completed'] = torrent.files()[f]['completed']
		fx['form'] = TorrentFileDetails(priority=fx['priority'])
		files.append(fx)
	user = 'stephane'
	
	control = Torrent(bandwidthpriority=torrent.bandwidthPriority)
	if control.validate_on_submit():
		type(button.data)
		#start_stop_torrent(tor_id)
	return render_template("torrent.html", title = torrent.name, files = files, user = user, torrent = torrent, control = control)

@app.route('/')
@app.route('/index', methods = ['GET', 'POST'])
def index():
	user = 'stephane'
	
	torrents = client.get_torrents()
	
	# for each torrent, we include a form which will allow start or stop
	for torrent in torrents:
		torrent.control = Torrent()
		torrent.control.hidden.value = torrent.id
		
	if torrent.control.validate_on_submit():
		start_stop_torrent(request.form["torrent_id"])
	# envoi d'un nouveau torrent
	form = TorrentSeedForm()
	if form.validate_on_submit():
		#form.torrentfile_url.data
		client.add_torrent(form.torrentseed_url.data)
	
	return render_template("index.html", form = form, title = "Home", user = user, torrents = torrents)
