import datetime
import logging
import os
import socket
import warnings
from uuid import UUID

import pandas as pd
import psycopg2
import psycopg2.extras
import pytz
import utils.error_messages as errors
import utils.valid_messages as valid_messages
from database.db_connection import sql_connection
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

    if HOSTNAME:
        # Localhost / Docker
        return INFLUXDB_LOCAL_URL
    else:
        # Remote Host
        return INFLUXDB_REMOTE_URL


client = InfluxDBClient(url=get_influx_url(), token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

product_routing_blueprint = Blueprint("product_routing", __name__)


@product_routing_blueprint.route("/api/product/<string:uuid>", methods=["GET"])
def get_product(uuid):
    """
    Returns the product matching the uuid.

    :param uuid: identify the product
    :return: dictionary the product specifications
    """
    if not uuid:
        return {}

    try:
        uuid = str(uuid)
        uuid = UUID(uuid, version=4)
    except:
        logger.error(errors.UUID_NOT_VALID)
        logger.error(uuid)
        return {}

    image_str = "'images', COALESCE(images#>>'{large}',images#>>'{medium}')"

    query = f"""
                SELECT 

                json_agg(json_build_object('name', p.name, {image_str}, 'manufacturer', m.name, 'specifications', ps.specs, 'availabilities', availability, 'category', c.name)) as product_data

                    
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
                    SELECT product_id, json_agg(json_build_object('shopName', sh.name, 'price', pa.price, 'stock', pa.stock, 'url', pa.url, 'outlet', pa.outlet)) as availability
                    FROM products_availabilities pa
                    LEFT JOIN shops sh on sh._id = pa.shop_id
                    WHERE pa.price > 0
                    GROUP BY product_id
                    ) pa on p._id = pa.product_id

                WHERE p.uuid = '{uuid}'
            """

    connection = sql_connection()
    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(query)
    product_dict = dict(cursor.fetchone())
    connection.close()

    if not product_dict or product_dict["product_data"] == None:
        logger.warning(f"No hay datos del producto {product_dict}")
        return {}

    params = {
        "_start": datetime.datetime(2022, 1, 1).astimezone(pytz.timezone("CET")),
        "_end": datetime.datetime.now(pytz.timezone("CET")) + datetime.timedelta(days=1),
    }

    query = f"""
        from(bucket:"{INFLUXDB_BUCKET}")
        |> range(start: _start, stop: now())
        |> filter(fn: (r) => r["_measurement"] == "prices" and r["uuid"] == "{str(uuid)}")
        |> aggregateWindow(every: 1d, fn: min, createEmpty: false)
        |> yield(name: "prices")
        """

    historical_prices = {}
    labels = []
    try:
        df = query_api.query_data_frame(query=query, params=params)
        remove_columns = ["table", "result", "_start", "_stop", "_field", "_measurement", "uuid"]
        df = df.drop(columns=remove_columns)

        df["_time"] = pd.to_datetime(df["_time"].dt.date)
        df_min_values = df.groupby(["_time", "shop"]).min().reset_index()

        time_list = df_min_values["_time"].tolist()
        for time in time_list:
            formatted_time = time.strftime("%Y-%m-%d")
            if formatted_time in labels:
                continue
            labels.append(formatted_time)

        datasets = []
        groups = df_min_values.groupby("shop")
        shop_counts = groups.size().to_dict()
        for shop in shop_counts:
            if shop_counts[shop] == len(labels):
                continue

            times = df_min_values["_time"].unique()
            shops = df_min_values["shop"].unique()
            rows = []
            for time in times:
                for shop in shops:
                    row = {"_time": time, "shop": shop}
                    values = df_min_values.loc[(df_min_values["_time"] == time) & (df_min_values["shop"] == shop), "_value"]
                    if values.empty:
                        row["_value"] = "null"
                    else:
                        row["_value"] = values.iloc[0]
                    rows.append(row)

            df_min_values = pd.DataFrame(rows)

        groups = df_min_values.groupby("shop")
        for name, group in groups:
            data = {
                "label": name,
                "data": group["_value"].tolist(),
            }
            datasets.append(data)

        historical_prices = {"labels": labels, "datasets": datasets}

    except:
        logger.error(errors.HISTORICAL_PRICES_NOT_GATHERED)
        product_dict = product_dict["product_data"][0]
        return product_dict

    try:
        product_dict = product_dict["product_data"][0]
        product_dict["historical_prices"] = historical_prices
        valid_messages.petition_completed(f"product: {uuid}")
        return product_dict
    except:
        logger.error(errors.RESPONSE_EMPTY)
        return {}
