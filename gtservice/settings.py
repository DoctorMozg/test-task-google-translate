import logging
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING")
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", 10))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", 10))

LOG_LEVEL = int(os.environ.get("LOG_LEVEL", logging.INFO))
