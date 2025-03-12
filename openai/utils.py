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


def execute_connector_action(config_id, connector_name, operation, payload):
    try:
        url = '/api/integration/execute/?format=json'
        method = 'POST'
        payload = {
            "connector": connector_name,
            "version": "3.0.0",
            "config": config_id,
            "operation": operation,
            "params": payload,
            "audit": False
        }
        return make_request(url, method, body=payload)
    except requests.exceptions.HTTPError as http_err:
        logger.error(f'HTTP error occurred while executing connector action: {http_err}')
        response_content = http_err.response.text
        logger.error(f'Response content: {json.loads(response_content).get("message")}')
        raise Exception(json.loads(response_content).get("message"))
    except Exception as error:
        raise Exception(f'Error occurred in executing connector action: {error}')
