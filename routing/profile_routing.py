import logging
from http import HTTPStatus
from uuid import UUID

import models.alert.alert_data as alert_data
import models.auth.auth_data as auth_data
import models.jwt.JwtToken as Token
import utils.error_messages as errors
import utils.valid_messages as valid_messages
from database.stockfinder_models.Alert import Alert
from database.stockfinder_models.Availability import Availability
from database.stockfinder_models.base import Session
from database.stockfinder_models.NewAvailability import NewAvailability
from database.stockfinder_models.Product import Product
from database.stockfinder_models.ProductSpec import ProductSpec
from database.stockfinder_models.User import User
from flask import Blueprint, request
from sqlalchemy import and_
from utils.common import check_url_is_valid, extract_shop, fix_clear_url
from utils.error_messages_management import generate_error_data
from utils.validate_inputs import valid_data_recv

# enabling logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

profile_routing_blueprint = Blueprint("profile_routing", __name__)


@profile_routing_blueprint.route("/register_alert", methods=["POST"])
def register_alert():
    """
    Creates a new alert (there are 3 types of alerts) depending on the data received.

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "RegisterAlert")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    # Validamos el token
    decoded_token, decode_result = Token.JwtToken.decode(user_data["token"])
    if not decode_result:
        return generate_error_data(errors.TOKEN_INVALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    email = decoded_token[alert_data.EMAIL]
    # telegram = decoded_token[user_data['TELEGRAM_ID]

    # Validamos la UUID
    if user_data["alert_type"] == "Producto":
        try:
            uuid = UUID(user_data["uuid"], version=4)
        except:
            logger.error(errors.UUID_NOT_VALID)
            logger.error(uuid)
            return generate_error_data(errors.UUID_NOT_VALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    session = Session()
    user_found = session.query(User).filter(User.email == email).first()
    if not user_found:
        session.close()
        return generate_error_data(errors.USER_NOT_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    current_watches = len(session.query(Alert).filter(and_(Alert.user_id == user_found._id, Alert.deleted == False)).all())
    max_watches = user_found.role.max_watches
    if not current_watches < max_watches:
        session.close()
        return generate_error_data(errors.URL_MAX_REACHED, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    ##############
    # Modelo
    ##############
    if user_data["alert_type"] == "Modelo":
        spec_value = user_data["model"]
        result = session.query(ProductSpec).filter(and_(ProductSpec.spec_id == 3, ProductSpec.value == spec_value)).first()
        if not result:
            session.close()
            return generate_error_data(errors.GPU_SPEC_NOT_FOUND, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        user_alerts = user_found.alerts
        for alert in user_alerts:
            if not alert.spec_value or not alert.spec_id:
                continue
            elif alert.spec_value == spec_value and alert.deleted == False:
                session.close()
                return generate_error_data(errors.URL_ALREADY_REGISTER, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED
            elif alert.spec_value == spec_value and alert.deleted == True:
                alert.deleted = False
                alert.max_price = user_data["price"]
                alert.alert_by_telegram = user_data["telegram_check"]
                alert.alert_by_email = user_data["mail_check"]
                session.commit()
                session.close()
                data = {}
                data["status"] = "ok"
                data["ok"] = "La alerta ya existía y ha sido actualizada"
                return data, HTTPStatus.OK

        new_alert = Alert(
            user_id=int(user_found._id),
            spec_id=int(3),
            spec_value=spec_value,
            max_price=user_data["price"],
            alert_by_telegram=user_data["telegram_check"],
            alert_by_email=user_data["mail_check"],
        )
        session.add(new_alert)
        session.commit()
        session.close()

        data["status"] = "ok"
        data["ok"] = "Se ha añadido la alerta"
        valid_messages.petition_completed(f"register_alert {email}")
        return data, HTTPStatus.OK

    ##############
    # Producto
    ##############
    if user_data["alert_type"] == "Producto":
        product = session.query(Product).filter(Product.uuid == uuid).first()
        if not product:
            session.close()
            return generate_error_data(errors.PRODUCT_NOT_FOUND, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        user_alerts = user_found.alerts
        for alert in user_alerts:
            if not alert.product:
                continue
            elif alert.product.uuid == uuid and alert.deleted == False:
                session.close()
                return generate_error_data(errors.URL_ALREADY_REGISTER, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED
            elif alert.product.uuid == uuid and alert.deleted == True:
                alert.deleted = False
                alert.max_price = user_data["price"]
                alert.alert_by_telegram = user_data["telegram_check"]
                alert.alert_by_email = user_data["mail_check"]
                session.commit()
                session.close()
                data = {}
                data["status"] = "ok"
                data["ok"] = "La alerta ya existía y ha sido actualizada"
                return data, HTTPStatus.OK

        new_alert = Alert(
            user_id=int(user_found._id),
            product_id=int(product._id),
            max_price=user_data["price"],
            alert_by_telegram=user_data["telegram_check"],
            alert_by_email=user_data["mail_check"],
        )
        session.add(new_alert)
        session.commit()
        session.close()

        data["status"] = "ok"
        data["ok"] = "Se ha añadido la alerta"
        valid_messages.petition_completed(f"register_alert {email} - uuid: {uuid}")
        return data, HTTPStatus.OK

    ##############
    # Enlace
    ##############
    if user_data["alert_type"] == "Enlace":
        result = check_url_is_valid(url=user_data["url"])
        if not result:
            session.close()
            return generate_error_data(errors.URL_NOT_VALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        shop_name = extract_shop(url=user_data["url"])
        if not shop_name:
            session.close()
            return generate_error_data(errors.SHOP_NOT_VALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

        url = fix_clear_url(shop_name=shop_name, url=user_data["url"])

        counter = 0
        user_alerts = user_found.alerts
        for alert in user_alerts:
            counter += 1
            if not alert.availability:
                continue
            elif alert.availability.url == url and alert.deleted == False:
                session.close()
                return generate_error_data(errors.URL_ALREADY_REGISTER, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED
            elif alert.availability.url == url and alert.deleted == True:
                alert.deleted = False
                alert.max_price = user_data["price"]
                alert.alert_by_telegram = user_data["telegram_check"]
                alert.alert_by_email = user_data["mail_check"]
                session.commit()
                session.close()
                data = {}
                data["status"] = "ok"
                data["ok"] = "La alerta será procesada en unos minutos"
                return data, HTTPStatus.OK

        # Double check ¿?
        # if not counter < max_watches:
        #     session.close()
        #     return
        #         generate_error_data(errors.URL_MAX_REACHED, user_ip=user_ip),
        #         HTTPStatus.UNAUTHORIZED
        #     )

        availability = session.query(Availability).filter(Availability.url == url).first()
        if availability:
            availability = availability.__dict__
            availability_id = int(availability.get("_id", None))
            logger.warning(availability_id)
            new_alert = Alert(
                user_id=int(user_found._id),
                availability_id=availability_id,
                max_price=user_data["price"],
                alert_by_telegram=user_data["telegram_check"],
                alert_by_email=user_data["mail_check"],
            )
            session.add(new_alert)
            session.commit()
            session.close()
            data = {}
            data["status"] = "ok"
            data["ok"] = "Se ha añadido la alerta"
            valid_messages.petition_completed(f"register_alert {email} - url: {url}")
            return data, HTTPStatus.OK

        logger.warning(f"No existe la disponibilidad - url: {url} - Se añade a la tabla new_availabilities")
        new_availability = NewAvailability(
            user_id=int(user_found._id),
            max_price=user_data["price"],
            url=url,
            alert_by_telegram=user_data["telegram_check"],
            alert_by_email=user_data["mail_check"],
        )
        session.add(new_availability)
        session.commit()
        session.close()

        data = {}
        data["status"] = "ok"
        data["ok"] = "La alerta será procesada en unos minutos"
        valid_messages.petition_completed(f"register_alert {email} - url: {url}")
        return data, HTTPStatus.OK

    return generate_error_data(errors.ALERT_TYPE_NO_FOUND, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED


@profile_routing_blueprint.route("/update_alert", methods=["POST"])
def update_alert():
    """
    Updates an existing alert (enable/disable alert or change price).

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "UpdateAlert")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    # Validamos el token
    decoded_token, decode_result = Token.JwtToken.decode(user_data["token"])
    if not decode_result:
        return generate_error_data(errors.TOKEN_INVALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    email = decoded_token[auth_data.EMAIL]
    # telegram = decoded_token[user_data['TELEGRAM_ID]

    session = Session()
    user_found = session.query(User).filter(User.email == email).first()
    if not user_found:
        session.close()
        return generate_error_data(errors.USER_NOT_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    # DB Write
    session.query(Alert).filter(and_(Alert.user_id == user_found._id, Alert._id == user_data["user_prod_id"])).update(
        {"alert_by_telegram": user_data["telegram_check"], "alert_by_email": user_data["mail_check"], "max_price": user_data["new_price"]}
    )
    session.commit()
    session.close()

    data = {}
    data["status"] = "ok"
    data["ok"] = "Se ha actualizado la alerta"
    valid_messages.petition_completed(f'update_alert {email} - alert_id: {user_data["user_prod_id"]}')
    return data, HTTPStatus.OK


@profile_routing_blueprint.route("/delete_alert", methods=["POST"])
def delete_alert():
    """
    Deletes an existing alert.

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "DeleteAlert")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    # Validamos el token
    decoded_token, decode_result = Token.JwtToken.decode(user_data["token"])
    if not decode_result:
        return generate_error_data(errors.TOKEN_INVALID, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    email = str(decoded_token[auth_data.EMAIL])
    # telegram = int(decoded_token[user_data['TELEGRAM_ID]) if decoded_token[user_data['TELEGRAM_ID] and decoded_token[user_data['TELEGRAM_ID] != "" else None
    alert_id = int(request_body[alert_data.ALERT_ID])

    session = Session()
    user_found = session.query(User).filter(User.email == email).first()
    if not user_found:
        session.close()
        return generate_error_data(errors.USER_NOT_EXISTS, user_ip=user_data["user_ip"]), HTTPStatus.UNAUTHORIZED

    db_alert_data = session.query(Alert).filter(and_(Alert.user_id == user_found._id, Alert._id == alert_id)).first()
    db_alert_data.deleted = True
    session.commit()
    session.close()

    data = {}
    data["status"] = "ok"
    data["ok"] = "Se ha eliminado la alerta"
    valid_messages.petition_completed(f"delete_alert {email} - alert_id: {alert_id}")
    return data, HTTPStatus.OK


@profile_routing_blueprint.route("/select_models_gpu", methods=["POST"])
def select_models_gpu():
    """
    Selects the GPU models available for creating a new alert.

    :return: a JSON with status key error/ok keys and a HTTP Status Code
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "CheckUser")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data

    email = str(user_data[auth_data.EMAIL])

    session = Session()
    db_data = session.query(ProductSpec.value).distinct(ProductSpec.value).filter(ProductSpec.spec_id == 3).all()
    session.close()

    gpu_models = []
    for model in db_data:
        gpu_models.append(model[0])
        continue

    data = {"data": gpu_models}
    data["status"] = "ok"
    data["ok"] = ""
    valid_messages.petition_completed(f"select_models_gpu {email}")
    return data, HTTPStatus.OK
