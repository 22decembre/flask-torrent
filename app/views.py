# -*- coding: utf-8 -*-
from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from werkzeug import secure_filename
from app   import app, lm, basedir
from forms import TorrentSeedForm, TorrentFileDetails, Torrent, LoginForm
from models import User
import transmissionrpc as tr
import sys, os, base64

UPLOAD_FOLDER = '/tmp'

# need to be variabilized
client = tr.Client(address=app.config['TRANSMISSION_HOST'],
		   port=app.config['TRANSMISSION_PORT'],
		   user=app.config['TRANSMISSION_USER'],
		   password=app.config['TRANSMISSION_PASS'], http_handler=None, timeout=None)

def start_stop_torrent(tor_id):
	torrent = client.get_torrent(tor_id)
	if torrent.status == 'stopped':
		torrent.start()
	else:
		torrent.stop()

@app.before_request
def before_request():
	g.user = current_user

@lm.user_loader
def load_user(userid):
	return User(ident=userid)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
	if g.user is not None and g.user.is_authenticated():
		return redirect(url_for('index'))
	
	form = LoginForm()
	if request.method == 'POST' and form.validate():
		session['remember_me'] = form.remember_me.data
		user = User(ident=form.username.data, password=form.password.data)
		if user.is_active():
			login_user(user, remember = session['remember_me'])
		return redirect(url_for("index"))
	return render_template("login.html", form=form)

@app.route('/torrent/<tor_id>', methods = ['GET','POST'])
@login_required
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
	user = g.user
	
	control = Torrent(bandwidthpriority=torrent.bandwidthPriority)
	if control.validate_on_submit():
		type(button.data)
		#start_stop_torrent(tor_id)
	return render_template("torrent.html", title = torrent.name, files = files, user = user, torrent = torrent, control = control)

@app.route('/')
@app.route('/index', methods = ['GET', 'POST'])
@login_required
def index():
	user = g.user
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
		if form.torrentseed_file.data.mimetype == 'application/x-bittorrent':
			#torrent_to_start = form.torrentseed_file.data
			filename = secure_filename(form.torrentseed_file.data.filename)
			form.torrentseed_file.data.save(os.path.join(basedir + '/tmp', filename))
			f = open(basedir + '/tmp/' + filename)
			torrent_to_start = base64.b64encode(f.read())
		else:
			torrent_to_start = form.torrentseed_url.data
		#form.torrentfile_url.data
		client.add_torrent(torrent_to_start)
	
	return render_template("index.html", form = form, title = "Home", user = user, torrents = torrents)
