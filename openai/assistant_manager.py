"""
Copyright start
MIT License
Copyright (c) 2025 Fortinet Inc
Copyright end
"""

from .assistant_event_handler import EventHandler
from .operations import _init_openai, create_thread_message
from .constants import *
from connectors.core.connector import get_logger

logger = get_logger(LOGGER_NAME)


class AssistantManager:

    def __init__(self, config, params):
        self.config = config
        self.params = params
        self.message_detail = {}
        self.tool_choice = "auto"
        if 'tool_choice' in self.params:
            self.tool_choice = self.params['tool_choice']

    def _prepare_attachments(self):
        attachments = []
        attachment_tool = ATTACHMENT_TOOLS.get(self.params.get('tool'), self.params.get('tools', "file_search"))

        file_ids = self.params.get('file_ids').split(",")
        for file_id in file_ids:
            attachments.append({"file_id": file_id.strip(), "tools": [{"type": attachment_tool}]})
        return attachments

    def get_llm_response(self):
        payload = {'thread_id': self.params['thread_id'], 'role': self.params['role'],
                   'content': self.params['content']}
        if self.params.get('file_ids'):
            payload.update({'attachments': self._prepare_attachments()})
        self.message_detail = create_thread_message(config=self.config, params=payload)
        assistant_response = self.run_assistant()
        return assistant_response

    def run_assistant(self, instructions=""):
        client = _init_openai(self.config)
        event_handler = EventHandler(config=self.config, params=self.params,
                                     last_message_id=self.message_detail.get("id"))
        response_format = self.params.get('response_format') or None
        if response_format:
            logger.info(f'Response format: {response_format}')
        with client.beta.threads.runs.stream(
                thread_id=self.params['thread_id'],
                assistant_id=self.params['assistant_id'],
                instructions=instructions,
                event_handler=event_handler,
                tool_choice=self.tool_choice,
                response_format=response_format
        ) as stream:
            stream.until_done()
        response = event_handler.get_response()
        if response['status']:
            return {"llm_response": response['message'], "token_usage": event_handler.token_usage}
        raise Exception(response['message'])


def get_llm_response(config, params):
    assistant = AssistantManager(config, params)
    return assistant.get_llm_response()
