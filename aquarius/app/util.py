#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import json
import logging
from datetime import datetime

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

logger = logging.getLogger('aquarius')


def sanitize_record(data_record):
    if '_id' in data_record:
        data_record.pop('_id')
    return json.dumps(data_record, default=datetime_converter)


def make_paginate_response(query_list_result, search_model):
    total = query_list_result[1]
    offset = search_model.offset
    result = dict()
    result['results'] = query_list_result[0]
    result['page'] = search_model.page

    result['total_pages'] = int(total / offset) + int(total % offset > 0)
    result['total_results'] = total
    return result


def datetime_converter(o):
    if isinstance(o, datetime):
        return o.strftime(DATETIME_FORMAT)


def format_timestamp(timestamp):
    return f'{datetime.strptime(timestamp, DATETIME_FORMAT).replace(microsecond=0).isoformat()}Z'


def get_timestamp():
    """Return the current system timestamp."""
    return f'{datetime.utcnow().replace(microsecond=0).isoformat()}Z'


def get_curation_metadata(services):
    return get_metadata_from_services(services)['attributes']['curation']


def get_main_metadata(services):
    return get_metadata_from_services(services)['attributes']['main']


def get_metadata_from_services(services):
    for service in services:
        if service['type'] == 'metadata':
            return service


def reorder_services_list(services):
    result = []
    for service in services:
        if service['type'] == 'metadata':
            result.append(service)

    for service in services:
        if service['type'] != 'metadata':
            result.append(service)

    return result


def validate_date_format(date):
    try:
        datetime.strptime(date, DATETIME_FORMAT)
        return None, None
    except Exception as e:
        logging.error(str(e))
        return f"Incorrect data format, should be '{DATETIME_FORMAT}'", 400


def check_no_urls_in_files(main, method):
    if 'files' in main:
        for file in main['files']:
            if 'url' in file:
                logger.error(
                    '%s request failed: url is not allowed in files ' % method)
                return '%s request failed: url is not allowed in files ' % method, 400
    return None, None


def check_required_attributes(required_attributes, data, method):
    assert isinstance(
        data, dict), 'invalid `body` type, should already formatted into a dict.'
    logger.info('got %s request: %s' % (method, data))
    if not data:
        logger.error('%s request failed: data is empty.' % method)
        logger.error('%s request failed: data is empty.' % method)
        return 'payload seems empty.', 400

    for attr in required_attributes:
        if attr not in data:
            logger.error(
                '%s request failed: required attr %s missing.' % (method, attr))
            return '"%s" is required in the call to %s' % (attr, method), 400

    return None, None


def list_errors(list_errors_function, data):
    error_list = list()
    for err in list_errors_function(data):
        stack_path = list(err[1].relative_path)
        stack_path = [str(p) for p in stack_path]
        this_err_response = {
            'path': "/".join(stack_path), 'message': err[1].message}
        error_list.append(this_err_response)
    return error_list
