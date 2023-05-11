import logging
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

user_routing_blueprint = Blueprint("user_routing", __name__)


@user_routing_blueprint.route("/get-user-info", methods=["POST"])
def get_user_info():
    """
    Get the user information.

    :return: a JSON with status key error/ok keys, user data and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "GetUserInfo")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    # Validamos el token
    decoded_token, decode_result = Token.JwtToken.decode(user_data["token"])
    if not decode_result:
        return generate_error_data(errors.TOKEN_INVALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    email = decoded_token[auth_data.EMAIL]
    # telegram = decoded_token[user_data.TELEGRAM_ID] if decoded_token[user_data.TELEGRAM_ID] else None

    session = Session()
    user_found = session.query(User).filter(User.email == email).first()

    if not user_found:
        session.close()
        return generate_error_data(errors.USER_NOT_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    data["telegram_id"] = user_found.telegram
    data["mail"] = user_found.email
    data["pass"] = user_found.password
    data["max_watches"] = user_found.role.max_watches
    data["current_watches"] = len(user_found.alerts)

    watches = []
    for alert in user_found.alerts:
        if alert.deleted == True:
            continue

        if alert.availability:
            try:
                images_dict = alert.availability.product.images
                images = images_dict.get("small", None) if images_dict.get("small", None) else images_dict.get("medium", "")
                image = "https://images.stockfinder.tech" + images[0] if images else images
            except:
                image = ""

            watched_product = {
                "id": alert._id,
                "user_max_price": alert.max_price,
                "product_data": {
                    "image": image,
                    "url": "producto/" + str(alert.availability.product.uuid),
                    "stock": alert.availability.stock,
                    "price": alert.availability.price,
                    "name": alert.availability.product.name,
                    "telegram_alert": alert.alert_by_telegram,
                    "mail_alert": alert.alert_by_email,
                    "shop": alert.availability.shop.name,
                },
                "spec_data": {},
                "alert_type": "Enlace",
            }
        elif alert.product:
            try:
                images_dict = alert.product.images
                images = images_dict.get("small", None) if images_dict.get("small", None) else images_dict.get("medium", "")
                image = "https://images.stockfinder.tech" + images[0] if images else images
            except:
                image = ""

            price_stock_true = 99999999
            price_stock_false = 99999999
            for availaibility in alert.product.availabilities:
                if availaibility.price < price_stock_true and availaibility.stock == 1:
                    price_stock_true = availaibility.price
                elif availaibility.price < price_stock_false and availaibility.stock == 0:
                    price_stock_false = availaibility.price
                continue

            price = price_stock_true if price_stock_true != 99999999 else price_stock_false

            watched_product = {
                "id": alert._id,
                "user_max_price": alert.max_price,
                "product_data": {
                    "image": image,
                    "url": "producto/" + str(alert.product.uuid),
                    "stock": True if price_stock_true != 99999999 else False,
                    "price": price,
                    "name": alert.product.name,
                    "telegram_alert": alert.alert_by_telegram,
                    "mail_alert": alert.alert_by_email,
                },
                "spec_data": {},
                "alert_type": "Producto",
            }
        elif alert.spec_id:
            watched_product = {
                "id": alert._id,
                "user_max_price": alert.max_price,
                "spec_data": {
                    "name": alert.spec_value,
                    "telegram_alert": alert.alert_by_telegram,
                    "mail_alert": alert.alert_by_email,
                },
                "product_data": {},
                "alert_type": "Modelo",
            }
        else:
            continue
        watches.append(watched_product)

    session.close()
    watches = sorted(watches, key=lambda d: d["id"])
    data = {"products": watches}
    data["status"] = "ok"
    valid_messages.petition_completed("get-user-info")
    return data, HTTPStatus.OK


@user_routing_blueprint.route("/check_user", methods=["POST"])
def check_user():
    """
    Check if user is valid and exists.

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "CheckUser")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    email_validation, is_email_validated = is_email_valid(["user_data.email"])
    if not is_email_validated:
        return generate_error_data(email_validation, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    session = Session()
    email_found = session.query(User.email).filter(User.email == user_data["email"]).first()
    session.close()
    if not email_found:
        return generate_error_data(errors.USER_NOT_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    data = {}
    data["status"] = "ok"
    data["ok"] = "El usuario existe"
    valid_messages.petition_completed("check_user")
    return data, HTTPStatus.OK
