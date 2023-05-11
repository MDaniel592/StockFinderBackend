import logging
import sqlite3
from datetime import datetime, timedelta

import utils.error_messages as errors
import verification_db.db_manager as verification_manager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True


def set_verification_code(code, account_to_verify):
    connection = verification_manager.sql_connection_verification_db()
    if not connection:
        return (errors.DB_CONNECTION_ERROR, False)
    cursor = connection.cursor()
    try:
        expiration_date = datetime.utcnow() + timedelta(minutes=15)
        cursor.execute(
            f"INSERT INTO verification_codes(account_to_verify, verification_code, expiration_date) VALUES (:account_to_verify, :verification_code, :expiration_date) ON CONFLICT(account_to_verify) DO UPDATE SET verification_code = :verification_code, expiration_date = :expiration_date",
            {
                "account_to_verify": account_to_verify,
                "verification_code": code,
                "expiration_date": expiration_date.timestamp(),
            },
        )
        connection.commit()

        cursor.close()
        connection.close()

        return ("", True)
    except Exception as e:
        print(e)
        cursor.close()
        connection.close()
        return (errors.DB_OPERATION_ERROR, False)


def verify_code(code, account_to_verify):
    connection = verification_manager.sql_connection_verification_db()
    connection.row_factory = sqlite3.Row

    if not connection:
        return (errors.DB_CONNECTION_ERROR, False)
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT * from verification_codes WHERE account_to_verify = ? AND verification_code = ?",
            (account_to_verify, code),
        )
        data = cursor.fetchone()
        print(data)
        if data == None:
            cursor.close()
            connection.close()
            return (errors.DB_VERIFICATION_CODE_WRONG, False)
        time = datetime.utcnow()
        if datetime.utcnow().timestamp() > data["expiration_date"]:
            cursor.close()
            connection.close()
            return (errors.DB_VERIFICATION_TIMESTAMP_LATE, False)
        cursor.close()
        connection.close()
        return ("", True)
    except Exception as e:
        print(e)
        cursor.close()
        connection.close()
        return (errors.DB_OPERATION_ERROR, False)
