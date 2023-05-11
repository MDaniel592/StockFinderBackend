import logging
from datetime import datetime, timedelta
from http import HTTPStatus

import database.db_management.auth_management as auth
import models.auth.auth_data as auth_data
import models.jwt.JwtToken as Token
import models.password.password_data as password_data
import utils.error_messages as errors
import utils.valid_messages as valid_messages
from database.stockfinder_models.base import Session
from database.stockfinder_models.User import User
from flask import Blueprint, request
from sqlalchemy import and_
from utils.common import is_email_valid, is_password_valid
from utils.error_messages_management import generate_error_data
from utils.validate_inputs import valid_data_recv
from werkzeug.security import check_password_hash, generate_password_hash

# enabling logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

password_routing_blueprint = Blueprint("password_routing", __name__)


@password_routing_blueprint.route("/email_password_reset", methods=["POST"])
def email_password_reset():
    """
    Change the user password when users forgot the current one. The password can be changed one time each 24 hours

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "EmailPasswordReset")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    email_validation, is_email_validated = is_email_valid(user_data["email"])
    if not is_email_validated:
        return generate_error_data(email_validation, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    password_validation, is_password_validated = is_password_valid(user_data["password"])
    if not is_password_validated:
        return generate_error_data(password_validation, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    email_verification_error, is_email_verified = auth.verify_code(user_data["email_code"], user_data["email"])
    if not is_email_verified:
        return generate_error_data(email_verification_error, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    # RESET PASSWORD ONCE EACH 24 HOURS
    session = Session()
    user_found = session.query(User).filter(User.email == user_data["email"]).first()
    if not user_found:
        session.close()
        return (generate_error_data(errors.USER_NOT_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED)

    next_time = user_found.password_reseted_at + timedelta(hours=24)
    current_time = datetime.now().replace(microsecond=0)
    if current_time < next_time:
        return (generate_error_data(errors.PASSWORD_RESET_LIMIT, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED)
    # RESET PASSWORD ONCE EACH 24 HOURS

    user_found.password = generate_password_hash(user_data["password"])
    session.commit()
    session.close()

    valid_messages.password_reset_succeded(user_data["email"])
    data = {}
    data["status"] = "ok"
    data["ok"] = "Se ha actualizado la contraseña"
    return data, HTTPStatus.OK


@password_routing_blueprint.route("/password_reset", methods=["POST"])
def password_reset():
    """
    Set a new user password knowing the current password. The password can be changed one time each 24 hours

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "PasswordReset")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    password_validation, is_password_validated = is_password_valid(user_data["new_password"])
    if not is_password_validated:
        return generate_error_data(password_validation, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    # Validamos el token
    decoded_token, decode_result = Token.JwtToken.decode(user_data["token"])
    if not decode_result:
        return generate_error_data(errors.TOKEN_INVALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    email = decoded_token[auth_data.EMAIL]
    telegram_id = decoded_token[password_data.TELEGRAM_ID] if decoded_token[password_data.TELEGRAM_ID] else None

    # RESET PASSWORD ONCE EACH 24 HOURS
    session = Session()
    if telegram_id:
        logger.warning(telegram_id)
        user_db_data = session.query(User).filter(and_(User.email == email, User.telegram == int(telegram_id))).first()
    else:
        logger.warning(email)
        user_db_data = session.query(User).filter(User.email == email).first()

    if not user_db_data:
        session.close()
        return generate_error_data(errors.USER_NOT_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    last_reset = user_db_data.password_reseted_at if user_db_data.password_reseted_at else datetime.now() - timedelta(hours=48)
    next_time = last_reset + timedelta(hours=24)
    current_time = datetime.now().replace(microsecond=0)
    if current_time < next_time:
        session.close()
        return generate_error_data(errors.PASSWORD_RESET_LIMIT, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED
    # RESET PASSWORD ONCE EACH 24 HOURS

    # Comparo los hashes de las contraseñas, si no son iguales, salgo
    # Verificamos que la contraseña que el usuario ha introducido y la que está en la BD es la misma
    if not check_password_hash(user_db_data.password, user_data["current_password"]):
        session.close()
        return generate_error_data(errors.PASSWORD_ERROR, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    user_db_data.password = generate_password_hash(user_data["new_password"])
    user_db_data.password_reseted_at = datetime.now()
    session.commit()
    session.close()

    valid_messages.password_reset_succeded(email, telegram_id)
    data = {}
    data["status"] = "ok"
    data["ok"] = "Se ha actualizado la contraseña"
    return data, HTTPStatus.OK


@password_routing_blueprint.route("/verify-password-reset-code", methods=["POST"])
def verify_email_code():
    request_body = request.json
    data, status = valid_data_recv(request_body, "VerifyPasswordResetCode")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    email_verification_error, is_email_verified = auth.verify_code(user_data["email_code"], user_data["email"])
    if not is_email_verified:
        return generate_error_data(email_verification_error, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    valid_messages.correct_code(user_data["email"], user_data["email_code"])
    data = {}
    data["status"] = "ok"
    return data, HTTPStatus.OK
