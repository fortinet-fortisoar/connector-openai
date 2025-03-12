"""
Copyright start
MIT License
Copyright (c) 2025 Fortinet Inc
Copyright end
"""
import json
import openai
import arrow
import re
from bs4 import BeautifulSoup
from jsonschema import validate
from connectors.core.connector import get_logger, ConnectorError
from .constants import *
import tiktoken
import requests
import httpx
import os
from pathlib import Path
from connectors.cyops_utilities.files import save_file_in_env, download_file_from_cyops


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
    return re.sub(r'@\w+\s', '', tag_stripped)


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
    openai_args = {"api_key": config.get('apiKey')}
    api_type = config.get("api_type")
    https_proxy = os.environ.get('HTTPS_PROXY')
    no_proxy = os.environ.get('NO_PROXY', 'localhost')
    base_url = 'api.openai.com'
    if api_type:
        openai.api_type = "azure"
        openai.base_url = config.get("api_base")
        openai.api_version = config.get("api_version")
        openai_args.update({
            "base_url": config.get("api_base"),
            "api_type": "azure",
            "api_version": config.get("api_version")
        })
        base_url = config.get("api_base")
    if config.get('project'):
        openai.project = config.get('project')
    if config.get('organization'):
        openai.organization = config.get('organization')
    verify_ssl = config.get('verify_ssl')
    if https_proxy and base_url not in no_proxy:
        openai.http_client = httpx.Client(proxy=https_proxy, verify=verify_ssl)
    else:
        openai.http_client = httpx.Client(verify=verify_ssl)
    openai_args['http_client'] = openai.http_client
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
    other_fields = params.get('other_fields', {})
    if config.get("deployment_id"):
        openai_args.update({"deployment_id": config.get("deployment_id")})
    if temperature:
        openai_args.update({"temperature": temperature})
    if max_tokens:
        openai_args.update({"max_tokens": max_tokens})
    if top_p:
        openai_args.update({"top_p": top_p})
    if other_fields:
        openai_args.update(other_fields)
    openai_args['timeout'] = params.get('timeout') if params.get('timeout') else 600
    return openai.chat.completions.create(**openai_args).model_dump()


def list_models(config, params):
    __init_openai(config)
    return openai.models.list().model_dump()


def get_usage(config, params):
    date = arrow.get(params.get('date', arrow.now().int_timestamp)).format('YYYY-MM-DD')
    query_param = {'date': date}
    api_type = config.get("api_type")
    if api_type:
        base_url = config.get("api_base").strip("/")
        if base_url.startswith('http') or base_url.startswith('https'):
            url = "{0}/openai/deployments/{1}/usage".format(base_url, config.get('deployment_id'))
        else:
            url = "https://{0}/openai/deployments/{1}/usage".format(base_url, config.get('deployment_id'))
        query_param["api-version"] = config.get('api_version')
    else:
        url = USAGE_URL
    response = make_rest_call(config, url=url, params=query_param)
    return response


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
        if hasattr(err, 'code'):
            if err.code == 'invalid_api_key':
                logger.exception("Incorrect API key provided. You can find your API key at https://platform.openai.com/account/api-keys")
                raise ConnectorError("Incorrect API key provided. You can find your API key at https://platform.openai.com/account/api-keys",)
            if hasattr(err, 'body') and err.body.get("message"):
                logger.exception(err.body.get("message"))
                raise ConnectorError(err.body.get("message"))
        logger.exception('{0}'.format(err))
        if hasattr(err, 'error'):
            raise ConnectorError(err.error.get("message"))
        raise ConnectorError('{0}'.format(err))


def make_rest_call(config, url, method='GET', **kwargs):
    try:
        headers = {
            "Authorization": "Bearer {0}".format(config.get('apiKey'))
        }
        try:
            from connectors.debug_utils.curl_script import make_curl
            debug_headers = headers.copy() if headers else None
            debug_headers["Authorization"] = "*****************"
            make_curl(method=method, url=url, headers=debug_headers, **kwargs)
        except Exception as err:
            logger.info("Error: {0}".format(err))
        response = requests.request(method=method, url=url, headers=headers, **kwargs)
        if response.ok:
            return response.json()
        else:
            try:
                logger.error("Error: {0}".format(response.json()))
                raise ConnectorError('Error: {0}'.format(response.json()))
            except Exception as error:
                logger.exception('Error occurred: {0}'.format(str(error)))
                raise ConnectorError('{0}'.format(response.text if response.text else str(response)))
    except requests.exceptions.SSLError as e:
        logger.exception('{0}'.format(e))
        raise ConnectorError('{0}'.format(e))
    except requests.exceptions.ConnectionError as e:
        logger.exception('{0}'.format(e))
        raise ConnectorError('{0}'.format(e))
    except Exception as e:
        logger.error('{0}'.format(e))
        raise ConnectorError('{0}'.format(e))


