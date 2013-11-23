# -*- coding: utf-8 -*-

from flask import Flask

app = Flask(__name__)
app.config.from_object('config')

from app import views, filesize

from moment import momentjs
app.jinja_env.globals['momentjs'] = momentjs
app.jinja_env.filters['filesize'] = filesize.do_filesize