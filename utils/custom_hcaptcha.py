import requests


class BlueprintCompatibility(object):
    site_key = None
    secret_key = None

class DEFAULTS(object):
    IS_ENABLED = True

class hCaptcha(object):

    VERIFY_URL = "https://hcaptcha.com/siteverify"
    site_key = None
    secret_key = None
    is_enabled = False

    def __init__(self, app=None, site_key=None, secret_key=None, is_enabled=True, **kwargs):
        if site_key:
            BlueprintCompatibility.site_key = site_key
            BlueprintCompatibility.secret_key = secret_key
            self.is_enabled = is_enabled

        elif app:
            self.init_app(app=app)

    def init_app(self, app=None):
        self.__init__(site_key=app.config.get("HCAPTCHA_SITE_KEY"),
                      secret_key=app.config.get("HCAPTCHA_SECRET_KEY"),
                      is_enabled=app.config.get("HCAPTCHA_ENABLED", DEFAULTS.IS_ENABLED))


    def verify(self, response=None, remote_ip=None):
        if self.is_enabled:
            data = {
                "secret": BlueprintCompatibility.secret_key,
                "response": response ,
                "remoteip": remote_ip ,
            }

            r = requests.post(self.VERIFY_URL, data=data)
            return r.json()["success"] if r.status_code == 200 else False
        return True
