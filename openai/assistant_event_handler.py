"""
Copyright start
MIT License
Copyright (c) 2025 Fortinet Inc
Copyright end
"""
from typing_extensions import override
from openai import AssistantEventHandler
from openai.types.beta.threads.runs import RunStepDelta
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import ToolCall, RunStep
from openai.types.beta import AssistantStreamEvent
from .operations import *
from .utils import execute_connector_action

logger = get_logger(LOGGER_NAME)


class EventHandler(AssistantEventHandler):
    def __init__(self, config, params, last_message_id):
        super().__init__()
        self.run_id = None
        self.thread_messages = []
        self.config = config
        self.params = params
        self.tool_outputs = []
        self.token_usage = {}
        self.function_call_token_usage = None
        self.last_message_id = last_message_id
        self.to_add_message = True
        self.function_calling_output = None

    # Executes on every event
    @override
    def on_event(self, event: AssistantStreamEvent) -> None:
        # logger.info(f'event: {event.event}')
        self.run_id = event.data.id
        if event.event == 'thread.run.requires_action':
            self.handle_requires_action(data=event.data)

    def handle_requires_action(self, data):
        for tool in data.required_action.submit_tool_outputs.tool_calls:
            if tool.type == 'function':
                self.tool_call_type_function(tool=tool)
        # Submit all tool_outputs at the same time
        self.submit_tool_outputs()

    def tool_call_type_function(self, tool):
        logger.info(
            f'Calling tool function, Function Name: {tool.function.name}, Function Argument: {tool.function.arguments}')
        # call required function
        self.call_required_function(tool.function.name, tool.function.arguments)
        logger.info(f'Function Calling output: {self.function_calling_output}')
        if not self.function_calling_output:
            self.function_calling_output = 'There seems to be some issue while function calling output is None.'
        # To add tool call function output to thread or not
        if self.to_add_message:
            self.tool_outputs.append({"tool_call_id": tool.id, "output": self.function_calling_output})
        else:
            # Directly add the message to thread and cancel the run
            cancel_run(config=self.config,
                       params={'thread_id': self.params['thread_id'], 'run_id': self.run_id})
            create_thread_message(self.config,
                                  params={'thread_id': self.params['thread_id'], 'role': 'assistant',
                                          'content': self.function_calling_output})

    def submit_tool_outputs(self):
        client = openai.OpenAI(api_key=self.config['apiKey'], project=self.config.get('project'),
                               organization=self.config.get('organization'))
        run_object = get_run(config=self.config, params={'run_id': self.run_id, 'thread_id': self.params['thread_id']})
        if run_object['status'] != 'cancelled':
            with client.beta.threads.runs.submit_tool_outputs_stream(
                    thread_id=self.params['thread_id'],
                    run_id=self.run_id,
                    tool_outputs=self.tool_outputs,
                    event_handler=EventHandler(self.config, self.params, self.last_message_id)
            ) as stream:
                stream.until_done()
        logger.info(f'Successfully submitted tool output')

    # thread.run.step.created
    @override
    def on_run_step_created(self, run_step: RunStep) -> None:
        pass

    # thread.run.step.delta
    @override
    def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep):
        pass

    # thread.run.completed
    @override
    def on_run_step_done(self, run_step: RunStep) -> None:
        pass

    # thread.message.created
    @override
    def on_message_created(self, message: Message) -> None:
        pass

    # thread.message.delta
    @override
    def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        pass

    # thread.message.completed
    @override
    def on_message_done(self, message: Message) -> None:
        pass

    @override
    def on_tool_call_created(self, tool_call):
        pass

    @override
    def on_tool_call_delta(self, delta, snapshot):
        pass

    @override
    def on_tool_call_done(self, tool_call: ToolCall) -> None:
        # logger.info(f'Tool Call: {tool_call}')
        pass

    @override
    def on_end(self):
        run_payload = {'run_id': self.run_id, 'thread_id': self.params['thread_id']}
        run_object = get_run(config=self.config, params=run_payload)

        # wait for the run to get completed or canceled to load the messages
        while run_object['status'] not in ['completed', 'cancelled']:
            run_object = get_run(config=self.config, params=run_payload)
            # logger.info(f'Run Status: {run_object.status}')

        self.thread_messages = list_thread_messages(config=self.config,
                                                    params={'thread_id': self.params['thread_id'],
                                                            'before': self.last_message_id})
        # check if more token has been used in function calling
        if self.function_call_token_usage is not None:
            self.token_usage = self.set_token_usage(run_object['usage'])
        else:
            self.token_usage = run_object['usage']

    @override
    def on_exception(self, exception: Exception) -> None:
        logger.error(f"Exception occurred while executing thread: {exception}")

    def get_thread_messages(self):
        return self.thread_messages

    def call_required_function(self, function_name, arguments):
        try:
            payload = {"connector_name": 'openai', "config_id": self.config['config_id'],
                       "function_name": function_name, "arguments": arguments, "tool_call_metadata": self.params}
            response = execute_connector_action(self.params['tool_call_function_config_id'],
                                                self.params['tool_call_function_connector_name'],
                                                self.params['tool_call_function_operation_name'], payload)
            if response.get('status') == 'Success':
                self.function_calling_output = response['data'].get('function_calling_output')
                if 'to_add_message' in response['data']:
                    self.to_add_message = response['data'].get('to_add_message')
                if 'token_usage' in response['data']:
                    self.function_call_token_usage = response['data'].get('token_usage')
                return
            self.function_calling_output = response.get('message')
            if not self.function_calling_output:
                self.function_calling_output = 'Unknown error occurred.'
        except Exception as error:
            error_message = f'Error occurred while executing tool function call: {error}'
            logger.error(error_message)
            self.function_calling_output = error_message

    # Add function call token to run call token usage
    def set_token_usage(self, token_usage):
        self.function_call_token_usage = dict(self.function_call_token_usage)
        token_usage = dict(token_usage)

        self.merge_dicts(token_usage, self.function_call_token_usage)
        return token_usage

    def merge_dicts(self, dict1, dict2):
        for key, value in dict2.items():
            if isinstance(value, dict):
                # Check if value is dict, and present in dict
                if key not in dict1:
                    # Create a new dict if not present
                    dict1[key] = {}
                self.merge_dicts(dict1[key], value)
            elif isinstance(value, int):
                dict1[key] = dict1.get(key, 0) + value
