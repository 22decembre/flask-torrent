# -*- coding: utf-8 -*-
from flask import render_template, flash, redirect, session, url_for, request, g, json
from flask.ext.login import login_user, logout_user, current_user, login_required
from werkzeug import secure_filename
from app   import app, db, lm
from config import basedir
from forms import TorrentSeedForm, TorrentFileDetails, TorrentForm, LoginForm
from models import User, Torrent
import transmissionrpc as tr
import sys, os, base64

# need to be variabilized
client = tr.Client(address=app.config['TRANSMISSION_HOST'],
		port=app.config['TRANSMISSION_PORT'],
		user=app.config['TRANSMISSION_USER'],
		password=app.config['TRANSMISSION_PASS'], http_handler=None, timeout=None)
# tr_session car il y a déjà un session quelque part : la session web avec auth et mots de passe (entre autre)
tr_session = tr.Session(client)
tr_session.script_torrent_done_enabled = True
tr_session.script_torrent_done_filename = "finish.py"

def redirect_url():
    return request.referrer or url_for('index')

# forbidden -> used when user try to go to a torrent he doesn't own
@app.errorhandler(403)
def internal_error(error):
    return render_template('403.html'), 403

# page / torrent doesn'y exist
@app.errorhandler(404)
def internal_error(error):
    return render_template('404.html'), 404

# page / torrent doesn'y exist anymore ! (but used too ...)
@app.errorhandler(410)
def internal_error(error):
    return render_template('410.html'), 410

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


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
			try:
				os.stat(user.dl_dir)
			except:
				os.mkdir(user.dl_dir)
		return redirect(url_for("index"))
	return render_template("login.html", form=form)

@app.route('/torrent/<tor_id>', methods = ['GET','POST'])
@login_required
def torrent(tor_id):
	user = g.user
	
	# fetch informations about the torrent from transmission
	torrent = client.get_torrent(tor_id)
	
	# fetch information about the torrent from DB
	tordb = Torrent.query.filter_by(hashstring = torrent.hashString).first()
	if tordb.user != unicode(user):
		return render_template("404.html")
	else:
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
			
		control = TorrentForm(bandwidthpriority=torrent.bandwidthPriority)
		###
		for f in torrent.files():
			if torrent.files()[f]['selected'] == True:
				priority = torrent.files()[f]['priority']
			else:
				priority = 0
			f_form = TorrentFileDetails(csrf_enabled=False)
			f_form.filename	= unicode(torrent.files()[f]['name'])
			f_form.priority = priority
			f_form.size 	= torrent.files()[f]['size']
			f_form.completed = torrent.files()[f]['completed']
			
			control.files.append_entry(f_form)
		
		# the form is not validated because of the csrf trick !
		if control.is_submitted():
			update = False
			if control.ratiolimit.data != torrent.seedRatioLimit:
				torrent.seed_ratio_limit = float(control.ratiolimit.data)
				torrent.seed_ratio_mode = 'single'
				update = True
			if control.downloadlimit.data != torrent.downloadLimit:
				torrent.download_limit = int(control.downloadlimit.data)
				update = True
			if control.uploadlimit.data != torrent.uploadLimit:
				torrent.upload_limit = int(control.uploadlimit.data)
				update = True
			if control.bandwidthpriority.data != torrent.bandwidthPriority:
				if control.bandwidthpriority.data == '-1':
					print('low')
					torrent.priority = 'low'
				if control.bandwidthpriority.data == '1':
					print('high')
					torrent.priority = 'high'
				if control.bandwidthpriority.data == '0':
					print('normal')
					torrent.priority = 'normal'
				update = True
			#for x in control.files:
			#	prio = x.priority.data
			#	file_id = x.filename.data
				
			if update:
				torrent.update()
			#start_stop_torrent(tor_id)
		return render_template("torrent.html", title = torrent.name, user = user, torrent = torrent, control = control)

@app.route('/start/<tor_id>', methods = ['GET','POST'])
@login_required
def torrent_start(tor_id):
	torrent = client.get_torrent(tor_id)
	torrent.start()
	return redirect(redirect_url())

@app.route('/stop/<tor_id>', methods = ['GET','POST'])
@login_required
def torrent_stop(tor_id):
	torrent = client.get_torrent(tor_id)
	torrent.stop()
	return redirect(redirect_url())

@app.route('/del/<tor_id>', methods = ['GET','POST'])
@login_required
def torrent_del(tor_id):
	torrent = client.remove_torrent(tor_id, delete_data=False)
	torrent_to_del = Torrent.query.filter_by(hashstring=tor_id).first()
	db.session.delete(torrent_to_del)
	db.session.commit()
	return redirect(redirect_url())

@app.route('/del_tot/<tor_id>', methods = ['GET','POST'])
@login_required
def torrent_del(tor_id):
	torrent = client.remove_torrent(tor_id, delete_data=True)
	torrent_to_del = Torrent.query.filter_by(hashstring=tor_id).first()
	db.session.delete(torrent_to_del)
	db.session.commit()
	return redirect(redirect_url())

@app.route('/')
@app.route('/index', methods = ['GET', 'POST'])
@login_required
def index():
	#user = g.user
	# recuperer les torrents de l'utilisateur et de lui uniquement !
	#torrents_from_db = Torrent.query.filter_by(user = unicode(g.user)).all()
	
	torrents = client.get_torrents()
	
	# for each torrent, we include a form which will allow start or stop
	# for torrent_to_control in torrents:
	#	torrent_to_control.control_form = TorrentForm()
	#	torrent_to_control.control_form.hidden.value = torrent_to_control.id
		#if torrent_to_control.control_form.validate_on_submit():
			#start_stop_torrent(request.form["torrent_id"])
	
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
		try:
			# ON ajoute le torrent à transmission
			new_tor = client.add_torrent(torrent_to_start)
			new_tor.downloadDir = g.user.dl_dir
			print(g.user.dl_dir)
			new_tor.update()
			
			# on ajoute le torrent à la base de données pour se souvenir à qui il appartient.
			torrent_to_add = Torrent(hashstring=new_tor.hashString,user=unicode(g.user))
			print(new_tor.downloadDir)
			db.session.add(torrent_to_add)
			db.session.commit()
		except tr.TransmissionError:
			print(message)
		
	return render_template("index.html", form = form, title = "Home", user = g.user, torrents = torrents)
