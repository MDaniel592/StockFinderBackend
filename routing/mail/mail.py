import logging
import os
import random
import string

import yagmail

SMTP_SERVER = os.environ.get("MAIL_SMTP_SERVER")
SMTP_PORT = os.environ.get("MAIL_SMTP_PORT")
SENDER_EMAIL = os.environ.get("MAIL_SENDER_EMAIL")
USERNAME = os.environ.get("MAIL_USERNAME")
PASSWORD = os.environ.get("MAIL_PASSWORD")
CODE_LENGTH = 6

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def send_mail(receiver_email, subject, content):
    try:
        yag = yagmail.SMTP(USERNAME, PASSWORD)
        yag.send(receiver_email, subject, content)
        return True

    except Exception as e:
        print(e)
        return False


def send_code(receiver_email):
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=CODE_LENGTH))
    message = [f"Para completar el registro introduce en la web el siguiente código: {code}"]

    result = send_mail(receiver_email, "Clave de validación - StockTracker", message)

    logger.warning(f"Código de email enviado a: {receiver_email} - Code: {code}")
    return code if result else False
