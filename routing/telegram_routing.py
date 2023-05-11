import logging

import psycopg2
import psycopg2.extras
import utils.valid_messages as valid_messages
from database.db_connection import sql_connection
from flask import Blueprint, request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True


telegram_routing_blueprint = Blueprint("telegram_routing", __name__)


@telegram_routing_blueprint.route("/api/telegram_channels", methods=["GET"])
def get_telegram_channels():
    """
    Get the existing telegram channels.

    :return: a dictionary with each telegram channel
    """
    query = f"""
                SELECT 

                json_build_object('channel_name', channel_name, 'image', image, 'url', url, 'data', json_agg(json_build_object('max_price', tc.max_price, 'modelo', tc.product_spec_value, 'status', tc.deleted::int)) )

                FROM telegram_channels tc

                GROUP BY channel_name, tc.image,  tc.url
            """

    connection = sql_connection()
    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(query)
    data = cursor.fetchall()
    connection.close()

    telegram_dict = {}
    for index in range(len(data)):
        telegram_dict[index] = data[index][0]

    valid_messages.petition_completed("telegram_channels")
    return telegram_dict
