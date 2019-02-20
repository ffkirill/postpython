from collections import defaultdict
from copy import copy
import json

from postpython.utils import (extract_dict_from_raw_mode_data, extract_dict_from_raw_headers, format_object,
                              normalize_func_name, normalize_class_name)


class PostPythonRequestsBackend:
    @staticmethod
    def request(request_dict: dict):
        import requests
        return requests.request(**request_dict)


class PostPythonDjangoRequestsBackend:
    def __init__(self, test_client):
        self.test_client = test_client

    @staticmethod
    def normalize_headers(headers: dict):
        def norm_name(key: str):
            key = key.upper().replace('-', '_')
            if key.startswith('X_'):
                key = 'HTTP_' + key
            return key
        return {norm_name(key): value for key, value in headers.items()}

    def request(self, request_dict: dict):
        method = request_dict.pop('method')
        url = request_dict.pop('url')
        data = json.dumps(request_dict.pop('json'))
        headers = self.normalize_headers(request_dict.pop('headers'))
        return self.test_client.generic(path=url, method=method, data=data, **headers)


class PostPythonFolder:
    path: tuple
    flat_items: dict
    name: str

    def __init__(self, flat_items: dict, path: tuple = tuple()):
        self.path = path
        self.flat_items = flat_items
        self.name = '.'.join(path)

    def __getattr__(self, item):
        new_path = (*self.path, item)
        str_path = '.'.join(new_path)
        if str_path not in self.flat_items:
            raise AttributeError(item)
        return self.flat_items[str_path]

    def __repr__(self):
        return f'PostPythonFolder("{self.name}")'


class PostPythonRequest:
    request_kwargs: dict
    environment: dict
    name: str
    backend = None

    def __init__(self, backend, data: dict, environment: dict):
        self.backend = backend
        self.request_kwargs = {}
        self.environment = environment
        self.name = data['name']
        self.request_kwargs['url'] = data['request']['url']['raw']
        if data['request']['body']['mode'] == 'raw' and data['request']['body']['raw']:
            self.request_kwargs['json'] = extract_dict_from_raw_mode_data(data['request']['body']['raw'])
            self.request_kwargs['method'] = data['request']['method']
            self.request_kwargs['headers'] = extract_dict_from_raw_headers(data['request']['header'])

    def __call__(self, *args, **kwargs):
        new_env = copy(self.environment)
        new_env.update(kwargs)
        formatted_kwargs = format_object(self.request_kwargs, new_env)
        return self.backend.request(formatted_kwargs)

    def __repr__(self):
        return f'PostPythonRequest("{self.name}")'


class PostPythonCollection:
    flat_items: dict
    environment: dict
    backend = None

    def __init__(self, postman_collection_file_path, backend=PostPythonRequestsBackend):
        self.environment = {}
        self.backend = backend
        with open(postman_collection_file_path, encoding='utf8') as postman_collection_file:
            self.flat_items = defaultdict(list)
            collection = json.load(postman_collection_file)
            self.process_folder(collection)

    @staticmethod
    def is_item(it: dict):
        return 'request' in it

    def process_folder(self, folder: dict, parent_folder: tuple = tuple()):
        for item in folder['item']:
            if self.is_item(item):
                path = '.'.join((*parent_folder, normalize_func_name(item['name'])))
                self.process_item(item, path)
            else:
                current_name = normalize_class_name(item['name'])
                path = (*parent_folder, current_name)
                self.flat_items['.'.join(path)] = PostPythonFolder(self.flat_items, path)
                self.process_folder(item, path)

    def process_item(self, item, path: str):
        self.flat_items[path] = PostPythonRequest(self.backend, item, self.environment)

    def __getattr__(self, item):
        if item in self.flat_items:
            return self.flat_items[item]
        else:
            return PostPythonFolder(self.flat_items, (item,))

    def __repr__(self):
        return f'<PostPythonCollection {list(self.flat_items.keys())!r}>'
