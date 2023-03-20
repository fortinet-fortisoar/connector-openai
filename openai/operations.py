import openai
from connectors.core.connector import get_logger, ConnectorError
from .constants import LOGGER_NAME
logger = get_logger(LOGGER_NAME)


def chat_completions(config, params):
    openai.api_key = config.get('apiKey')
    model = params.get('model', 'gpt-3.5-turbo')
    message = params.get('message')
    temperature = params.get('temperature')
    top_p = params.get('top_p')
    max_tokens = params.get('max_tokens')
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

    if max_tokens and temperature and top_p:
        return openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature,
                                                        top_p=top_p, max_tokens=max_tokens)
    elif max_tokens and temperature:
        return openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    elif max_tokens and top_p:
        return openai.ChatCompletion.create(model=model, messages=messages, top_p=top_p, max_tokens=max_tokens)
    elif max_tokens:
        return openai.ChatCompletion.create(model=model, messages=messages, max_tokens=max_tokens)
    elif temperature and top_p:
        return openai.ChatCompletion.create(model=model, messages=messages, top_p=top_p, temperature=temperature)
    elif temperature:
        return openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature)
    elif top_p:
        return openai.ChatCompletion.create(model=model, messages=messages, top_p=top_p)
    else:
        return openai.ChatCompletion.create(model=model, messages=messages)


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
