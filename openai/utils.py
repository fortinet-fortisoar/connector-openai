"""
Copyright start
MIT License
Copyright (c) 2025 Fortinet Inc
Copyright end
"""
import json

import requests
from integrations.crudhub import make_request
from connectors.core.connector import get_logger
from .constants import LOGGER_NAME

logger = get_logger(LOGGER_NAME)


def execute_connector_action(config_id, connector_name, operation, payload, version='1.0.0'):
    input_data = {
        "connector": connector_name,
        "version": version,
        "params": payload if payload else {},
        "operation": operation if operation else 'get_credential',
        "config": config_id if config_id else 'get_default_config'
    }
    from connectors.views import ConnectorExecute
    try:
        response, is_binary = ConnectorExecute.execute_connector_operation(input_data)
        if response.get('status') == "Success":
            return response
        message = f'Error occurred in executing connector action: {response.get("message")}'
        logger.error(message)
        raise Exception(message)
    except Connector.DoesNotExist:
        message = f'Connector {connector_name} not found.'
        logger.error(message)
        raise Exception(message)
    except Exception as error:
        raise Exception(f'Error occurred in executing connector action: {error}')
