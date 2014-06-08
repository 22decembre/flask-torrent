# -*- coding: utf-8 -*-
from flask import render_template, flash, redirect, session, url_for, request, g, json, jsonify
from flask.ext.login import login_user, logout_user, current_user, login_required
from werkzeug import secure_filename
from app   import app, db, lm
from config import basedir, ADMINS
from forms import IndexForm, TorrentFileDetails, TorrentForm, LoginForm, TorrentIndex, TorrentAdmin
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
tr_session.script_torrent_done_enabled=True
tr_session.script_torrent_done_filename = os.path.dirname(os.path.realpath(__file__)) + "/finish.py"
tr_session.update()
#tr_session.set_session(timeout=None,script_torrent_done_enabled = True,script_torrent_done_filename = os.path.dirname(os.path.realpath(__file__)) + "/finish.py")

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

@app.route('/login', methods=["GET", "POST"])
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
	if tordb.user==unicode(user):

		###
		if torrent.error == 1:
			torrent.error = 'tracker warning'
		if torrent.error == 2:
			torrent.error = 'tracker error'
		if torrent.error == 3:
			torrent.error = 'local error'
		
		control = TorrentForm(ratiomode=torrent.seedRatioMode,bandwidthpriority=torrent.bandwidthPriority)
		###
		for file_x in client.get_files(tor_id)[torrent.id]:
			# no csrf because this form is just a part of a bigger one which has already its own csrf !
			f_form = TorrentFileDetails()
			f_form.key = file_x
			f_form.filename	= unicode(client.get_files(tor_id)[torrent.id][file_x]['name'])
			f_form.priority  = client.get_files(tor_id)[torrent.id][file_x]['priority']
			f_form.size 	 = client.get_files(tor_id)[torrent.id][file_x]['size']
			f_form.completed = client.get_files(tor_id)[torrent.id][file_x]['completed']
			f_form.selected  = client.get_files(tor_id)[torrent.id][file_x]['selected']
			
			control.files.append_entry(f_form)
		
		if control.validate_on_submit():
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
			if int(control.bandwidthpriority.data) != int(torrent.bandwidthPriority):
				updatebandwidthpriority(tor_id,control.bandwidthpriority.data)
			
			# we use the ID returned by transmission itself ! Not the hashString.
			# the first torrent.id is to say which torrent we are talking about. Transmission gives us a dict containing the info for the torrents asked.
			# so the dict contains ONE torrent info
			# but still, begin with the torrent.id, this is why the second torrent.id
			#files_dict = client.get_files(torrent.id)[torrent.id]
			files_answers = {}
			
			for file_un in control.files:
				files_update = False
				# create a dict that contains the new priority for each file according to the form
				file_answer = client.get_files(tor_id)[torrent.id][int(file_un.key.data)]
				if file_un.priority.data != file_answer['priority']:
					update = True
					files_update = True
					file_answer['priority'] = file_un.priority.data
					
				if file_un.selected.data != file_answer['selected']:
					update = True
					files_update = True
					file_answer['selected'] = file_un.selected.data
				
				# append the dict to the general dict previously created (files_answers).
				# the key is the ID of the file itself ! >> no value name !
				if files_update:
					files_answers[int(file_un.key.data)] = file_answer
			
			#finally, we create the last dict which will contain only one value : the files_answers dict !
			answer = {}
			answer[int(torrent.id)] = files_answers
			client.set_files(answer)
			
			if update:
				torrent.update()
			return redirect(redirect_url())
		else:
			app.logger.info(control.errors)
		return render_template("torrent.html", title = torrent.name, user = user, torrent = torrent, control = control)
	
	else:
		return render_template("404.html")

def updatebandwidthpriority(tor_id,new_prio):
	user = g.user
	torrent = client.get_torrent(tor_id)
	
	if new_prio == '-1':
		torrent.priority = 'low'
	if new_prio == '1':
		torrent.priority = 'high'
	if new_prio == '0':
		torrent.priority = 'normal'
	torrent.update()
	app.logger.info("%s a modifié la priorité de %s à %s", user,torrent,torrent.priority)

@app.route('/start/<tor_id>', methods = ['GET','POST'])
@login_required
def start(tor_id):
	torrent = client.get_torrent(tor_id)
	torrent.start()
	app.logger.info("%s demarré par %s.",tor_id,g.user)
	return redirect(redirect_url())

@app.route('/stop/<tor_id>', methods = ['GET','POST'])
@login_required
def stop(tor_id):
	torrent = client.get_torrent(tor_id)
	torrent.stop()
	app.logger.info("%s arreté par %s.",tor_id,g.user)
	return redirect(redirect_url())

