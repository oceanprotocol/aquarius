#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import copy
import json

import pytest

from aquarius.constants import BaseURLs
from aquarius.run import app
from tests.ddos.ddo_sample1 import json_dict
from tests.ddos.ddo_sample_updates import json_update

app = app


@pytest.fixture
def base_ddo_url():
    return BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo'


@pytest.fixture
def client_with_no_data():
    client = app.test_client()
    client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo')
    yield client


@pytest.fixture
def client():
    client = app.test_client()
    client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo')
    post = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                       data=json.dumps(json_update),
                       content_type='application/json')
    if post.status_code not in (200, 201):
        raise AssertionError(f'register asset failed: {post}')
    post2 = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                        data=json.dumps(json_dict),
                        content_type='application/json')

    yield client

    client.delete(
        BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post.data.decode('utf-8'))['id'])
    client.delete(
        BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post2.data.decode('utf-8'))[
            'id'])


@pytest.fixture
def test_assets():
    _assets = []
    for i in range(10):
        a = copy.deepcopy(json_dict)
        a['id'] = a['id'][:-2] + str(i) + str(i)
        _assets.append(a)
    return _assets
