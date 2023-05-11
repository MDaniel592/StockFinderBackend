import logging
import sqlite3 as db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

DB_PATH = "./verification_db/verification_db.db"


def sql_connection_verification_db():
    try:
        con = db.connect(DB_PATH, check_same_thread=False)
        logger.info("Connection established")
        return con
    except db.Error as e:
        logger.warning(e)
        return None
