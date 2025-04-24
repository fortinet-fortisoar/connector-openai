"""
Copyright start
MIT License
Copyright (c) 2025 Fortinet Inc
Copyright end
"""
from connectors.core.connector import get_logger, ConnectorError
from openai import NotFoundError, BadRequestError

from .constants import *

logger = get_logger(LOGGER_NAME)


def handle_exception(err: Exception):
    """
    Standard exception handler that logs and raises ConnectorError with appropriate messages.
    """
    error_message = None

    if isinstance(err, NotFoundError):
        error_message = NON_FOUND_ERROR_MESSAGE
    elif isinstance(err, BadRequestError):
        error_message = BAD_REQUEST_ERROR_MESSAGE
    elif hasattr(err, 'error') and err.error.get("message"):
        error_message = str(err.error.get("message"))

    logger.exception(f'Error: {err} \n Message: {error_message}')
    raise ConnectorError(error_message)
