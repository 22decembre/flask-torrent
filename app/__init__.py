# -*- coding: utf-8 -*-

from flask import Flask
from flask.ext.login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
import os
from flask.ext.sqlalchemy import SQLAlchemy





app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

from app import views

from moment import momentjs
app.jinja_env.globals['momentjs'] = momentjs

import logging
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler('tmp/microblog.log', 'a', 1 * 1024 * 1024, 10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.setLevel(logging.INFO)
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.info('microblog startup')