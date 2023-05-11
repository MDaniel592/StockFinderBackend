import logging

# enabling logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True


def petition_completed(method):
    return logger.info(f"Petición completada con éxito - {method}")


def valid_login(email):
    return logger.info(f"Usuario: {email} ha iniciado sesión correctamente")


def password_reset_succeded(email, telegram_id=None):
    if telegram_id:
        return logger.info(f"Se ha cambiado la contraseña correctamente: {email} - {telegram_id}")
    return logger.info(f"Se ha cambiado la contraseña correctamente: {email}")


def seding_code(telegram_id=None, email=None):
    if telegram_id:
        return logger.info(f"Se le va a enviar el código de Telegram al usuario con ID: {telegram_id}")
    return logger.info(f"Se le va a enviar el código de correo a: {email}")


def correct_code(email, email_code):
    return logger.info(f"Se ha introducido un código correcto: {email} - {email_code}")


def register_succeded(email, telegram_id=None):
    return logger.info(f"Se ha registrado correctamente: {email} - {telegram_id}")
