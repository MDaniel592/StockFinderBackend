import logging
import math
import re

import psycopg2
import psycopg2.extras
import utils.valid_messages as valid_messages
from database.db_connection import sql_connection
from flask import Blueprint

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True


apistock_routing_blueprint = Blueprint("apistock_routing", __name__)

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


## Allowed groups
SPECS_VALUES = {
    "RTX3050": "GeForce RTX 3050",
    "RTX3060": "GeForce RTX 3060",
    "RTX3060LHR": "GeForce RTX 3060 LHR",
    "RTX3060TI": "GeForce RTX 3060 Ti",
    "RTX3060TILHR": "GeForce RTX 3060 Ti LHR",
    "RTX3070": "GeForce RTX 3070",
    "RTX3070LHR": "GeForce RTX 3070 LHR",
    "RTX3070TI": "GeForce RTX 3070 Ti",
    "RTX3070TILHR": "GeForce RTX 3070 Ti",
    "RTX3080": "GeForce RTX 3080 10GB",
    "RTX3080LHR": "GeForce RTX 3080 10GB LHR",
    "RTX308012GB": "GeForce RTX 3080 12GB",
    "RTX308012GBLHR": "GeForce RTX 3080 12GB",
    "RTX3080TI": "GeForce RTX 3080 Ti",
    "RTX3080TILHR": "GeForce RTX 3080 Ti",
    "RTX3090": "GeForce RTX 3090",
    "RTX3090LHR": "GeForce RTX 3090 LHR",
    "RTX3090TI": "GeForce RTX 3090 Ti",
    "RTX4060TI": "GeForce RTX 4060 Ti",
    "RTX4070": "GeForce RTX 4070",
    "RTX4070TI": "GeForce RTX 4070 Ti",
    "RTX4080": "GeForce RTX 4080",
    "RTX4090": "GeForce RTX 4090",
    ########################
    "RX6400": "Radeon RX 6400",
    "RX6500XT": "Radeon RX 6500 XT",
    "RX6600": "Radeon RX 6600",
    "RX6600XT": "Radeon RX 6600 XT",
    "RX6650XT": "Radeon RX 6650 XT",
    "RX6700": "Radeon RX 6700",
    "RX6700XT": "Radeon RX 6700 XT",
    "RX6750XT": "Radeon RX 6750 XT",
    "RX6800": "Radeon RX 6800",
    "RX6800XT": "Radeon RX 6800 XT",
    "RX6900XT": "Radeon RX 6900 XT",
    "RX6950XT": "Radeon RX 6950 XT",
    "RX7600": "Radeon RX 7600",
    "RX7900XT": "Radeon RX 7900 XT",
    "RX7900XTX": "Radeon RX 7900 XTX",
}


@apistock_routing_blueprint.route("/api/stock/<string:category>", methods=["GET"])
def get_category_products_in_stock(category):
    """
    Returns all the products in stock matching the category.

    :param category: type of product
    :return: dictionary with a list of products
    """
    if not category:
        return {}

    category = str(category)
    result = SPECS_VALUES.get(category, None)
    if not result:
        return {}

    selected = ()
    if "RTX" in category:
        is_ti_model = "TI" in category
        for key, value in SPECS_VALUES.items():
            if category in key and (is_ti_model or "TI" not in key):
                if value not in selected:
                    selected += (value,)
    elif "RX" in category:
        selected = (result,)
    else:
        return {}

    if len(selected) == 1:
        where_str = f"= '{selected[0]}'"
    else:
        where_str = f"in {selected}"

    image_str = "'image', COALESCE(images#>>'{medium, 0}',images#>>'{large, 0}')"

    query = f"""
            SELECT
                
            MIN(price) as min_price,
            MAX(price) as max_price,
            json_agg(pr.product_data) as products
            
            FROM product_specs ps

            INNER JOIN 
            (
                SELECT pr._id, price, json_build_object('uuid', uuid, 'name', pr.name, 'price', price, 'shop', shop_name, 'refurbished', pr.refurbished, {image_str}) as product_data, MIN(pa.price)
                FROM products pr
                
                INNER JOIN 
                    (
                        SELECT pa.product_id, pa.url, pa.code, pa.price, sh.shop_name, pa.deleted, pa.stock
                        FROM products_availabilities pa 

                        INNER JOIN 
                            (
                            SELECT sh._id, sh.name as shop_name
                            FROM shops sh 
                            ) sh ON sh._id = pa.shop_id

                        WHERE pa.deleted = {False} and pa.stock = {True} and pa.price > 0 AND pa.code > 0
                    ) pa ON pa.product_id = pr._id
                                        
                WHERE pr.deleted = {False}
                GROUP BY price, pr._id, pa.shop_name

            ) pr ON pr._id = ps.product_id

            WHERE ps.value {where_str}
            """

    with sql_connection() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(query)
            data = dict(cursor.fetchone())

    if not data.get("products", None):
        data["products"] = []
        return data

    data["min_price"] = int(math.floor(data["min_price"] / 100.0)) * 100
    data["max_price"] = int(math.ceil(data["max_price"] / 100.0)) * 100

    valid_messages.petition_completed(f"stock: {category}")
    return data


