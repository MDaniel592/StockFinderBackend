import copy
import logging
import re
from http import HTTPStatus

import models.alert.alert_data as alert_data
import models.auth.auth_data as auth_data
import models.hcaptcha.hcaptchaToken as hcaptchaToken
import models.password.password_data as password_data
import models.register.register_data as register_data
import utils.error_messages as errors
from utils.error_messages_management import check_user_spam, generate_error_data
from utils.hcaptcha_data import hcaptcha

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True


def valid_data_recv(request_body, check):
    if not request_body:
        return generate_error_data(errors.REQUEST_EMPTY), HTTPStatus.UNAUTHORIZED

    if (not auth_data.USER_IP in request_body) or (request_body[auth_data.USER_IP] == ""):
        return generate_error_data(errors.USER_IP_NOT_PRESENT), HTTPStatus.UNAUTHORIZED

    user_ip = request_body[auth_data.USER_IP]
    result, data = check_user_spam(user_ip)
    if result:
        return data, HTTPStatus.UNAUTHORIZED

    user_data = {"user_ip": user_ip}

    request_copy = None
    if request_body.get("password", False):
        try:
            request_copy = copy.deepcopy(request_body)
            request_copy.pop("password")
            logger.info(request_copy)
        except:
            logger.error("Could not deepcopy password or remove it from the dict")
            pass

    if request_body.get("passwordConfirmation", False):
        try:
            request_copy = copy.deepcopy(request_body)
            request_copy.pop("passwordConfirmation")
            logger.info(request_copy)
        except:
            logger.error("Could not deepcopy password or remove it from the dict")
            pass

    if not request_copy:
        logger.info(request_body)

    if check == "SPAM":
        pass

    ####################################################################################################
    elif check == "UserLogin":
        if not hcaptchaToken.RESPONSE in request_body:
            return generate_error_data(errors.LOGIN_HCAPTCHA_NOTFOUND_ERROR, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        hcaptcha_res = request_body[hcaptchaToken.RESPONSE]
        if not hcaptcha.verify(response=hcaptcha_res, remote_ip=user_ip):
            return generate_error_data(errors.LOGIN_HCAPTCHA_ERROR, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if (not auth_data.EMAIL in request_body or request_body[auth_data.EMAIL] == "") or (
            not auth_data.PASSWORD in request_body or request_body[auth_data.PASSWORD] == ""
        ):
            return generate_error_data(errors.LOGIN_ERROR, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["email"] = str(request_body[auth_data.EMAIL])
            user_data["password"] = str(request_body[auth_data.PASSWORD])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED
    ####################################################################################################
    elif check == "Validate":
        if not request_body[auth_data.TOKEN] or request_body[auth_data.TOKEN] == "":
            return generate_error_data(errors.LOGIN_ERROR, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["token"] = str(request_body[auth_data.TOKEN])
        except:
            return generate_error_data(errors.TOKEN_INVALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED
    ####################################################################################################
    elif check == "EmailPasswordReset":
        if (not password_data.EMAIL in request_body) or (request_body[password_data.EMAIL] == ""):
            return generate_error_data(errors.EMAIL_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if not password_data.EMAIL_CODE in request_body or request_body[password_data.EMAIL_CODE] == "":
            return generate_error_data(errors.EMAIL_CODE_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if not password_data.PASSWORD in request_body or request_body[password_data.PASSWORD] == "":
            return generate_error_data(errors.PASSWORD_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["email"] = str(request_body[password_data.EMAIL])
            user_data["email_code"] = str(request_body[password_data.EMAIL_CODE])
            user_data["password"] = str(request_body[password_data.PASSWORD])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    ####################################################################################################
    elif check == "PasswordReset":
        if (not auth_data.TOKEN in request_body) or (request_body[auth_data.TOKEN] == ""):
            return generate_error_data(errors.TOKEN_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if (not password_data.NEW_PASSWORD in request_body) or (request_body[password_data.NEW_PASSWORD] == ""):
            return generate_error_data(errors.PASSWORD_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if (not password_data.CURRENT_PASSWORD in request_body) or (request_body[password_data.CURRENT_PASSWORD] == ""):
            return generate_error_data(errors.PASSWORD_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["token"] = str(request_body[auth_data.TOKEN])
            user_data["new_password"] = str(request_body[password_data.NEW_PASSWORD])
            user_data["current_password"] = str(request_body[password_data.CURRENT_PASSWORD])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    elif check == "VerifyPasswordResetCode":
        if (not password_data.EMAIL in request_body) or (request_body[password_data.EMAIL] == ""):
            return generate_error_data(errors.EMAIL_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if not password_data.EMAIL_CODE in request_body or request_body[password_data.EMAIL_CODE] == "":
            return generate_error_data(errors.EMAIL_CODE_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["email"] = str(request_body[password_data.EMAIL])
            user_data["email_code"] = str(request_body[password_data.EMAIL_CODE])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    ####################################################################################################
    elif check == "GetUserInfo":
        if (not auth_data.TOKEN in request_body) or (request_body[auth_data.TOKEN] == ""):
            return generate_error_data(errors.TOKEN_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["token"] = str(request_body[auth_data.TOKEN])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED
    ####################################################################################################
    elif check == "CheckUser":
        if (not alert_data.EMAIL in request_body) or (request_body[alert_data.EMAIL] == ""):
            return generate_error_data(errors.EMAIL_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["email"] = str(request_body[alert_data.EMAIL])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    ####################################################################################################
    elif check == "RegisterAlert":
        if (not auth_data.TOKEN in request_body) or (request_body[auth_data.TOKEN] == ""):
            return generate_error_data(errors.TOKEN_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if (not alert_data.ALERT_TYPE in request_body) or (request_body[alert_data.ALERT_TYPE] == ""):
            return generate_error_data(errors.ALERT_TYPE_NO_FOUND, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if request_body[alert_data.ALERT_TYPE] == "Enlace":
            if (not alert_data.URL in request_body) or (request_body[alert_data.URL] == ""):
                return generate_error_data(errors.URL_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED
        elif request_body[alert_data.ALERT_TYPE] == "Producto":
            if (not alert_data.UUID in request_body) or (request_body[alert_data.UUID] == ""):
                return generate_error_data(errors.UUID_NOT_FOUND, user_ip=user_ip), HTTPStatus.UNAUTHORIZED
        elif request_body[alert_data.ALERT_TYPE] == "Modelo":
            if (not alert_data.MODEL in request_body) or (request_body[alert_data.MODEL] == ""):
                return generate_error_data(errors.UUID_NOT_FOUND, user_ip=user_ip), HTTPStatus.UNAUTHORIZED
        else:
            return generate_error_data(errors.ALERT_TYPE_NO_FOUND, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if (not alert_data.PRICE in request_body) or (request_body[alert_data.PRICE] == ""):
            return generate_error_data(errors.PRICE_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["url"] = str(request_body[alert_data.URL])
            user_data["uuid"] = str(request_body[alert_data.UUID])
            user_data["model"] = str(request_body[alert_data.MODEL])
            user_data["price"] = float(request_body[alert_data.PRICE])
            user_data["alert_type"] = str(request_body[alert_data.ALERT_TYPE])
            user_data["telegram_check"] = True if request_body[alert_data.TELEGRAM_CHECK] else False
            user_data["mail_check"] = True if request_body[alert_data.EMAIL_CHECK] else False
            user_data["token"] = str(request_body[auth_data.TOKEN])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED
    ####################################################################################################
    elif check == "UpdateAlert":
        if (not auth_data.TOKEN in request_body) or (request_body[auth_data.TOKEN] == ""):
            return generate_error_data(errors.TOKEN_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if (not alert_data.ALERT_ID in request_body) or (request_body[alert_data.ALERT_ID] == ""):
            return generate_error_data(errors.URL_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["token"] = str(request_body[auth_data.TOKEN])
            user_data["user_prod_id"] = int(request_body[alert_data.ALERT_ID])
            user_data["telegram_check"] = 1 if request_body[alert_data.TELEGRAM_CHECK] else 0
            user_data["mail_check"] = 1 if request_body[alert_data.EMAIL_CHECK] else 0
            user_data["new_price"] = float(request_body[alert_data.PRICE])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    ####################################################################################################
    elif check == "DeleteAlert":
        if (not auth_data.TOKEN in request_body) or (request_body[auth_data.TOKEN] == ""):
            return generate_error_data(errors.TOKEN_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if (not alert_data.ALERT_ID in request_body) or (request_body[alert_data.ALERT_ID] == ""):
            return generate_error_data(errors.URL_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["token"] = str(request_body[auth_data.TOKEN])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID), HTTPStatus.UNAUTHORIZED
    ####################################################################################################
    elif check == "UserInfo":
        if (not register_data.EMAIL in request_body) or (request_body[register_data.EMAIL] == ""):
            return generate_error_data(errors.EMAIL_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if (not register_data.PASSWORD in request_body or request_body[register_data.PASSWORD] == "") or (
            not register_data.PASSWORD_CONFIRMATION in request_body or request_body[register_data.PASSWORD_CONFIRMATION] == ""
        ):
            return generate_error_data(errors.PASSWORD_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if not str(request_body[register_data.PASSWORD]) == str(request_body[register_data.PASSWORD_CONFIRMATION]):
            return generate_error_data(errors.PASSWORD_MISMATCH, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["email"] = str(request_body[register_data.EMAIL]).lower()
            user_data["password"] = str(request_body[register_data.PASSWORD])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    ####################################################################################################
    elif check == "TelegramID":
        if not register_data.TELEGRAM_ID in request_body:
            return generate_error_data(errors.TELEGRAM_ID_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if re.match(r"^-[0-9]*$", str(request_body[register_data.TELEGRAM_ID])):
            return generate_error_data(errors.TELEGRAM_ID_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["telegram_id"] = int(request_body[register_data.TELEGRAM_ID])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED
    ####################################################################################################
    elif check == "GenerateCode":
        if (not register_data.PARAM_NAME in request_body) or (request_body[register_data.PARAM_NAME] == ""):
            return generate_error_data(errors.USER_IP_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if (not register_data.PARAM_VALUE in request_body) or (request_body[register_data.PARAM_VALUE] == ""):
            return generate_error_data(errors.USER_IP_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["param_name"] = str(request_body[register_data.PARAM_NAME])
            user_data["param_value"] = request_body[register_data.PARAM_VALUE]
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    ####################################################################################################
    elif check == "VerifyRegisterCodes":
        if not register_data.EMAIL in request_body or request_body[register_data.EMAIL] == "":
            return generate_error_data(errors.EMAIL_CODE_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if not register_data.EMAIL_CODE in request_body or request_body[register_data.EMAIL_CODE] == "":
            return generate_error_data(errors.EMAIL_CODE_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        if not register_data.PASSWORD in request_body or request_body[register_data.PASSWORD] == "":
            return generate_error_data(errors.EMAIL_CODE_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["email"] = str(request_body[register_data.EMAIL]).lower()
            user_data["email_code"] = str(request_body[register_data.EMAIL_CODE])
            user_data["password"] = str(request_body[register_data.PASSWORD])
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    ####################################################################################################
    elif check == "VerifyTelegramCode":
        if not register_data.EMAIL in request_body or request_body[register_data.EMAIL] == "":
            return generate_error_data(errors.EMAIL_CODE_NOT_PRESENT, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

        try:
            user_data["email"] = str(request_body[register_data.EMAIL]).lower()
        except:
            return generate_error_data(errors.PARAM_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    ####################################################################################################
    else:
        logger.error(f"Why the user has reached this point? - check: {check}")
        return generate_error_data(errors.DATA_NOT_PRESENT), HTTPStatus.UNAUTHORIZED

    ####################################################################################################
    return user_data, HTTPStatus.OK
