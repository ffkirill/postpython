import re
from collections import defaultdict
from copy import copy

import requests

import json


def extract_dict_from_raw_mode_data(raw):
    try:
        return json.loads(raw)
    except json.decoder.JSONDecodeError:
        return {}


def extract_dict_from_raw_headers(raw):
    d = {}
    for header in raw:
        d[header['key']] = header['value']

    return d


def normalize_class_name(string):
    string = re.sub(r'[?!@#$%^&*()_\-+=,./\'\\\"|:;{}\[\]]', ' ', string)
    return string.title().replace(' ', '')


def normalize_func_name(string):
    string = re.sub(r'[?!@#$%^&*()_\-+=,./\'\\\"|:;{}\[\]]', ' ', string)
    return '_'.join(string.lower().split())


def format_object(o, key_values):
    if isinstance(o, str):
        try:
            return o.replace('{{', '{').replace('}}', '}').format(**key_values)
        except KeyError as e:
            raise KeyError(
                "Except value %s in PostPython environment variables.\n Environment variables are %s" % (e, key_values))
    elif isinstance(o, dict):
        return format_dict(o, key_values)
    elif isinstance(o, list):
        return [format_object(oo, key_values) for oo in o]


def format_dict(d, key_values):
    kwargs = {}
    for k, v in d.items():
        kwargs[k] = format_object(v, key_values)
    return kwargs


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


class PostPythonRequest:
    request_kwargs: dict
    environment: dict

    def __init__(self, data: dict, environment: dict):
        self.request_kwargs = {}
        self.environment = environment
        self.request_kwargs['url'] = data['request']['url']['raw']
        if data['request']['body']['mode'] == 'raw' and data['request']['body']['raw']:
            self.request_kwargs['json'] = extract_dict_from_raw_mode_data(data['request']['body']['raw'])
            self.request_kwargs['method'] = data['request']['method']
            self.request_kwargs['headers'] = extract_dict_from_raw_headers(data['request']['header'])

    def __call__(self, *args, **kwargs):
        new_env = copy(self.environment)
        new_env.update(kwargs)
        formatted_kwargs = format_object(self.request_kwargs, new_env)
        return requests.request(**formatted_kwargs)


class PostPythonCollection:
    flat_items: dict
    environment: dict

    def __init__(self, postman_collection_file_path):
        with open(postman_collection_file_path, encoding='utf8') as postman_collection_file:
            self.flat_items = defaultdict(list)
            collection = json.load(postman_collection_file)
            self.environment = {}
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
        self.flat_items[path] = PostPythonRequest(item, self.environment)

    def __getattr__(self, item):
        if item in self.flat_items:
            return self.flat_items[item]
        else:
            return self.Folder(self.flat_items, (item,))
