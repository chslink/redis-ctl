import os
import logging
import tempfile
from werkzeug.utils import import_string

APP_CLASS = os.getenv('APP_CLASS', 'app.RedisCtl')
SERVER_PORT = int(os.getenv('SERVER_PORT', 5000))

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_USERNAME = os.getenv('MYSQL_USERNAME', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'redisctl')
MYSQL_CHARSET  = os.getenv('MYSQL_CHARSET', 'utf8')

LOG_LEVEL = getattr(logging, os.getenv('LOG_LEVEL', 'info').upper())
LOG_FILE = os.getenv('LOG_FILE', '')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(levelname)s:%(asctime)s:%(message)s')

DEBUG = int(os.getenv('DEBUG', 0))
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 10))
PERMDIR = os.getenv('PERMDIR', tempfile.gettempdir())
NODE_MAX_MEM = int(os.getenv('NODE_MAX_MEM', 2048 * 1000 * 1000))
NODES_EACH_THREAD = int(os.getenv('NODES_EACH_THREAD', 10))
REDIS_CONNECT_TIMEOUT = int(os.getenv('REDIS_CONNECT_TIMEOUT', 5))
MICRO_PLAN_MEM = int(os.getenv('MICRO_PLAN_MEM', 108 * 1000 * 1000))

# ========================= #
# Thirdparty configurations #
# ========================= #

OPEN_FALCON = {
    'host_query': os.getenv('OPEN_FALCON_HOST_QUERY', ''),
    'host_write': os.getenv('OPEN_FALCON_HOST_WRITE', ''),
    'port_query': int(os.getenv('OPEN_FALCON_PORT_QUERY', 9966)),
    'port_write': int(os.getenv('OPEN_FALCON_PORT_WRITE', 8433)),
    'db': os.getenv('OPEN_FALCON_DATABASE', 'redisctlstats'),
    'interval': int(os.getenv('OPEN_FALCON_ANTICIPATED_INTERVAL', 30)),
}

try:
    from override_config import *
except ImportError:
    pass

App = import_string(APP_CLASS)
