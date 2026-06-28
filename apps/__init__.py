import os
import sqlite3

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
from sqlalchemy import event
from sqlalchemy.engine import Engine


db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    # Gor SQLite robust under samtidiga anvandare:
    #  WAL          -> manga lasare + en skrivare samtidigt utan att blockera
    #  busy_timeout -> en skrivning vantar (5s) istallet for att fela direkt
    #  synchronous  -> NORMAL ger bra prestanda med WAL utan dataforlust-risk
    #  foreign_keys -> havdar relationen conversation<->message
    if isinstance(dbapi_connection, sqlite3.Connection):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def register_extensions(app):
    db.init_app(app)

apps = ('pages', 'chat',)

def register_blueprints(app):
    for module_name in apps:
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def configure_database(app):

    # Skapa tabeller EN gang vid uppstart istallet for pa varje request.
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print('> Error: DBMS Exception: ' + str(e))
            # fallback to SQLite
            basedir = os.path.abspath(os.path.dirname(__file__))
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')
            print('> Fallback to SQLite ')
            db.create_all()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    return app
