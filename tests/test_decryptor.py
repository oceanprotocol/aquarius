#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import Mock, patch

import pytest
from requests.models import Response

from aquarius.events.decryptor import decrypt_ddo


def test_decryptor_nonce_exception():
    with pytest.raises(Exception):
        with patch("requests.get") as mock:
            the_response = Mock(spec=Response)
            the_response.status_code = 400
            mock.return_value = the_response
            decrypt_ddo(None, "provider_url", None, None, None)


def test_decryptor_request_exception():
    with pytest.raises(Exception):
        with patch("requests.get") as mock_get:
            the_get_response = Mock(spec=Response)
            the_get_response.status_code = 200
            the_get_response.json.return_value = {"nonce": "13"}
            mock_get.return_value = the_get_response
            with patch("requests.post") as mock:
                the_response = Mock(spec=Response)
                the_response.status_code = 400
                mock.return_value = the_response
                decrypt_ddo(None, "provider_url", None, None, None)
