# from sys import api_version
# from urllib import response
import openai
import arrow
import re
from openai.api_requestor import APIRequestor
from requests_toolbelt.utils import dump
from bs4 import BeautifulSoup
from jsonschema import validate
from connectors.core.connector import get_logger, ConnectorError
from .constants import *
import tiktoken

logger = get_logger(LOGGER_NAME)


# logger.setLevel(logging.DEBUG)


def _validate_json_schema(_instance, _schema):
    try:
        validate(instance=_instance, schema=_schema)
        return _instance
    except Exception as err:
        logger.error("Error: {0} {1}".format(SCHEMA_ERROR, err))
        raise ConnectorError("Error: {0} {1}".format(SCHEMA_ERROR, err))


def _remove_html_tags(text):
    tag_stripped = BeautifulSoup(text, "html.parser").text
    return re.sub(r'#\w+\s', '', tag_stripped)


def _build_messages(params):
    ''' builds the message list based on the chat type '''
    operation = params.get('operation')
    messages = [
        {
            "role": "system",
            "content": "Be concise and helpful assistant."
        }
    ]
    if operation == 'chat_completions':
        messages.append({"role": "user", "content": _remove_html_tags(params.get('message'))})
    elif operation == 'chat_conversation':
        replies = _validate_json_schema(params.get('messages'), MESSAGES_SCHEMA)
        for message in replies:
            message.update({'content': _remove_html_tags(message['content'])})
        messages = messages + replies
    return messages


def __init_openai(config):
    openai.api_key = config.get('apiKey')
    openai_args = {"key": config.get('apiKey')}
    api_type = config.get("api_type")
    if api_type:
        openai.api_type = "azure"
        openai.api_base = config.get("api_base")
        openai.api_version = config.get("api_version")
        openai_args.update({
            "api_base": config.get("api_base"),
            "api_type": "azure",
            "api_version": config.get("api_version")
        })
    return openai_args


def chat_completions(config, params):
    __init_openai(config)
    model = params.get('model')
    if not model:
        model = 'gpt-3.5-turbo'
    temperature = params.get('temperature')
    top_p = params.get('top_p')
    max_tokens = params.get('max_tokens')
    messages = _build_messages(params)
    logger.debug("Messages: {}".format(messages))
    openai_args = {"model": model, "messages": messages}
    if config.get("deployment_id"):
        openai_args.update({"deployment_id": config.get("deployment_id")})
    if temperature:
        openai_args.update({"temperature": temperature})
    if max_tokens:
        openai_args.update({"max_tokens": max_tokens})
    if top_p:
        openai_args.update({"top_p": top_p})
    return openai.ChatCompletion.create(**openai_args)


def list_models(config, params):
    __init_openai(config)
    return openai.Model.list()


def get_usage(config, params):
    date = arrow.get(params.get('date', arrow.now().int_timestamp)).format('YYYY-MM-DD')
    request_args = __init_openai(config)
    requestor = APIRequestor(**request_args)
    response = requestor.request_raw('get', '/usage', params={'date': date})
    logger.debug('Request \n:{}'.format(dump.dump_all(response).decode('utf-8')))
    return response.json()


def count_tokens(config, params):
    """Returns the number of tokens in a text string."""
    input_text = params.get("input_text")
    model = params.get("model")
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(input_text))
    return {"tokens": num_tokens}


def check(config):
    try:
        list_models(config, {})
        return True
    except Exception as err:
        if err.error:
            logger.error('{0}'.format(err))
            raise ConnectorError(err.error.get("message"))
        raise ConnectorError('{0}'.format(err))
