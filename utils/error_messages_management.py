import logging
from datetime import datetime

import utils.error_messages as errors
from utils.common import is_spam

# enabling logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

# Gestor de errores
def generate_error_data(error_text, user_ip=None):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {"status": "error", "error": error_text}
    logger.error(f"{current_time} - IP: {user_ip} - error: {error_text}")

    return data


def check_user_spam(user_ip):
    result, banned_time = is_spam(user_ip=user_ip)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = {}
    if result and user_ip != "127.0.0.1":
        data["status"] = "error"
        data["error"] = errors.SPAM_DETECTED
        logger.error(f"{current_time} - IP: {user_ip} - error: {data['error']} - Banned until: {banned_time}")
    else:
        data["status"] = "ok"
        data["ok"] = "Actividad correcta"
        logger.info(f"{current_time} - IP: {user_ip} - {data['ok']}")

    return result, data
