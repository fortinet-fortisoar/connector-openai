from connectors.core.connector import Connector
from connectors.core.connector import get_logger, ConnectorError
from .builtins import *
from .constants import LOGGER_NAME
from .operations import check
logger = get_logger(LOGGER_NAME)


class Openai(Connector):

    def execute(self, config, operation, params, *args, **kwargs):
        return supported_operations.get(operation)(config, params)

    def check_health(self, config=None, *args, **kwargs):
        return check(config)
