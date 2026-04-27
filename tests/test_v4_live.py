"""Unit tests for the v4 Live (JSON) client adapter — mocked, no network."""
import json
import logging

import pytest
import responses

from tapi_yandex_direct import YandexDirectV4Live
from tapi_yandex_direct import exceptions as exc
from tapi_yandex_direct.v4 import SUPPORTED_V4_METHODS

logging.basicConfig(level=logging.DEBUG)

V4_LIVE_URL = "https://api.direct.yandex.ru/live/v4/json/"
V4_LIVE_SANDBOX_URL = "https://api-sandbox.direct.yandex.ru/live/v4/json/"


def _make_client(**overrides):
    defaults = dict(
        access_token="test-token",
        login="ksamatadirect",
        is_sandbox=False,
        language="en",
        retry_if_exceeded_limit=False,
        retries_if_server_error=0,
    )
    defaults.update(overrides)
    return YandexDirectV4Live(**defaults)


def _last_request_body() -> dict:
    """Decode the body of the last call captured by `responses`."""
    return json.loads(responses.calls[-1].request.body)


@responses.activate
def test_v4live_post_success_returns_data():
    responses.add(
        responses.POST,
        V4_LIVE_URL,
        json={"data": [{"UnitsRest": 32000, "Login": "ksamatadirect"}]},
        status=200,
    )
    client = _make_client()
    result = client.v4live().post(
        data={"method": "GetClientsUnits", "param": ["ksamatadirect"]}
    )
    assert result.data == {"data": [{"UnitsRest": 32000, "Login": "ksamatadirect"}]}


@responses.activate
def test_v4live_token_appended_to_body_and_header():
    responses.add(responses.POST, V4_LIVE_URL, json={"data": []}, status=200)
    client = _make_client(access_token="AQAAAA-secret")
    client.v4live().post(data={"method": "GetClientsUnits", "param": []})

    sent = responses.calls[-1].request
    assert sent.headers["Authorization"] == "Bearer AQAAAA-secret"
    body = json.loads(sent.body)
    assert body["token"] == "AQAAAA-secret"
    assert body["method"] == "GetClientsUnits"


@responses.activate
def test_v4live_locale_passed_in_body():
    responses.add(responses.POST, V4_LIVE_URL, json={"data": []}, status=200)
    client = _make_client(language="ru")
    client.v4live().post(data={"method": "GetClientsUnits", "param": []})
    assert _last_request_body()["locale"] == "ru"


@responses.activate
def test_v4live_default_locale_is_en():
    responses.add(responses.POST, V4_LIVE_URL, json={"data": []}, status=200)
    # Drop language explicitly to take the adapter default.
    client = YandexDirectV4Live(access_token="t")
    client.v4live().post(data={"method": "GetClientsUnits", "param": []})
    assert _last_request_body()["locale"] == "en"


@responses.activate
def test_v4live_login_injected_into_param_dict():
    responses.add(responses.POST, V4_LIVE_URL, json={"data": []}, status=200)
    client = _make_client(login="agent@yandex")
    client.v4live().post(
        data={"method": "GetEventsLog", "param": {"TimestampFrom": 1714200000}}
    )
    body = _last_request_body()
    assert body["param"]["login"] == "agent@yandex"


@responses.activate
def test_v4live_login_not_injected_when_param_is_list():
    responses.add(responses.POST, V4_LIVE_URL, json={"data": []}, status=200)
    client = _make_client(login="agent@yandex")
    client.v4live().post(data={"method": "GetClientsUnits", "param": ["sub"]})
    # param remains a list; login does not get pushed in
    assert _last_request_body()["param"] == ["sub"]


@responses.activate
def test_v4live_unknown_method_raises_value_error():
    # No responses.add — the call must fail before any HTTP request.
    client = _make_client()
    with pytest.raises(ValueError, match="Unknown v4 Live method"):
        client.v4live().post(data={"method": "BogusMadeUpMethod", "param": {}})


@responses.activate
def test_v4live_extract_returns_data_field():
    responses.add(
        responses.POST,
        V4_LIVE_URL,
        json={"data": [{"UnitsRest": 100}]},
        status=200,
    )
    client = _make_client()
    result = client.v4live().post(
        data={"method": "GetClientsUnits", "param": []}
    )
    assert result().extract() == [{"UnitsRest": 100}]


@responses.activate
def test_v4live_error_code_53_raises_token_error():
    responses.add(
        responses.POST,
        V4_LIVE_URL,
        json={"error_code": 53, "error_str": "Invalid token", "error_detail": ""},
        status=200,
    )
    client = _make_client()
    with pytest.raises(exc.V4LiveTokenError) as info:
        client.v4live().post(data={"method": "GetClientsUnits", "param": []})
    assert info.value.error_code == 53
    assert "Invalid token" in info.value.error_str


