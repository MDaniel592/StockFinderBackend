import os

import flask
from utils.custom_hcaptcha import hCaptcha

app = flask.Flask(__name__)


if os.environ.get("FLASK_DEBUG") == 1:
    # Test
    app.config["HCAPTCHA_SITE_KEY"] = "10000000-ffff-ffff-ffff-000000000001"
    app.config["HCAPTCHA_SECRET_KEY"] = "0x0000000000000000000000000000000000000000"
else:
    # Production
    app.config["HCAPTCHA_SITE_KEY"] = os.environ.get("HCAPTCHA_SITE_KEY")
    app.config["HCAPTCHA_SECRET_KEY"] = os.environ.get("HCAPTCHA_SECRET_KEY")

app.config["HCAPTCHA_ENABLED"] = True
hcaptcha = hCaptcha()
hcaptcha.init_app(app)
