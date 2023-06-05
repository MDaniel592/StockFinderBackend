import logging
import os
import warnings

import utils.error_messages as errors
import utils.valid_messages as valid_messages
from database.stockfinder_models.base import Session
from database.stockfinder_models.Product import Product
from flask import Blueprint
from influxdb_client import InfluxDBClient
from influxdb_client.client.warnings import MissingPivotFunction

warnings.simplefilter("ignore", MissingPivotFunction)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

HOSTNAME = os.environ.get("HOSTNAME", False)
INFLUXDB_LOCAL_URL = os.environ.get("INFLUXDB_LOCAL_URL")
INFLUXDB_REMOTE_URL = os.environ.get("INFLUXDB_REMOTE_URL")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")


def get_influx_url():
    """
    Returns the influxDB URL depending of the hostname/environment.

    :return: string of influxDB URL
    """

    if HOSTNAME == "Docker":
        # Localhost / Docker
        return INFLUXDB_LOCAL_URL
    else:
        # Remote Host
        return INFLUXDB_REMOTE_URL


client = InfluxDBClient(url=get_influx_url(), token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

oportunity_routing_blueprint = Blueprint("oportunity_routing", __name__)


def get_image(images):
    if images == None:
        return ""

    medium = images.get("medium", None)
    if medium:
        return medium[0]

    large = images.get("large", None)
    if large:
        return large[0]

    return ""


@oportunity_routing_blueprint.route("/get_oportunities", methods=["GET"])
def get_oportinities():
    """
    Returns the products with a discount greater than 20%.

    :return: dictionary of products (uuid, name, shop, price and image)
    """
    remove_columns = ["table", "result", "_start", "_stop", "_field", "_measurement", "shop"]
    query = f"""
        from(bucket:"{INFLUXDB_BUCKET}")
            |> range(start: -7d, stop: -1d) // Retrieve data for the last 7 days
            |> filter(fn: (r) => r["_measurement"] == "prices")
            |> filter(fn: (r) => r["_field"] == "price")
            |> group(columns: ["uuid"])
            |> min(column: "_value")
            |> yield(name: "min_price")
        """
    min_price_table = query_api.query_data_frame(query=query)
    min_price_table = min_price_table.drop(columns=remove_columns)

    min_prices = {}

    for index, row in min_price_table.iterrows():
        product_uuid = row["uuid"]
        price = float(row["_value"])

        if product_uuid not in min_prices:
            min_prices[product_uuid] = {"price": price}

    remove_columns = ["table", "result", "_start", "_stop", "_field", "_measurement"]
    query = f"""
        from(bucket:"{INFLUXDB_BUCKET}")
            |> range(start: -1d) // Retrieve data for the last 1 day (current day)
            |> filter(fn: (r) => r["_measurement"] == "prices")
            |> filter(fn: (r) => r["_field"] == "price")
            |> group(columns: ["uuid"])
            |> min(column: "_value")
            |> yield(name: "current_price")
        """
    current_price_table = query_api.query_data_frame(query=query)
    current_price_table = current_price_table.drop(columns=remove_columns)

    result = {20: [], 30: [], 40: [], 50: []}
    # Iterate over the 'current_price' table and compare with the minimum prices
    session = Session()
    for index, row in current_price_table.iterrows():
        shop = row["shop"]
        product_uuid = row["uuid"]
        current_price = float(row["_value"])

        if product_uuid not in min_prices:
            continue

        lowest_price = min_prices[product_uuid]["price"]
        product = {"uuid": product_uuid, "shop": shop, "price": current_price}

        if current_price * 1.5 <= lowest_price:
            db_product = session.query(Product).filter(Product.uuid == product_uuid).first()
            product["name"] = db_product.name
            product["image"] = get_image(db_product.images)
            result[50].append(product)

        if current_price * 1.4 <= lowest_price:
            db_product = session.query(Product).filter(Product.uuid == product_uuid).first()
            product["name"] = db_product.name
            product["image"] = get_image(db_product.images)
            result[40].append(product)

        if current_price * 1.3 <= lowest_price:
            db_product = session.query(Product).filter(Product.uuid == product_uuid).first()
            product["name"] = db_product.name
            product["image"] = get_image(db_product.images)
            result[30].append(product)

        elif current_price * 1.2 <= lowest_price:
            db_product = session.query(Product).filter(Product.uuid == product_uuid).first()
            product["name"] = db_product.name
            product["image"] = get_image(db_product.images)
            result[20].append(product)

    session.close()
    return result
