# -*- coding: utf-8 -*-

from flask import Flask
from flask.ext.login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user

app = Flask(__name__)
app.config.from_object('config')

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

from app import views, filesize

from moment import momentjs
app.jinja_env.globals['momentjs'] = momentjs
app.jinja_env.filters['filesize'] = filesize.do_filesize