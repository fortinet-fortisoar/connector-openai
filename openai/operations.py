import openai
from connectors.core.connector import get_logger, ConnectorError
from .constants import LOGGER_NAME
logger = get_logger(LOGGER_NAME)


def chat_completions(config, params):
    openai.api_key = config.get('apiKey')
    model = params.get('model', 'gpt-3.5-turbo')
    message = params.get('message')
    messages = [
        {
            "role": "system",
            "content": "Be concise and helpful assistant."
        },
        {
            "role": "user",
            "content": message
        }
    ]
    response = openai.ChatCompletion.create(model=model, messages=messages)
    return response


def check(config):
    try:
        openai.api_key = config.get('apiKey')
        result = openai.Model.list()
        return True
    except Exception as err:
        if err.error:
            logger.error('{0}'.format(err))
            raise ConnectorError(err.error.get("message"))
        raise ConnectorError('{0}'.format(err))
