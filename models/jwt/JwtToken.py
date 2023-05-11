import os
from dataclasses import dataclass
from datetime import datetime

import jwt

AUTH_SECRET_KEY = os.environ.get("JWT_AUTH_SECRET")


@dataclass
class JwtToken:
    data: dict
    expired_at: datetime

    def encode(self):
        data = self.data
        data["expired_at"] = self.expired_at.timestamp()
        return jwt.encode(data, AUTH_SECRET_KEY, algorithm="HS256")

    def decode(token):
        payload = {}
        try:
            payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=["HS256"])
        except Exception as err:
            print(err)
            return ({}, False)
        if not payload["email"] or not payload["expired_at"]:
            return ({}, False)

        if datetime.utcnow() > datetime.fromtimestamp(payload["expired_at"]):
            return ({}, False)
        data = {}
        data["email"] = payload["email"]
        data["telegram"] = payload["telegram"]
        data["expired_at"] = payload["expired_at"]
        return (data, True)
