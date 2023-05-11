import logging
from datetime import datetime, timedelta
from http import HTTPStatus

import models.auth.auth_data as auth_data
import models.jwt.JwtToken as Token
import utils.error_messages as errors
import utils.valid_messages as valid_messages
from database.stockfinder_models.base import Session
from database.stockfinder_models.User import User
from flask import Blueprint, request
from utils.common import is_email_valid
from utils.error_messages_management import generate_error_data
from utils.validate_inputs import valid_data_recv
from werkzeug.security import check_password_hash

# enabling logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

auth_routing_blueprint = Blueprint("auth_routing", __name__)


@auth_routing_blueprint.route("/login", methods=["POST"])
def login():
    """
    Check if the credentials received are valid (generate a JWT)

    :return: a dict containing a JWT
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "UserLogin")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    # Validamos el email
    email_validation, is_email_validated = is_email_valid(user_data["email"])
    if not is_email_validated:
        return email_validation, HTTPStatus.UNAUTHORIZED

    # Me traigo los datos del usuario de la BD, en el caso de que no hayan coincidencias, en bd_user vendrá el error.
    data = {}
    session = Session()
    user_found = session.query(User).filter(User._email == user_data["email"]).first()
    if not user_found:
        session.close()
        data["user_data"] = ""
        data["is_user_valid"] = False
        data["error"] = errors.LOGIN_ERROR
        return generate_error_data(errors.USER_NOT_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    data["user_data"] = {"telegram": user_found.telegram, "email": user_found.email, "pass": user_found.password, "role": user_found.role.name}
    data["is_user_valid"] = True
    session.close()

    user_validation = data
    if not user_validation["is_user_valid"]:
        return generate_error_data(user_validation["error"], user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    # Comparo los hashes de las contraseñas, si no son iguales, salgo
    # Verificamos que la contraseña que el usuario ha introducido y la que está en la BD es la misma
    if not check_password_hash(user_validation["user_data"]["pass"], user_data["password"]):
        return generate_error_data(errors.LOGIN_ERROR, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    session = Session()
    user_found = session.query(User).filter(User.email == user_data["email"]).first()
    user_found.last_login_at = datetime.now()
    session.commit()
    session.close()

    # Genero el JWT y lo paso al cliente.
    jwt_data = {}
    jwt_data["email"] = user_data["email"]
    jwt_data["role"] = user_validation["user_data"]["role"]
    jwt_data["telegram"] = user_validation["user_data"]["telegram"]
    token = Token.JwtToken(jwt_data, datetime.utcnow() + timedelta(days=7))
    data = {}
    data["token"] = token.encode()

    valid_messages.valid_login(user_data["email"])
    return data, HTTPStatus.OK


@auth_routing_blueprint.route("/validate", methods=["POST"])
def validate_token():
    """
    Returns a dict with a valid key which can be true or false
    in case the token received is valid

    :return: a dict
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "Validate")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    # Validamos el token
    try:
        decoded_token, decode_result = Token.JwtToken.decode(user_data["token"])
        if not decode_result:
            return {"valid": False}, HTTPStatus.UNAUTHORIZED
    except:
        return {"valid": False}, HTTPStatus.UNAUTHORIZED

    email = decoded_token[auth_data.EMAIL]
    session = Session()
    email_found = session.query(User.email).filter(User.email == email).first()
    session.close()

    valid_messages.petition_completed("validate")
    if not email_found:
        return {"valid": False}, HTTPStatus.UNAUTHORIZED

    return {"valid": True}, HTTPStatus.OK