def build_payload(params: dict):
    data = {}
    for k, v in params.items():
        if isinstance(v, (int, bool)):
            data[k] = v
        elif v:
            if isinstance(v, dict):
                data[k] = build_payload(v)
            elif isinstance(v, (list, tuple)):
                data[k] = list(v)
            else:
                data[k] = v
            if k == 'metadata':
                if v.get('version'):
                    data[k]['version'] = str(v['version'])
                if isinstance(v.get('modified'), bool):
                    data[k]['modified'] = str(v['modified'])
    return data


def create_assistant(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.assistants.create(**payload).model_dump()


def list_assistants(config, params):
    __init_openai(config)
    params['order'] = SORT_ORDER_MAPPING.get(params.get('order'))
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    limit = params.get('limit')
    # Maximum limit supported by API is 100
    if limit and isinstance(limit, int) and limit > 100:
        payload['limit'] = 100
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.assistants.list(**payload).model_dump()


def get_assistant(config, params):
    __init_openai(config)
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.assistants.retrieve(assistant_id=params.get('assistant_id'), timeout=600).model_dump()


def delete_assistant(config, params):
    __init_openai(config)
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.assistants.delete(assistant_id=params.get('assistant_id'), timeout=600).model_dump()


def update_assistant(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.assistants.update(**payload).model_dump()


def get_thread(config, params):
    __init_openai(config)
    params['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.retrieve(**params).model_dump()


def delete_thread(config, params):
    __init_openai(config)
    params['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.delete(**params).model_dump()


def create_thread(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.create(**payload).model_dump()


def update_thread(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.update(**payload).model_dump()


def create_thread_message(config, params):
    __init_openai(config)
    params['role'] = params.get('role', '').lower()
    contents = params.get('content')
    if isinstance(contents, list):
        for content in contents:
            c_text, c_type = content.get('text'), content.get('type')
            if isinstance(content, dict) and c_type == 'text' and c_text and isinstance(c_text, int):
                content['text'] = str(c_text)
    elif not isinstance(contents, str):
        params['content'] = str(contents)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.messages.create(**payload).model_dump()


def list_thread_messages(config, params):
    __init_openai(config)
    params['order'] = SORT_ORDER_MAPPING.get(params.get('order'))
    limit = params.get('limit')
    # Maximum limit supported by API is 100
    if limit and isinstance(limit, int) and limit > 100:
        params['limit'] = 100
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.messages.list(**payload).model_dump()


def delete_thread_message(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.messages.delete(**payload).model_dump()


def get_thread_message(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.messages.retrieve(**payload).model_dump()


def update_thread_message(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.messages.update(**payload).model_dump()


def list_runs(config, params):
    __init_openai(config)
    params['order'] = SORT_ORDER_MAPPING.get(params.get('order'))
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    limit = params.get('limit')
    # Maximum limit supported by API is 100
    if limit and isinstance(limit, int) and limit > 100:
        payload['limit'] = 100
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.runs.list(**payload).model_dump()


def get_run(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.runs.retrieve(**payload).model_dump()


def create_run(config, params):
    __init_openai(config)
    payload = build_payload(params)
    other_fields = params.pop('other_fields', {})
    if other_fields:
        payload.update(other_fields)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.runs.create(**payload).model_dump()


def update_run(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.runs.update(**payload).model_dump()


def cancel_run(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.runs.cancel(**payload).model_dump()


def create_thread_and_run(config, params):
    __init_openai(config)
    payload = build_payload(params)
    other_fields = params.pop('other_fields', {})
    if other_fields:
        payload.update(other_fields)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.create_and_run(**payload).model_dump()


def submit_tool_outputs_to_run(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.runs.submit_tool_outputs(**payload).model_dump()


def list_run_steps(config, params):
    __init_openai(config)
    params['order'] = SORT_ORDER_MAPPING.get(params.get('order'))
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    limit = params.get('limit')
    # Maximum limit supported by API is 100
    if limit and isinstance(limit, int) and limit > 100:
        payload['limit'] = 100
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.runs.steps.list(**payload).model_dump()


def get_run_step(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.threads.runs.steps.retrieve(**payload).model_dump()


def create_vector_store(config, params):
    __init_openai(config)
    handle_comma_separated_input(params, ['file_ids'])
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.vector_stores.create(**payload).model_dump()


def get_vector_store(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.vector_stores.retrieve(**payload).model_dump()


def create_vector_store_file(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.vector_stores.files.create(**payload).model_dump()


def create_vector_store_file_batch(config, params):
    __init_openai(config)
    file_ids = params.get('file_ids')
    if isinstance(file_ids, (tuple, list)):
        params['file_ids'] = list(file_ids)
    elif isinstance(file_ids, str):
        params['file_ids'] = [file_id.strip() if isinstance(file_id, str) else file_id for file_id in file_ids.split(",")]
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.vector_stores.file_batches.create(**payload).model_dump()


def get_vector_store_file_batch(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.vector_stores.file_batches.retrieve(**payload).model_dump()


def cancel_vector_store_file_batch(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.beta.vector_stores.file_batches.cancel(**payload).model_dump()


def create_speech(config, params, *args, **kwargs):
    __init_openai(config)
    env = kwargs.get('env', {})
    file_path = params.pop('file_path')
    _list = file_path.split('.')
    file_format = params.get('response_format') if params.get('response_format') else 'mp3'
    if len(_list) == 1:
        file_path += '.{0}'.format(file_format)
    elif _list[-1] not in ["mp3", "opus", "aac", "flac", "wav", "pcm"]:
        logger.warning('File extension is not in supported format. Supported formats: "mp3", "opus", "aac", "flac", "wav", "pcm"')
    if file_path.startswith('/tmp/'):
        speech_file_path = Path(file_path)
    else:
        speech_file_path = Path("/tmp") / file_path
    params['model'] = params.get('model', '').lower()
    params['voice'] = params.get('voice', '').lower()
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    openai.audio.speech.create(**payload).stream_to_file(speech_file_path)
    return_path = str(speech_file_path)
    save_file_in_env(env, return_path)
    return {'path': return_path}


def get_file_input(file_payload, env={}):
    if isinstance(file_payload, dict) and file_payload.get('@type') == "File":
        url = file_payload.get('@id')
        response = download_file_from_cyops(url)
        file_path = response.get('cyops_file_path')
        filename = response.get('filename')
    else:
        logger.warning("File path is provided.")
        file_path = file_payload
        filename = Path(file_payload).name
    if not file_path.startswith('/tmp/'):
        file_path = '/tmp/{0}'.format(file_path)
    with open(file_path, 'rb') as file:
        file_content = file.read()
    save_file_in_env(env, file_path)
    return filename, file_content


def create_transcription(config, params, *args, **kwargs):
    __init_openai(config)
    env = kwargs.get('env', {})
    params['voice'] = params.get('voice', '').lower()
    timestamp_granularities = [granularity.lower() for granularity in params.get('timestamp_granularities')]
    if timestamp_granularities:
        params['response_format'] = 'verbose_json'
    payload = build_payload(params)
    payload['timestamp_granularities'] = timestamp_granularities
    payload['file'] = get_file_input(params.get('file'), env)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    return openai.audio.transcriptions.create(**payload).model_dump()


def create_translation(config, params, *args, **kwargs):
    __init_openai(config)
    env = kwargs.get('env', {})
    payload = build_payload(params)
    payload['file'] = get_file_input(params.get('file'), env)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    return openai.audio.translations.create(**payload).model_dump()


def get_file(config, params):
    __init_openai(config)
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.files.retrieve(**payload).model_dump()


def list_files(config, params):
    __init_openai(config)
    params['purpose'] = FILE_PURPOSE_MAPPING.get(params.get('purpose'))
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.files.list(**payload).model_dump()


def upload_file(config, params, *args, **kwargs):
    __init_openai(config)
    env = kwargs.get('env', {})
    params['purpose'] = FILE_PURPOSE_MAPPING.get(params.get('purpose'), params.get('purpose'))
    payload = build_payload(params)
    payload['timeout'] = params.get('timeout') if params.get('timeout') else 600
    payload['file'] = get_file_input(params.get('file'), env)
    client = openai.OpenAI(api_key=openai.api_key, organization=openai.organization, project=openai.project, http_client=openai.http_client)
    return client.files.create(**payload).model_dump()


def handle_comma_separated_input(params, keys=[]):
    for key in keys:
        input_value = params.get(key)
        if isinstance(input_value, str):
            params[key] = [i.strip() for i in input_value.split(',')]
        elif isinstance(input_value, tuple):
            params[key] = list(input_value)

