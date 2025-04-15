"""
Copyright start
MIT License
Copyright (c) 2025 Fortinet Inc
Copyright end
"""
from connectors.core.connector import get_logger, ConnectorError

from .constants import LOGGER_NAME, NON_FOUND_ERROR_MESSAGE
from openai import NotFoundError

logger = get_logger(LOGGER_NAME)


def handle_exception(err: Exception):
    """
    Standard exception handler that logs and raises ConnectorError with appropriate messages.
    """
    if isinstance(err, NotFoundError):
        handle_not_found_error(err=err)
    if hasattr(err, 'error') and err.error.get("message"):
        error_message = f'{err.error.get("message")}'
        logger.exception(error_message)
        raise ConnectorError(error_message)
    logger.exception(err)
    raise ConnectorError(err)


def handle_not_found_error(err: Exception):
    """
    Handles NotFoundError with a contextualized suggestion.
    """
    error_message = NON_FOUND_ERROR_MESSAGE
    logger.exception(f'Error: {err} \n Message: {error_message}')
    raise ConnectorError(error_message)