@apistock_routing_blueprint.route("/api/category/<string:category>", methods=["GET"])
def get_category_products(category):
    """
    Returns all the products matching the category.

    :param category: type of product
    :return: dictionary with a list of products and their specifications
    """
    if not category:
        return {}

    category = CATEGORIES.get(str(category), None)
    if not category:
        return {}

    image_str = "'image', COALESCE(images#>>'{medium, 0}',images#>>'{large, 0}')"

    additional_str = ""
    if category == "GPU":
        additional_str = """
                            MIN(substring(specs->>'Tamaño Memoria', '\d+')::int) as min_memory,
                            MAX(substring(specs->>'Tamaño Memoria', '\d+')::int) as max_memory,
                            """
    elif category == "Chassis":
        additional_str = """
                            MIN(substring(specs->>'Altura máxima CPU', '\d+')::int) as min_cpu,
                            MAX(substring(specs->>'Altura máxima CPU', '\d+')::int) as max_cpu,
                            MIN(substring(specs->>'Longitud máxima GPU', '\d+')::int) as min_gpu,
                            MAX(substring(specs->>'Longitud máxima GPU', '\d+')::int) as max_gpu,
                            """

    elif category == "CPU Cooler":
        additional_str = """
                            MIN(substring(specs->>'Altura (ventilador incluido)', '\d+')::int) as min_cpu,
                            MAX(substring(specs->>'Altura (ventilador incluido)', '\d+')::int) as max_cpu,
                            """
    elif category == "RAM":
        additional_str = """
                            MIN(substring(specs->>'Frecuencia Memoria', '\d+')::int) as min_freq,
                            MAX(substring(specs->>'Frecuencia Memoria', '\d+')::int) as max_freq,
                            """

    query = (
        """
        SELECT 

        MIN(COALESCE(pa.price, pa2.price)) as min_price,
        MAX(COALESCE(pa.price, pa2.price)) as max_price,
        """
        + additional_str
        + f"""
        json_agg(json_build_object('uuid', p.uuid, 'name', p.name, 'refurbished', p.refurbished, {image_str}, 'specs', ps.specs, 'shops', pa_sh.shops, 'price', COALESCE(pa.price, pa2.price), 'manufacturer', m.name, 'stock', COALESCE(pa.stock, pa2.stock))) as products
            
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
            SELECT product_id, json_agg(sh.name) AS shops
            FROM products_availabilities pa_sh
            LEFT JOIN shops sh on sh._id = pa_sh.shop_id
            GROUP BY 1
            HAVING MIN(pa_sh.price) > 0
            ) pa_sh on p._id = pa_sh.product_id

        LEFT JOIN (
            SELECT product_id, MIN(pa.price) AS price, MAX(pa.stock::int) AS stock
            FROM products_availabilities pa
			WHERE pa.stock = {True}
            GROUP BY 1
            HAVING MIN(pa.price) > 0
            ) pa ON p._id = pa.product_id
			
        LEFT JOIN (
            SELECT product_id, MIN(pa2.price) AS price, MAX(pa2.stock::int) AS stock
            FROM products_availabilities pa2
			WHERE pa2.stock = {False}
            GROUP BY 1
            HAVING MIN(pa2.price) > 0
            ) pa2 ON p._id = pa2.product_id

        WHERE c.name = '{category}' """
    )
    # Selecciono el precio mínimo de los productos sin stock (products_dict1) y con stock (products_dict2)

    with sql_connection() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(query)
            products_dict = dict(cursor.fetchone())

    products_dict["max_price"] = (
        int(math.ceil(products_dict["max_price"] / 100.0)) * 100
    )
    products_dict["min_price"] = (
        int(math.floor(products_dict["min_price"] / 100.0)) * 100
    )

    valid_messages.petition_completed(f"category: {category}")
    return products_dict


