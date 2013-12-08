# -*- coding: utf-8 -*-
from flask import render_template, flash, redirect, session, url_for, request, g, json
from flask.ext.login import login_user, logout_user, current_user, login_required
from werkzeug import secure_filename
from app   import app, db, lm
from config import basedir
from forms import TorrentSeedForm, TorrentFileDetails, TorrentForm, LoginForm
from models import User, Torrent
import transmissionrpc as tr
import sys, os, base64, magic

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
		#if torrent.seedRatioMode == 0:
		#	torrent.seedRatioMode = 'Global ratio limit'
		#if torrent.seedRatioMode == 1:
		#	torrent.seedRatioMode = 'Individual ratio limit'
		#if torrent.seedRatioMode == 2:
		#	torrent.seedRatioMode = 'Unlimited seeding'
		control = TorrentForm(ratiomode=torrent.seedRatioMode,bandwidthpriority=torrent.bandwidthPriority)
		###
		for file_x in client.get_files(tor_id)[torrent.id]:
			f_form = TorrentFileDetails(csrf_enabled=False)
			f_form.key = file_x
			f_form.filename	= unicode(client.get_files(tor_id)[torrent.id][file_x]['name'])
			f_form.priority  = client.get_files(tor_id)[torrent.id][file_x]['priority']
			f_form.size 	 = client.get_files(tor_id)[torrent.id][file_x]['size']
			f_form.completed = client.get_files(tor_id)[torrent.id][file_x]['completed']
			f_form.selected.default  = client.get_files(tor_id)[torrent.id][file_x]['selected']
			
			control.files.append_entry(f_form)
		
		# the form is not validated because of the csrf trick !
		if control.validate_on_submit():
			print('valide')
			update = False
			# by default, ratio limit can be updated !
			update_ratio_limit = True
			if control.ratiomode.data != torrent.seedRatioMode:
				
				if control.ratiomode.data == '0':
					torrent.seed_ratio_mode = 'global'
					# we don't allow anymore the ratio limit to be updated : the ratiolimit will be the gloabal one !
					update_ratio_limit = False
				if control.ratiomode.data == '1':
					torrent.seed_ratio_mode = 'single'
				if control.ratiomode.data == '2':
					torrent.seed_ratio_mode = 'unlimited'
					# we don't allow anymore the ratio limit to be updated : the ratiolimit will be the gloabal one !
					update_ratio_limit = False
				update = True
			# if we are still allowed to update ratio limit
			# eg : we haven't touched ratiomode in form - update_ratio_limit is still at its default : true
			# or it has been changed to single mode
			if update_ratio_limit:
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
					torrent.priority = 'low'
				if control.bandwidthpriority.data == '1':
					torrent.priority = 'high'
				if control.bandwidthpriority.data == '0':
					torrent.priority = 'normal'
				update = True
			
			# we use the ID returned by transmission itself ! Not the hashString.
			# the first torrent.id is to say which torrent we are talking about. Transmission gives us a dict containing the info for the torrents asked.
			# so the dict contains ONE torrent info
			# but still, begin with the torrent.id, this is why the second torrent.id
			#files_dict = client.get_files(torrent.id)[torrent.id]
			files_answers = {}
			for file_un in control.files:
				# create a dict that contains the new priority for each file according to the form
				file_answer = {}
				if file_un.priority.data != client.get_files(tor_id)[torrent.id][int(file_un.key.data)]['priority']:
					file_answer['priority'] = file_un.priority.data
				
				if file_un.selected.data != client.get_files(tor_id)[torrent.id][int(file_un.key.data)]['selected']:
					file_answer['selected'] = file_un.selected.data
				
				# append the dict to the general dict previously created (files_answers).
				# the key is the ID of the file itself ! >> no value name !
				files_answers[int(file_un.key.data)] = file_answer
			
			#finally, we create the last dict which will contain only one value : the files_answers dict !
			answer = {}
			answer[int(torrent.id)] = files_answers
			update = True
			client.set_files(answer)
			
			if update:
				torrent.update()
			#start_stop_torrent(tor_id)
		else:
			print(control.errors)
			print(control.ratiomode.data)
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
	torrents_from_db = Torrent.query.filter_by(user = unicode(g.user)).all()
	listing =list()
	for x in torrents_from_db:
		listing.append(x.hashstring)
	torrents = client.get_torrents(listing)
	
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
			db.session.add(torrent_to_add)
			db.session.commit()
		except tr.TransmissionError:
			print(message)
		
	return render_template("index.html", form = form, title = "Home", user = g.user, torrents = torrents)
