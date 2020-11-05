#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import copy
import json
import logging
from collections import OrderedDict
from datetime import datetime

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
DATETIME_FORMAT_NO_Z = '%Y-%m-%dT%H:%M:%S'

logger = logging.getLogger('aquarius')


def sanitize_record(data_record):
    """
    Sanitize a record to json.

    Args:
        data_record: (todo): write your description
    """
    if '_id' in data_record:
        data_record.pop('_id')
    if 'event' in data_record:
        data_record.pop('event')

    return json.dumps(data_record, default=datetime_converter)


def make_paginate_response(query_list_result, search_model):
    """
    Make paginate pagination response.

    Args:
        query_list_result: (list): write your description
        search_model: (todo): write your description
    """
    total = query_list_result[1]
    offset = search_model.offset
    result = dict()
    result['results'] = query_list_result[0]
    result['page'] = search_model.page

    result['total_pages'] = int(total / offset) + int(total % offset > 0)
    result['total_results'] = total
    return result


def get_request_data(request, url_params_only=False):
    """
    Get request parameters.

    Args:
        request: (todo): write your description
        url_params_only: (str): write your description
    """
    if url_params_only:
        return request.args
    return request.args if request.args else request.json


def datetime_converter(o):
    """
    Convert datetime. datetime.

    Args:
        o: (todo): write your description
    """
    if isinstance(o, datetime):
        return o.strftime(DATETIME_FORMAT)


def format_timestamp(timestamp):
    """
    Format a timestamp.

    Args:
        timestamp: (int): write your description
    """
    try:
        return f'{datetime.strptime(timestamp, DATETIME_FORMAT).replace(microsecond=0).isoformat()}Z'
    except Exception:
        return f'{datetime.strptime(timestamp, DATETIME_FORMAT_NO_Z).replace(microsecond=0).isoformat()}Z'


def get_timestamp():
    """Return the current system timestamp."""
    return f'{datetime.utcnow().replace(microsecond=0).isoformat()}Z'


def get_curation_metadata(services):
    """
    Retrieve the metadata. curation.

    Args:
        services: (todo): write your description
    """
    return get_metadata_from_services(services)['attributes']['curation']


def get_main_metadata(services):
    """
    Return a list of service.

    Args:
        services: (todo): write your description
    """
    return get_metadata_from_services(services)['attributes']['main']


def get_metadata_from_services(services):
    """
    Returns a list of service.

    Args:
        services: (todo): write your description
    """
    for service in services:
        if service['type'] == 'metadata':
            return service


def reorder_services_list(services):
    """
    Return a list of services

    Args:
        services: (todo): write your description
    """
    service_dict = OrderedDict([(s['type'], s) for s in services])
    result = [service_dict.pop('metadata')]
    result.extend([s for t, s in service_dict.items()])

    return result


def init_new_ddo(data):
    """
    Initialize a new record.

    Args:
        data: (todo): write your description
    """
    _record = copy.deepcopy(data)
    _record['created'] = format_timestamp(data['created'])
    _record['updated'] = _record['created']
    if 'accessWhiteList' not in data:
        _record['accessWhiteList'] = []
    else:
        if not isinstance(data['accessWhiteList'], list):
            _record['accessWhiteList'] = []
        else:
            _record['accessWhiteList'] = data['accessWhiteList']

    for service in _record['service']:
        if service['type'] == 'metadata':
            samain = service['attributes']['main']
            samain['dateCreated'] = format_timestamp(samain['dateCreated'])
            samain['datePublished'] = get_timestamp()

            curation = dict()
            curation['rating'] = 0.00
            curation['numVotes'] = 0
            curation['isListed'] = True
            service['attributes']['curation'] = curation
    _record['service'] = reorder_services_list(_record['service'])
    return _record


def validate_date_format(date):
    """
    Validate a date is valid.

    Args:
        date: (todo): write your description
    """
    try:
        datetime.strptime(date, DATETIME_FORMAT)
        return None, None
    except Exception as e:
        logging.error(f'validate_date_format: {str(e)}')
        return f"Incorrect data format, should be '{DATETIME_FORMAT}'", 400


def check_no_urls_in_files(main, method):
    """
    Check if the url is in the given url.

    Args:
        main: (str): write your description
        method: (str): write your description
    """
    if 'files' in main:
        for file in main['files']:
            if 'url' in file:
                logger.error(
                    '%s request failed: url is not allowed in files ' % method)
                return '%s request failed: url is not allowed in files ' % method, 400
    return None, None


def check_required_attributes(required_attributes, data, method):
    """
    Check if required attributes are required.

    Args:
        required_attributes: (todo): write your description
        data: (dict): write your description
        method: (str): write your description
    """
    assert isinstance(
        data, dict), 'invalid `body` type, should already formatted into a dict.'
    logger.info('got %s request: %s' % (method, data))
    if not data:
        logger.error('%s request failed: data is empty.' % method)
        logger.error('%s request failed: data is empty.' % method)
        return 'payload seems empty.', 400

    keys = set(data.keys())
    if not isinstance(required_attributes, set):
        required_attributes = set(required_attributes)
    missing_attrs = required_attributes.difference(keys)
    if missing_attrs:
        logger.error(f'{method} request failed: required attributes {missing_attrs} are missing.')
        return f'"{missing_attrs}" are required in the call to {method}', 400

    return None, None


def list_errors(list_errors_function, data):
    """
    Lists the errors

    Args:
        list_errors_function: (todo): write your description
        data: (array): write your description
    """
    error_list = list()
    for err in list_errors_function(data):
        stack_path = list(err[1].relative_path)
        stack_path = [str(p) for p in stack_path]
        this_err_response = {
            'path': "/".join(stack_path), 'message': err[1].message}
        error_list.append(this_err_response)
    return error_list


def validate_data(data, method):
    """
    Validate the data.

    Args:
        data: (todo): write your description
        method: (str): write your description
    """
    required_attributes = {'@context', 'created', 'id', 'publicKey', 'authentication', 'proof',
                           'service', 'dataToken'}

    msg, status = check_required_attributes(required_attributes, data, method)
    if msg:
        return msg, status

    msg, status = check_no_urls_in_files(get_main_metadata(data['service']), method)
    if msg:
        return msg, status

    msg, status = validate_date_format(data['created'])
    if status:
        return msg, status

    return None, None


def get_sender_from_txid(web3, txid):
    """
    Get transaction by its transaction.

    Args:
        web3: (str): write your description
        txid: (str): write your description
    """
    transaction = web3.eth.getTransaction(txid)
    if transaction is not None:
        return transaction['from']
    return None