@apistock_routing_blueprint.route("/api/deals", methods=["GET"])
def deals():
    """
    Returns the best deals of Graphic Cards (NVIDIA and AMD)

    :return: a dict containing the best deals
    """
    gpu_specs = ()
    for key in SPECS_VALUES:
        value = SPECS_VALUES.get(key)
        if value not in gpu_specs:
            gpu_specs = (*gpu_specs, value)

    connection = sql_connection()
    image_str = "'image', COALESCE(images#>>'{medium, 0}',images#>>'{large, 0}')"

    query = f"""
            SELECT DISTINCT ON (ps.value)

            ps.value, pa.price,
            json_agg(json_build_object('uuid', p.uuid, 'name', p.name, {image_str}, 'price', pa.price)) as products
                            
            FROM products p
            LEFT JOIN categories c on p.category_id = c._id 
            LEFT JOIN product_specs ps on ps.product_id = p._id
            JOIN (
                SELECT product_id, MIN(pa.price) AS price
                FROM products_availabilities pa
                LEFT JOIN shops sh on sh._id = pa.shop_id
                WHERE pa.deleted = {False} AND pa.stock = {True} AND pa.price > 0 AND pa.code > 0
                GROUP BY 1
                ) pa on p._id = pa.product_id

            WHERE c.name = 'GPU' AND ps.spec_id = 3
            GROUP BY ps.value, pa.price
            """

    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(query)
    rows = cursor.fetchall()
    connection.close()

    data = {"NVIDIA": {}, "AMD": {}}
    models_added = {}
    nvidia_counter = -1
    amd_counter = -1
    saved_row = None
    gpu_exceptions = {"RTX 3060 Ti": False, "RX 7900 XTX": False}
    for row in rows:
        row_data = dict(row)
        # Base Models (Insensitive to TI or LHR)
        gpu_model = re.findall(
            "RTX \d+(?: Ti)?|RX \d+ XT[X]?|RX \d+", row_data["value"], re.IGNORECASE
        )
        if not gpu_model:
            continue
        gpu_model = gpu_model[0]

        simple_model = re.findall("RTX \d+|RX \d+", gpu_model, re.IGNORECASE)
        if not simple_model:
            continue
        simple_model = simple_model[0]

        manufacturer = "NVIDIA" if simple_model.find("RTX") != -1 else "AMD"
        gpu_number = int(re.findall("\d\d\d\d", simple_model, flags=re.IGNORECASE)[0])

        result = models_added.get(gpu_model, False)
        if result and row_data["price"] > result:
            continue

        if saved_row and gpu_exceptions.get(gpu_model, True):
            if (
                saved_row["manufacturer"] == manufacturer
                and gpu_number >= saved_row["gpu_number"]
                and row_data["price"] < saved_row["price"] * 1.1
            ):
                nvidia_counter = (
                    nvidia_counter - 1 if manufacturer == "NVIDIA" else nvidia_counter
                )
                amd_counter = amd_counter - 1 if manufacturer == "AMD" else amd_counter
                data[manufacturer].pop(saved_row["gpu_model"])
            elif (
                saved_row["manufacturer"] == manufacturer
                and saved_row["gpu_number"] >= gpu_number
                and saved_row["price"] < row_data["price"]
            ):
                continue

        row_data["gpu_model"] = gpu_model
        row_data["gpu_number"] = gpu_number
        row_data["manufacturer"] = manufacturer
        saved_row = row_data

        models_added[gpu_model] = row_data["price"]

        data[manufacturer][gpu_model] = row_data["products"][0]
        nvidia_counter = (
            nvidia_counter + 1 if manufacturer == "NVIDIA" else nvidia_counter
        )
        amd_counter = amd_counter + 1 if manufacturer == "AMD" else amd_counter
        continue

    final_data = {"NVIDIA": [], "AMD": []}
    for manufacturer in data:
        for gpu_model in data[manufacturer]:
            final_data[manufacturer].append(data[manufacturer][gpu_model])

    valid_messages.petition_completed("deals")
    return final_data
