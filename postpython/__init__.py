from collections import defaultdict
import json
from urllib3 import encode_multipart_formdata

from postpython.utils import (extract_dict_from_raw_mode_data, extract_dict_from_raw_headers, format_object,
                              normalize_func_name, normalize_class_name)


class PostPythonRequestsBackend:
    @staticmethod
    def request(request_dict: dict, files: dict):
        import requests
        if 'data' in request_dict and not files:  # force multipart/form-data
            headers = {'Content-type': 'multipart/form-data; boundary=BoUnDaRyStRiNg'}
            request_dict['data'], _ = encode_multipart_formdata(request_dict['data'], boundary='BoUnDaRyStRiNg')
            if 'headers' in request_dict:
                request_dict['headers'].update(**headers)
            else:
                request_dict['headers'] = headers
        return requests.request(**request_dict, files=files)


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

    def request(self, request_dict: dict, files: dict):
        from django.test.client import encode_multipart
        method = request_dict['method']
        url = request_dict['url']

        if 'json' in request_dict:
            json_data = {'data': json.dumps(request_dict['json'])}
        else:
            json_data = {}

        if 'data' in request_dict:
            form_data = {'data': encode_multipart('BoUnDaRyStRiNg', dict(**request_dict['data'], **files)),
                         'content_type': 'multipart/form-data; boundary=BoUnDaRyStRiNg'}
        else:
            form_data = {}

        headers = self.normalize_headers(request_dict.pop('headers'))
        return self.test_client.generic(path=url, method=method, **json_data, **form_data, **headers)


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

        elif data['request']['body']['mode'] == 'formdata' and data['request']['body']['formdata']:
            self.process_form_data(data['request']['body']['formdata'])

        self.request_kwargs['method'] = data['request']['method']
        self.request_kwargs['headers'] = extract_dict_from_raw_headers(data['request']['header'])

    def process_form_data(self, data):
        form_data = {}
        self.request_kwargs['data'] = form_data
        for subdict in data:
            if subdict['type'] == 'text':
                form_data[subdict['key']] = subdict['value']

    def __call__(self, files: dict = None):
        if files is None:
            files = {}
        formatted_data = format_object(self.request_kwargs, self.environment)
        return self.backend.request(formatted_data, files)

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
