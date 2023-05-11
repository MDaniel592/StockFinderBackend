import logging
import os
import socket
from http import HTTPStatus
from uuid import UUID

import models.auth.auth_data as auth_data
import models.builds.build_data as build_data
import psycopg2
import psycopg2.extras
import utils.error_messages as errors
import utils.valid_messages as valid_messages
from database.db_connection import sql_connection
from database.stockfinder_models.Availability import Availability
from database.stockfinder_models.base import Session
from database.stockfinder_models.Build import Build
from database.stockfinder_models.Category import Category
from database.stockfinder_models.Manufacturer import Manufacturer
from database.stockfinder_models.Message import Message
from database.stockfinder_models.Product import Product
from database.stockfinder_models.ProductPartNumber import ProductPartNumber
from database.stockfinder_models.ProductSpec import ProductSpec
from database.stockfinder_models.Role import Role
from database.stockfinder_models.Shop import Shop
from database.stockfinder_models.Spec import Spec
from database.stockfinder_models.User import User
from flask import Blueprint, request
from sqlalchemy import and_
from utils.error_messages_management import generate_error_data
from utils.validate_inputs import valid_data_recv

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

build_routing_blueprint = Blueprint("build_routing", __name__)


ISO_TIME_FORMAT = "%d/%m/%Y %H:%M"

## Allowed categories
CATEGORIES = {
    "procesadores": "CPU",
    "tarjetas-graficas": "GPU",
    "placas-base": "Motherboard",
    "memoria-ram": "RAM",
    "almacenamiento": "Storage",
    "fuentes-alimentacion": "PSU",
    "torres": "Chassis",
    "disipadores-cpu": "CPU Cooler",
}


@build_routing_blueprint.route("get_build/<string:uuid>", methods=["GET"])
def get_build(uuid):
    """
    Returns dict of products matching the build UUID.

    :param uuid: product uuid to be retrieved
    :return: dict of products.
    """
    if not uuid:
        return generate_error_data(errors.UUID_NOT_VALID), HTTPStatus.UNAUTHORIZED

    try:
        uuid = str(uuid)
        uuid = UUID(uuid, version=4)
    except:
        return generate_error_data(errors.UUID_NOT_VALID), HTTPStatus.UNAUTHORIZED

    session = Session()
    build = session.query(Build).filter(Build.uuid == uuid).first()
    if not build:
        session.close()
        return generate_error_data(errors.UUID_NOT_VALID), HTTPStatus.UNAUTHORIZED

    data = {}
    data["build_name"] = build.name
    data["created"] = build.created_at.strftime(ISO_TIME_FORMAT)

    build_components = ["cpu", "gpu", "cooler", "motherboard", "case", "ram", "primary_storage", "secondary_storage", "psu"]
    for value in build_components:
        key = "chassis" if value == "case" else value
        key = "cpu cooler" if value == "cooler" else key
        key = "storage" if value == "primary_storage" else key
        key = "storage" if value == "secondary_storage" else key

        if not getattr(getattr(build, value, {}), "uuid", None):
            continue

        shop_name = getattr(getattr(getattr(build, value + "_availability", {}), "shop", {}), "name", None)
        shop_name = "PcComponentes" if shop_name == "PcComponentes Reacondicionados" else shop_name
        data[key] = {
            "uuid": getattr(getattr(build, value, {}), "uuid", None),
            "name": getattr(getattr(build, value, {}), "name", None),
            "original_price": getattr(build, value + "_price", 0),
            "actual_price": getattr(getattr(build, value + "_availability", {}), "price", 0),
            "url": getattr(getattr(build, value + "_availability", {}), "url", None),
            "shop": shop_name,
            "category": key,
        }

        db_image = getattr(getattr(build, value, {}), "images", None)
        if db_image:
            image = db_image.get("large", None)
            if not image:
                image = db_image.get("medium", None)
            if image:
                data[key]["image"] = image[0]

    session.close()
    valid_messages.petition_completed(f"get_build: {uuid}")
    return data, HTTPStatus.OK


