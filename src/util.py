import json
import sys
import os
import getopt
import math
import time
import random
from json import JSONDecodeError

from hug.format import content_type
from hug.input_format import text


def get_config_file():
    argv = sys.argv
    args = [arg for arg in argv[1:] if 'config' in arg]
    optlist, args = getopt.getopt(args, "", ["config=", ])
    opt_dict = dict(optlist)
    config_file = None
    if '--config' in opt_dict:
        config_file = opt_dict['--config']
        if not os.path.isfile(config_file):
            config_file = None

    return config_file


@content_type('application/json')
def json_formatter(body, charset='utf-8', **kwargs):
    """Takes JSON formatted data, converting it into native Python objects"""
    try:
        data = json.loads(text(body, charset=charset))
        return data

    except Exception as err:
        return 'Invalid payload format, expected json formatted payload, got %s.' % text(body, charset=charset)


@content_type('multipart/form-data')
def multipart(body, **header_params):
    """Converts multipart form data into native Python objects
    NOTE: this is a hack to work around an issue in processing file uploads.
    """
    from multipart import MultipartParser
    if header_params and 'boundary' in header_params:
        if type(header_params['boundary']) is str:
            header_params['boundary'] = header_params['boundary'].encode()

    parser = MultipartParser(stream=body, boundary=header_params['boundary'], disk_limit=17179869184)
    form = dict(zip([p.name for p in parser.parts()],
                [(p.filename, p.file) if p.filename else p.file.read().decode()
                 for p in parser.parts()]))
    return form


def make_new_id(num_existing_ids):
    next_number = (num_existing_ids + 1) % 1024
    t = int(math.floor(time.time() * 1000))
    r_number = random.randint(0, 1024)
    new_id = (t << 20) | (r_number << 10) | next_number
    return new_id


def read_json_data(resp_data):
    if not isinstance(resp_data, str):
        return resp_data

    try:
        return json.loads(resp_data)

    except JSONDecodeError as err:
        print("DEBUG: Data is not in JSON format: %s" % resp_data)
        return resp_data