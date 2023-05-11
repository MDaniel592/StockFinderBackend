import logging
import re
from http import HTTPStatus

import database.db_management.auth_management as auth
import models.register.register_data as register_data
import utils.error_messages as errors
import utils.valid_messages as valid_messages
from database.stockfinder_models.base import Session
from database.stockfinder_models.User import User
from flask import Blueprint, request
from routing.mail import mail
from routing.telegram_bot import bot_code
from utils.common import is_email_valid, is_password_valid
from utils.error_messages_management import generate_error_data
from utils.validate_inputs import valid_data_recv
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

register_routing_blueprint = Blueprint("register_routing", __name__)


# EMAIL SIERMPRE EN MINUSCULAS EN EL REGISTRO -> MUY CRÍTICO, LOS PROVEEDORES DE CORREOS NO SON CASE SENSITIVE
@register_routing_blueprint.route("/user-info", methods=["POST"])
def check_user_info():
    """
    Check if the telegram_id is already linked to an existing user (email is mandatory) on the database
    The emails providers are not case sensitive

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "UserInfo")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    email_validation, is_email_validated = is_email_valid(user_data["email"])
    if not is_email_validated:
        return generate_error_data(email_validation, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    password_validation, is_password_validated = is_password_valid(user_data["password"])
    if not is_password_validated:
        return generate_error_data(password_validation, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    session = Session()
    user_found = session.query(User).filter(User.email == user_data["email"]).first()
    if user_found:
        session.close()
        return generate_error_data(errors.USER_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    data = {}
    data["status"] = "ok"
    valid_messages.petition_completed("user-info")
    return data, HTTPStatus.OK


@register_routing_blueprint.route("/telegram-id", methods=["POST"])
def check_telegram_id():
    """
    Check if the telegram_id is already registered with an existing email on the database

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "TelegramID")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    session = Session()
    user_found = session.query(User).filter(User.telegram == user_data["telegram_id"]).first()
    if user_found:
        if user_found.__dict__.get("email", False):
            session.close()
            return generate_error_data(errors.USER_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    session.close()
    data = {}
    data["status"] = "ok"
    return data, HTTPStatus.OK


@register_routing_blueprint.route("generate-code", methods=["POST"])
def generate_code():
    """
    Generate a new code which will be sent via telegram or email

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "GenerateCode")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    if user_data["param_name"] == "email":
        try:
            email = str(user_data["param_value"]).lower()
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        session = Session()
        user_found = session.query(User).filter(User.email == email).first()
        if user_found:
            session.close()
            return generate_error_data(errors.USER_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        valid_messages.seding_code(email=email)
        try:
            auth.set_verification_code(mail.send_code(email), email)
        except:
            logger.error(f"No se le ha podido generar el código al correo {email}")
            return generate_error_data(errors.EMAIL_CODE_ERROR, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    elif user_data["param_name"] == "telegram":
        telegram_id = user_data["param_value"]

        if re.match(r"^-[0-9]*$", telegram_id):
            return generate_error_data(errors.TELEGRAM_ID_NOT_VALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        session = Session()

        user_found = session.query(User).filter(User.telegram == int(telegram_id)).first()
        if user_found:
            if user_found.__dict__.get("email", False):
                session.close()
                return generate_error_data(errors.USER_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        session.close()
        valid_messages.seding_code(telegram_id=telegram_id)
        try:
            auth.set_verification_code(bot_code.send_code(telegram_id), telegram_id)
        except:
            logger.error(f"No se le ha podido generar el código al usuario de Telegram con ID {telegram_id}")
            return generate_error_data(errors.TELEGRAM_CODE_ERROR, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED
    else:
        return generate_error_data(errors.USER_IP_NOT_PRESENT, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    data = {}
    data["status"] = "ok"
    valid_messages.petition_completed("generate-code")
    return data, HTTPStatus.OK


@register_routing_blueprint.route("/verify-register-codes", methods=["POST"])
def verify_codes():
    """
    Receive the email and telegram code sent by the user which must be verified
    If the codes are valid, then a new user is created

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "VerifyRegisterCodes")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    password_validation, is_password_validated = is_password_valid(user_data["password"])
    if not is_password_validated:
        return generate_error_data(password_validation, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    ## REGISTRO SIN TELEGRAM
    if not register_data.TELEGRAM_ID in request_body or request_body[register_data.TELEGRAM_ID] == "":
        session = Session()
        user_found = session.query(User).filter(User.email == user_data["email"]).first()
        session.close()
        if user_found:
            return generate_error_data(errors.USER_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        email_verification_error, is_email_verified = auth.verify_code(user_data["email_code"], user_data["email"])
        if not is_email_verified:
            return generate_error_data(email_verification_error, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        hashed_password = generate_password_hash(user_data["password"])

        session = Session()
        new_user = User(telegram=None, email=user_data["email"], password=hashed_password)
        session.add(new_user)
        session.commit()
        session.close()

        data = {}
        data["status"] = "ok"
        valid_messages.register_succeded(user_data["email"])
        return data, HTTPStatus.OK
    ## REGISTRO SIN TELEGRAM

    ## REGISTRO CON TELEGRAM
    if not register_data.TELEGRAM_CODE in request_body or request_body[register_data.TELEGRAM_CODE] == "":
        return generate_error_data(errors.TELEGRAM_CODE_NOT_PRESENT, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    telegram_id = request_body[register_data.TELEGRAM_ID]
    telegram_code = request_body[register_data.TELEGRAM_CODE]
    if re.match(r"^-[0-9]*$", telegram_id):
        return generate_error_data(errors.TELEGRAM_ID_NOT_VALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED
    session = Session()
    user_found = session.query(User).filter(User.telegram == str(telegram_id)).first()
    if user_found:
        if user_found.__dict__.get("email", False):
            session.close()
            return generate_error_data(errors.USER_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    telegram_verification_error, is_telegram_verified = auth.verify_code(telegram_code, telegram_id)
    if not is_telegram_verified:
        session.close()
        return generate_error_data(telegram_verification_error, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    email_verification_error, is_email_verified = auth.verify_code(user_data["email_code"], user_data["email"])
    if not is_email_verified:
        session.close()
        return generate_error_data(email_verification_error, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    hashed_password = generate_password_hash(user_data["password"])

    if user_found:
        user_found.email = user_data["email"]
        user_found.password = hashed_password
    else:
        ROLE_ID_NORMAL = 1
        new_user = User(telegram=telegram_id, email=user_data["email"], password=hashed_password)
        new_user.role_id = ROLE_ID_NORMAL
        session.add(new_user)

    session.commit()
    session.close()

    data = {}
    data["status"] = "ok"
    valid_messages.register_succeded(user_data["email"], telegram_id)
    return data, HTTPStatus.OK
    ## REGISTRO CON TELEGRAM


@register_routing_blueprint.route("/verify-telegram-code", methods=["POST"])
def verify_telegram_code():
    """
    Receive the telegram code sent by the user which must be verified
    If the code is valid, a telegram_id is added to an exising user

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "VerifyTelegramCode")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    if not register_data.TELEGRAM_CODE in request_body or request_body[register_data.TELEGRAM_CODE] == "":
        return generate_error_data(errors.TELEGRAM_CODE_NOT_PRESENT, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    email = request_body[register_data.EMAIL]
    telegram_id = request_body[register_data.TELEGRAM_ID]
    telegram_code = request_body[register_data.TELEGRAM_CODE]
    if re.match(r"^-[0-9]*$", telegram_id):
        return generate_error_data(errors.TELEGRAM_ID_NOT_VALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED
    session = Session()
    user_found = session.query(User).filter(User.telegram == str(telegram_id)).first()
    if user_found:
        if user_found.__dict__.get("email", False):
            session.close()
            return generate_error_data(errors.USER_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    telegram_verification_error, is_telegram_verified = auth.verify_code(telegram_code, telegram_id)
    if not is_telegram_verified:
        session.close()
        return generate_error_data(telegram_verification_error, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    actual_user = session.query(User).filter(User.email == str(email)).first()
    if not actual_user:
        session.close()
        return generate_error_data(errors.USER_NOT_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    if user_found:
        session.query(User).filter(User.telegram == str(telegram_id)).delete(synchronize_session=False)
        session.commit()

    actual_user.telegram = telegram_id
    session.commit()
    session.close()
    valid_messages.petition_completed("verify-telegram-code")
    data = {}
    data["status"] = "ok"
    return data, HTTPStatus.OK
