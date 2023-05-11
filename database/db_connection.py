import os
import socket

import psycopg2
import psycopg2.extras

HOSTNAME = os.environ.get("HOSTNAME", False)
DATABASE = os.environ.get("POSGRESQL_DATABASE")

LOCAL_USER = os.environ.get("POSGRESQL_LOCAL_USER")
LOCAL_USER_PASSWORD = os.environ.get("POSGRESQL_LOCAL_USER_PASSWORD")
LOCAL_URL = os.environ.get("POSGRESQL_LOCAL_URL")
LOCAL_PORT = os.environ.get("POSGRESQL_LOCAL_PORT")

REMOTE_USER = os.environ.get("POSGRESQL_REMOTE_USER")
REMOTE_USER_PASSWORD = os.environ.get("POSGRESQL_REMOTE_USER_PASSWORD")
REMOTE_URL = os.environ.get("POSGRESQL_REMOTE_URL")
REMOTE_PORT = os.environ.get("POSGRESQL_REMOTE_PORT")


def sql_connection():
    if HOSTNAME:
        # Localhost / Docker
        connection = psycopg2.connect(user=LOCAL_USER, password=LOCAL_USER_PASSWORD, host=LOCAL_URL, port=LOCAL_PORT, database=DATABASE)
    else:
        # Remote Host
        connection = psycopg2.connect(user=REMOTE_USER, password=REMOTE_USER_PASSWORD, host=REMOTE_URL, port=REMOTE_PORT, database=DATABASE)

    return connection
