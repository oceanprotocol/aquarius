#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import Mock, patch

import pytest
from requests.models import Response

from aquarius.events.decryptor import decrypt_ddo


def test_decryptor_request_exception():
    with pytest.raises(Exception, match="Provider exception on decrypt"):
        with patch("requests.post") as mock:
            the_response = Mock(spec=Response)
            the_response.status_code = 400
            mock.return_value = the_response
            decrypt_ddo(None, "provider_url", None, None, None, "test_hash", None)

    with pytest.raises(Exception, match="Hash check failed"):
        with patch("requests.post") as mock:
            the_response = Mock(spec=Response)
            the_response.status_code = 201
            the_response.content = b"some other test"
            mock.return_value = the_response
            decrypt_ddo(
                None,
                "provider_url",
                None,
                None,
                None,
                "test_hash".encode("utf-8"),
                None,
            )
