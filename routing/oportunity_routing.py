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
    Returns the product matching the uuid.

    :param uuid: identify the product
    :return: dictionary the product specifications
    """
    remove_columns = ["table", "result", "_start", "_stop", "_field", "_measurement"]
    #

    query = f"""
        from(bucket:"{INFLUXDB_BUCKET}")
            |> range(start: -7d, stop: -1d) // Retrieve data for the last 7 days
            |> filter(fn: (r) => r["_measurement"] == "prices")
            |> filter(fn: (r) => r["_field"] == "price")
            |> min()
            |> yield(name: "min_price")
        """
    min_price_table = query_api.query_data_frame(query=query)
    min_price_table = min_price_table.drop(columns=remove_columns)
    min_price_table = min_price_table.groupby(["uuid", "shop"])

    # Create a dictionary to store the minimum prices by product and shop
    min_prices = {}

    # Iterate over the 'min_price' table and populate the 'min_prices' dictionary
    for grouped_keys, grouped_data in min_price_table:
        product_uuid, shop = grouped_keys
        price = float(grouped_data["_value"])

        if product_uuid not in min_prices:
            min_prices[product_uuid] = {}

        min_prices[product_uuid][shop] = price

    query = f"""
        from(bucket:"{INFLUXDB_BUCKET}")
            |> range(start: -1d) // Retrieve data for the last 1 day (current day)
            |> filter(fn: (r) => r["_measurement"] == "prices")
            |> filter(fn: (r) => r["_field"] == "price")
            |> last()
            |> yield(name: "current_price")
        """
    current_price_table = query_api.query_data_frame(query=query)
    current_price_table = current_price_table.drop(columns=remove_columns)
    current_price_table = current_price_table.groupby(["uuid", "shop"])

    result = {10: [], 20: [], 30: []}
    # Iterate over the 'current_price' table and compare with the minimum prices
    session = Session()
    for grouped_keys, grouped_data in current_price_table:
        product_uuid, shop = grouped_keys
        price = float(grouped_data["_value"])

        if product_uuid in min_prices and shop in min_prices[product_uuid]:
            min_price = min_prices[product_uuid][shop]

            product = {"uuid": product_uuid, "shop": shop, "price": price}
            if price * 1.1 <= min_price and price * 1.3 < min_price:
                db_product = session.query(Product).filter(Product.uuid == product_uuid).first()
                product["name"] = db_product.name
                product["image"] = get_image(db_product.images)
                result[10].append(product)

            elif price * 1.2 <= min_price and price * 1.3 < min_price:
                db_product = session.query(Product).filter(Product.uuid == product_uuid).first()
                product["name"] = db_product.name
                product["image"] = get_image(db_product.images)
                result[20].append(product)

            elif price * 1.3 <= min_price:
                db_product = session.query(Product).filter(Product.uuid == product_uuid).first()
                product["name"] = db_product.name
                product["image"] = get_image(db_product.images)
                result[30].append(product)

    session.close()
    return result
