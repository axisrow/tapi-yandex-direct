"""Optional live integration test for v4 Live JSON client.

Skipped automatically unless YANDEX_DIRECT_TOKEN is in the environment, so CI
never hits the real API. Run locally with:

    export YANDEX_DIRECT_TOKEN=...   (real OAuth token)
    export YANDEX_DIRECT_LOGIN=...   (account login, defaults to ksamatadirect)
    pytest tests/test_v4_live_integration.py -v -m live
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("YANDEX_DIRECT_TOKEN"),
    reason="set YANDEX_DIRECT_TOKEN to run against the real Yandex Direct API",
)


@pytest.mark.live
def test_get_clients_units_live():
    from tapi_yandex_direct import YandexDirectV4Live

    login = os.environ.get("YANDEX_DIRECT_LOGIN", "ksamatadirect")
    client = YandexDirectV4Live(
        access_token=os.environ["YANDEX_DIRECT_TOKEN"],
        login=login,
    )
    result = client.v4live().post(
        data={"method": "GetClientsUnits", "param": [login]}
    )
    extracted = result().extract()
    assert isinstance(extracted, list)
    assert extracted, "expected at least one entry in GetClientsUnits response"
    entry = extracted[0]
    assert entry["Login"]
    assert isinstance(entry["UnitsRest"], int)