@build_routing_blueprint.route("register_build", methods=["POST"])
def build_add():
    """
    Returns the UUID of the new build created.

    :param uuid: product uuid to be retrieved
    :return: a string (build uuid).
    """
    request_body = request.json
    data, status = valid_data_recv(request_body, "SPAM")
    if status != HTTPStatus.OK:
        return data, status
    user_data = data
    user_ip = user_data["user_ip"]

    allowed_keys = {
        build_data.CPU: True,
        build_data.GPU: True,
        build_data.PSU: True,
        build_data.RAM: True,
        build_data.CASE: True,
        build_data.COOLER: True,
        build_data.MOTHERBOARD: True,
        build_data.PRIMARY_STORAGE: True,
        build_data.SECONDARY_STORAGE: True,
    }
    build_dict = {}
    try:
        build_name = str(request_body[build_data.BUILD_NAME])
        build_dict["name"] = build_name

        request_body.pop(build_data.BUILD_NAME, None)
        request_body.pop(auth_data.USER_IP, None)

        session = Session()

        for key in request_body:
            result = allowed_keys.get(key, False)
            if not result:
                logger.error(f"{key} no permitida")
                session.close()
                return generate_error_data(errors.BUILD_NOT_VALID), HTTPStatus.UNAUTHORIZED

            product_uuid = request_body[key].get("uuid", False)
            availability_shop = request_body[key].get("shop", False)
            availability_price = request_body[key].get("price", False)
            if not availability_shop or not product_uuid or not availability_price:
                logger.error(f"Falta un parámetro: {product_uuid} {availability_shop} {availability_price}")
                session.close()
                return generate_error_data(errors.BUILD_NOT_VALID), HTTPStatus.UNAUTHORIZED

            product_uuid = str(product_uuid)
            availability_shop = str(availability_shop)
            availability_price = float(availability_price)
            #
            product_uuid = UUID(product_uuid, version=4)
            product_uuid = str(product_uuid)
            #

            db_product = session.query(Product).filter(Product.uuid == product_uuid).first()
            if not db_product:
                logger.error(errors.UUID_NOT_FOUND)
                session.close()
                return generate_error_data(errors.BUILD_NOT_VALID), HTTPStatus.UNAUTHORIZED
            product_id = db_product._id

            db_shop = session.query(Shop).filter(Shop.name == availability_shop).first()
            if not db_shop:
                logger.error(errors.SHOP_NOT_VALID)
                session.close()
                return generate_error_data(errors.BUILD_NOT_VALID), HTTPStatus.UNAUTHORIZED
            shop_id = db_shop._id

            availability = session.query(Availability).filter(and_(Availability.product_id == product_id, Availability.shop_id == shop_id)).first()
            if not availability:
                logger.error(errors.AVAILABILITY_NOT_FOUND)
                session.close()
                return generate_error_data(errors.BUILD_NOT_VALID), HTTPStatus.UNAUTHORIZED
            availabity_id = availability._id

            key_lower = str(key).lower()
            key_lower = "case" if key_lower == "chassis" else key_lower
            key_lower = "motherboard" if key_lower == "mdb" else key_lower
            key_lower = "primary_storage" if key_lower == "hdd" else key_lower

            build_dict[f"{key_lower}_id"] = product_id
            build_dict[f"{key_lower}_price"] = availability_price
            build_dict[f"{key_lower}_availability_id"] = availabity_id
    except:
        session.close()
        return generate_error_data(errors.BUILD_NOT_VALID, user_ip=user_ip), HTTPStatus.UNAUTHORIZED

    logger.warning(build_dict)

    session = Session()
    new_build = Build(**build_dict)
    session.add(new_build)
    session.commit()
    build_uuid = new_build.uuid
    session.close()

    data = {"build_uuid": build_uuid}
    valid_messages.petition_completed(f"register_build: {build_uuid}")
    return data, HTTPStatus.OK


@build_routing_blueprint.route("categories/<string:category>", methods=["GET"])
def get_product_from_category(category):
    """
    Returns a list of products matching that category. It comes with the Product format.

    :param category: product category to be retrieved
    :return: list of products.
    """
    if not category or not category in CATEGORIES:
        return {"products": []}
    image_str = "'image', COALESCE(images#>>'{medium, 0}',images#>>'{large, 0}')"

    query = f"""
        SELECT 
        json_agg(json_build_object(
            'uuid', p.uuid, 
            'name', p.name, 
            'refurbished', p.refurbished, 
            'specifications', ps.specs, 
            'availabilities', pa.availabilities, 
            'manufacturer', m.name,
            {image_str}
            ) ORDER BY pa.min_price
        ) as products
            
        FROM products p
        LEFT JOIN categories c on p.category_id = c._id 
        LEFT JOIN manufacturers m on p.manufacturer_id = m._id
        JOIN (
            SELECT product_id, json_object_agg(sp.name,ps.value) AS specs
            FROM product_specs ps
            LEFT JOIN specs sp on ps.spec_id = sp._id
            WHERE ps.value != 'None'
            GROUP BY 1
            ) ps on ps.product_id = p._id
        JOIN (
            SELECT 
            product_id, 
            MIN(pa.price) AS min_price,
            json_agg(
                json_build_object('shopName', sh.name, 'url', pa.url, 'price', pa.price) ORDER BY pa.price
            ) AS availabilities

            FROM products_availabilities pa
            LEFT JOIN shops sh on sh._id = pa.shop_id

            WHERE pa.deleted = {False}
            GROUP BY 1
            HAVING MIN(pa.price) > 0
            
            ) pa on p._id = pa.product_id

        WHERE c.name = '{CATEGORIES[category]}' and p.deleted = {False}
        """

    connection = sql_connection()
    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(query)
    products_dict = dict(cursor.fetchone())
    connection.close()

    valid_messages.petition_completed(f"get_product_from_category: {category}")
    return {"category": category, "products": products_dict["products"]}