@app.route('/delete/<tor_id>', methods = ['GET','POST'])
@login_required
def delete(tor_id):
	torrent = client.remove_torrent(tor_id, delete_data=False)
	torrent_to_del = Torrent.query.filter_by(hashstring=tor_id).first()
	db.session.delete(torrent_to_del)
	db.session.commit()
	app.logger.info("%s arreté et effacé définitivement par %s.",tor_id,g.user)
	return redirect(redirect_url())

@app.route('/erase/<tor_id>', methods = ['GET','POST'])
@login_required
def erase(tor_id):
	torrent = client.remove_torrent(tor_id, delete_data=True)
	torrent_to_del = Torrent.query.filter_by(hashstring=tor_id).first()
	db.session.delete(torrent_to_del)
	db.session.commit()
	app.logger.info("%s arreté et effacé définitivement, y compris les données téléchargées, par %s.",tor_id,g.user)
	return redirect(redirect_url())

@app.route('/')
@app.route('/index', methods = ['GET', 'POST'])
@login_required
def index():
	user = g.user
	#print(tr_session.get_session)
	
	# recuperer les torrents de l'utilisateur et de lui uniquement !
	torrents_from_db = Torrent.query.filter_by(user = unicode(g.user)).all()
	# this listing will be used to fetch torrents, and after, to check the update of torrents
	listing =list()
	for x in torrents_from_db:
		listing.append(x.hashstring)
	
	# envoi d'un nouveau torrent
	form = IndexForm()
	torrents = client.get_torrents(listing)
	for torrent in torrents:
		torrent_x=TorrentIndex()
		torrent_x.bandwidthpriority=torrent.bandwidthPriority
		torrent_x.status = torrent.status
		torrent_x.torrentname = torrent.name
		torrent_x.progress = float(torrent.progress)
		torrent_x.tor_id = torrent.hashString
		form.torrents.append_entry(torrent_x)
	
	torrent_to_start = False
	if form.validate_on_submit():
		for torrent_un in form.torrents:
			x = client.get_torrent(unicode(torrent_un.tor_id.data))
			# if the torrent is in the listing...
			if torrent_un.bandwidthpriority.data != int(x.bandwidthPriority) and x.hashString in listing:
				app.logger.info('%s priorité intiale %s, finale %s.',x.name,x.bandwidthPriority,torrent_un.bandwidthpriority.data)
				# we update...
				updatebandwidthpriority(x.hashString,torrent_un.bandwidthpriority.data)
				# and we remove the id from the listing -> if we don't do so, torrents bandwidth priority is updated twice for some obscure reason
				# thus staying at the first priority instead of being really updated to the user wish.
				listing.remove(torrent_un.tor_id.data)
		
		if form.torrentseed_file.data.mimetype == 'application/x-bittorrent':
			filename = secure_filename(form.torrentseed_file.data.filename)
			form.torrentseed_file.data.save(os.path.join(basedir + '/tmp', filename))
			f = open(basedir + '/tmp/' + filename)
			torrent_to_start = base64.b64encode(f.read())
		else:
			if form.torrentseed_url.data != '':
				torrent_to_start = form.torrentseed_url.data
		if torrent_to_start:
			# ON ajoute le torrent à transmission
			new_tor = client.add_torrent(torrent_to_start)
			new_tor.start()
			
			app.logger.info('%s demarré et ajouté à la base de données par %s.',new_tor,user)
			
			# on ajoute le torrent à la base de données pour se souvenir à qui il appartient.
			torrent_to_add = Torrent(hashstring=new_tor.hashString,user=unicode(g.user))
			db.session.add(torrent_to_add)
			db.session.commit()
		#except tr.TransmissionError:
		#	app.logger.info(tr.TransmissionError)
		return redirect(redirect_url())
		
	return render_template("index.html", form = form, title = "Home", user = g.user)

@app.route('/admin', methods = ['GET', 'POST'])
@login_required
def admin():
	user = g.user
	if user.is_admin():
		torrents = client.get_torrents()
		torrents_forms = IndexForm()
		for torrent in torrents:
			form = TorrentIndex()
			form.tor_id = torrent.hashString
			form.torrentname = torrent.name
			form.status = torrent.status
			
			t = Torrent.query.filter_by(hashstring = torrent.hashString).first()
			if t!=None and t.user!=None:
				form.owner = t.user
			
			form.bandwidthpriority=torrent.bandwidthPriority
			torrents_forms.torrents.append_entry(form)

	return render_template("admin.html", title = "Admin", user = g.user, torrents = torrents, torrents_forms = torrents_forms)
