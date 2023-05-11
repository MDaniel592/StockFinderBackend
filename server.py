import os

import flask
from flask_cors import CORS

from routing.apistock_routing import apistock_routing_blueprint
from routing.auth_routing import auth_routing_blueprint
from routing.builds_routing import build_routing_blueprint
from routing.password_routing import password_routing_blueprint
from routing.product_routing import product_routing_blueprint
from routing.profile_routing import profile_routing_blueprint
from routing.register_routing import register_routing_blueprint
from routing.telegram_routing import telegram_routing_blueprint
from routing.user_routing import user_routing_blueprint

SECRET_KEY = os.environ.get("FLASK_AUTH_SECRET")


app = flask.Flask(__name__)
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = SECRET_KEY
CORS(app)

spams = {}


app.register_blueprint(auth_routing_blueprint, url_prefix="/api")
app.register_blueprint(password_routing_blueprint, url_prefix="/api")
app.register_blueprint(profile_routing_blueprint, url_prefix="/api")
app.register_blueprint(register_routing_blueprint, url_prefix="/api")
app.register_blueprint(user_routing_blueprint, url_prefix="/api")
#
app.register_blueprint(build_routing_blueprint, url_prefix="/api")
#
app.register_blueprint(apistock_routing_blueprint, url_prefix="/")
app.register_blueprint(product_routing_blueprint, url_prefix="/")
app.register_blueprint(telegram_routing_blueprint, url_prefix="/")


if __name__ == "__main__":
    app.run(debug=True)
