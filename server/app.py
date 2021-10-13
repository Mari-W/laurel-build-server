import os
from datetime import timedelta

from flask import Flask
from werkzeug.security import gen_salt

from server.database import database
from server.error_handling import error_handling
from server.oauth import init_oauth
from server.routing.api import api_bp
from server.routing.auth import auth_bp
from server.routing.builds import builds_bp
from server.routing.home import home_bp


def create_app():
    # init server
    app = Flask(__name__, template_folder="../templates")
    app.config.update(os.environ)

    # some dynamic settings
    app.config["SECRET_KEY"] = gen_salt(32)
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=100)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # init database
    @app.before_first_request
    def create_tables():
        database.alchemy.create_all()

    database.alchemy.init_app(app)

    # add routers
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(builds_bp, url_prefix='/builds')
    app.register_blueprint(api_bp, url_prefix='/api')

    # setup error handling
    error_handling(app)

    # init oauth client
    init_oauth(app)

    return app
