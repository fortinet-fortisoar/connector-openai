from sys import api_version
from urllib import response
import openai
import logging
import arrow
import re
import json
import requests
from bs4 import BeautifulSoup
from jsonschema import validate
from integrations.crudhub import maybe_json_or_raise
from connectors.core.connector import get_logger, ConnectorError
from .constants import *
logger = get_logger(LOGGER_NAME)
#logger.setLevel(logging.DEBUG) # Uncomment to enable local debug

def _validate_json_schema(_instance, _schema):
    try:
        validate(instance=_instance, schema=_schema)
        return _instance
    except Exception as err:
        logger.error("Error: {0} {1}".format(SCHEMA_ERROR,err))
        raise ConnectorError("Error: {0} {1}".format(SCHEMA_ERROR,err))
    

def _remove_html_tags(text):
    tag_stripped = BeautifulSoup(text, "html.parser").text
    return re.sub(r'#\w+\s','',tag_stripped) 


def _build_messages(params):
    ''' builds the message list based on the chat type '''
    chat_type = params.get('chat_type')    
    messages = [
        {
            "role": "system",
            "content": "Be concise and helpful assistant."
        }
    ]
    if chat_type == 'Question':
        messages.append({"role": "user","content": _remove_html_tags(params.get('message'))})
    elif chat_type == 'Conversation':
        replies =_validate_json_schema(params.get('messages'), MESSAGES_SCHEMA)
        for message in replies:
            message.update({'content':_remove_html_tags(message['content'])})
        messages = messages + replies
    return messages


def chat_completions(config, params):
    openai.api_key = config.get('apiKey')
    model = params.get('model')
    if not model:
        model = 'gpt-3.5-turbo'
    temperature = params.get('temperature')
    top_p = params.get('top_p')
    max_tokens = params.get('max_tokens')
    messages = _build_messages(params)
    logger.debug("Messages: {}".format(messages))

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

def list_models(config, params):
    openai.api_key = config.get('apiKey')
    return openai.Model.list()


def get_usage(config, params):
    headers = {'Authorization':'Bearer ' + config.get('apiKey')}
    date = arrow.get(params.get('date',arrow.now().int_timestamp)).format('YYYY-MM-DD')
    url = '{0}/{1}/usage'.format(BASE_URL, API_VERSION)
    headers = {'Authorization':'Bearer ' + config.get('apiKey')}
    logger.debug('Fetching usage report at" {0} on: {1}'.format(url,date))
    response = requests.request('get', url, params={'date':date}, headers=headers)
    if response.status_code == 200:
        response_json = json.loads(response.content)
        return response_json
    else:
        logger.error('Error fetching token usage: {0}'.format(response.content))
        raise ConnectorError('Error fetching token usage: {0}'.format(response.content))
    
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
