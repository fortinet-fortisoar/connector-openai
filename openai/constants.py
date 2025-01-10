"""
Copyright start
MIT License
Copyright (c) 2025 Fortinet Inc
Copyright end
"""
LOGGER_NAME = 'openai'
SCHEMA_ERROR = 'There was an error in your messages format, use this schema instead: [{\'role\': \'user\', \'content\': \'question1\'},{\'role\': \'assistant\', \'content\': \'response1\'},{\'role\': \'user\', \'content\': \'question2\'}]'
MESSAGES_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'role': {
                'type': 'string'
            },
            'content': {
                'type': ['string']
            }
        },
        'required': [
            'role',
            'content'
        ]
    }
}

USAGE_URL = 'https://api.openai.com/v1/usage'
SORT_ORDER_MAPPING = {
    'Ascending': 'asc',
    'Descending': 'desc'
}
FILE_PURPOSE_MAPPING = {
    "Assistants": "assistants",
    "Vision": "vision",
    "Batch": "batch",
    "Fine-tune": "fine-tune",
    "User Data": "user_data",
    "Assistants Output": "assistants_output",
    "Batch Output": "batch_output",
    "Fine-tune Results": "fine-tune-results"
}