@responses.activate
def test_v4live_error_code_54_raises_limit_when_retry_disabled():
    responses.add(
        responses.POST,
        V4_LIVE_URL,
        json={"error_code": 54, "error_str": "Limit", "error_detail": ""},
        status=200,
    )
    client = _make_client(retry_if_exceeded_limit=False)
    with pytest.raises(exc.V4LiveRequestsLimitError) as info:
        client.v4live().post(data={"method": "GetClientsUnits", "param": []})
    assert info.value.error_code == 54


@responses.activate
def test_v4live_error_code_54_retries_when_enabled(monkeypatch):
    # Stub time.sleep so we don't actually wait 10s.
    import tapi_yandex_direct.v4.adapter as adapter_mod
    monkeypatch.setattr(adapter_mod.time, "sleep", lambda _s: None)

    responses.add(
        responses.POST,
        V4_LIVE_URL,
        json={"error_code": 54, "error_str": "Limit", "error_detail": ""},
        status=200,
    )
    responses.add(
        responses.POST,
        V4_LIVE_URL,
        json={"data": [{"UnitsRest": 1}]},
        status=200,
    )
    client = _make_client(retry_if_exceeded_limit=True)
    result = client.v4live().post(
        data={"method": "GetClientsUnits", "param": []}
    )
    assert result().extract() == [{"UnitsRest": 1}]
    assert len(responses.calls) == 2


@responses.activate
def test_v4live_arbitrary_error_raises_v4live_error():
    responses.add(
        responses.POST,
        V4_LIVE_URL,
        json={"error_code": 71, "error_str": "Bad params", "error_detail": "x"},
        status=200,
    )
    client = _make_client()
    with pytest.raises(exc.V4LiveError) as info:
        client.v4live().post(data={"method": "GetClientsUnits", "param": []})
    # Generic V4LiveError, not subclass for token/limit
    assert type(info.value) is exc.V4LiveError
    assert info.value.error_code == 71


@responses.activate
def test_v4live_pages_and_items_do_not_raise_type_error():
    # Iterator hooks (get_iterator_pages / _items / _iteritems) call
    # self.extract via **kwargs without response / request_kwargs. extract's
    # signature therefore accepts both as optional — otherwise .items() /
    # .pages() raise "extract() missing 2 required positional arguments".
    responses.add(
        responses.POST,
        V4_LIVE_URL,
        json={"data": [{"id": 1}, {"id": 2}]},
        status=200,
    )
    client = _make_client()
    result = client.v4live().post(
        data={"method": "GetClientsUnits", "param": []}
    )
    items = list(result().items())
    assert items == [{"id": 1}, {"id": 2}]


@responses.activate
def test_v4live_malformed_error_code_treated_as_success():
    # Defensive cast in process_response: if Yandex ever returned
    # error_code=null or a non-numeric string, the response should be treated
    # as success rather than letting a raw TypeError/ValueError leak through.
    responses.add(
        responses.POST,
        V4_LIVE_URL,
        json={"error_code": None, "data": [{"x": 1}]},
        status=200,
    )
    client = _make_client()
    result = client.v4live().post(
        data={"method": "GetClientsUnits", "param": []}
    )
    assert result().extract() == [{"x": 1}]


@responses.activate
def test_v4live_sandbox_url_used():
    responses.add(
        responses.POST,
        V4_LIVE_SANDBOX_URL,
        json={"data": []},
        status=200,
    )
    client = _make_client(is_sandbox=True)
    client.v4live().post(data={"method": "GetClientsUnits", "param": []})
    assert responses.calls[-1].request.url.startswith(V4_LIVE_SANDBOX_URL)


def test_v4live_supported_methods_match_matrix_candidates():
    """SUPPORTED_V4_METHODS must match Phase 1 matrix actual_no_v5_analogue list.

    Activates only after Phase 1 (PR #16) lands on master and exposes
    V4_TO_V5_MAP from scripts/audit_wsdl.py. Skipped otherwise so this PR can
    be reviewed independently of the audit-matrix PR.
    """
    import importlib.util
    from pathlib import Path

    audit_path = Path(__file__).resolve().parents[1] / "scripts" / "audit_wsdl.py"
    spec = importlib.util.spec_from_file_location("audit_wsdl", audit_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if not hasattr(mod, "V4_TO_V5_MAP"):
        pytest.skip("V4_TO_V5_MAP not yet on master (Phase 1 / PR #16 pending)")

    for method in SUPPORTED_V4_METHODS:
        assert method in mod.V4_TO_V5_MAP, (
            f"{method} declared as supported but missing from V4_TO_V5_MAP"
        )
        assert mod.V4_TO_V5_MAP[method] is None, (
            f"{method} is supported as v4 candidate but has v5 equivalent "
            f"{mod.V4_TO_V5_MAP[method]!r} — should not be implemented"
        )
