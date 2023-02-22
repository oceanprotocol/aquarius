#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging
import requests
import os

logger = logging.getLogger("aquarius")


class RBAC:
    @staticmethod
    def set_headers(request):
        RBAC.headers = {k: v for k, v in request.headers.items()}

    @staticmethod
    def sanitize_record(data_record):
        payload = {
            "eventType": "filter_single_result",
            "component": "metadatacache",
            "ddo": data_record,
            "browserHeaders": getattr(RBAC, "headers", {}),
        }

        response = requests.post(os.getenv("RBAC_SERVER_URL"), timeout=5, json=payload)
        if response.status_code != 200:
            logger.warning(
                f"Expected response code 200 from RBAC server, got {response.status_code}."
            )

        return (
            response.json()
            if response.status_code == 200 and response.json() is not False
            else data_record
        )

    @staticmethod
    def sanitize_query_result(query_result):
        payload = {
            "eventType": "filter_query_result",
            "component": "metadatacache",
            "query_result": query_result,
            "browserHeaders": getattr(RBAC, "headers", {}),
        }

        response = requests.post(os.getenv("RBAC_SERVER_URL"), json=payload, timeout=5)

        if response.status_code != 200:
            logger.warning(
                f"Expected response code 200 from RBAC server, got {response.status_code}."
            )

        return (
            response.json()
            if response.status_code == 200 and response.json() is not False
            else query_result
        )

    @staticmethod
    def validate_ddo_rbac(data):
        payload = {
            "eventType": "validateDDO",
            "component": "metadatacache",
            "ddo": data,
            "browserHeaders": getattr(RBAC, "headers", {}),
        }

        return requests.post(
            os.getenv("RBAC_SERVER_URL"), json=payload, timeout=5
        ).json()

    @staticmethod
    def check_permission_rbac(event_type, address):
        payload = {
            "eventType": event_type,
            "component": "metadatacache",
            "credentials": {"type": "address", "value": address},
        }

        try:
            return requests.post(
                os.getenv("RBAC_SERVER_URL"), json=payload, timeout=5
            ).json()
        except Exception:
            return False
