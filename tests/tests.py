import logging

import pytest
import responses

import tapi_yandex_direct.tapi_yandex_direct as adapter_mod
from tapi_yandex_direct import YandexDirect
from tapi_yandex_direct import exceptions as exc

logging.basicConfig(level=logging.DEBUG)

client = YandexDirect(
    access_token="",
    is_sandbox=False,
    retry_if_not_enough_units=False,
    retry_if_exceeded_limit=False,
    retries_if_server_error=5,
    # For Reports resource.
    processing_mode="offline",
    wait_report=True,
    return_money_in_micros=True,
    skip_report_header=True,
    skip_column_header=False,
    skip_report_summary=True,
)


@responses.activate
def test_sanity():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": []}},
        status=200,
    )

    result = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )
    assert result.data == {"result": {"Clients": []}}


@responses.activate
def test_extract():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": []}},
        status=200,
    )

    result = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )
    assert result().extract() == []


@responses.activate
def test_iter_items():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 1}, {"id": 2}], "LimitedBy": 1}},
        status=200,
    )

    clients = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )

    ids = []
    for item in clients().items():
        ids.append(item["id"])

    assert ids == [1, 2]


@responses.activate
def test_iter_pages_and_items():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 1}], "LimitedBy": 1}},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 2}]}},
        status=200,
    )

    clients = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )

    ids = []
    for page in clients().pages():
        for item in page().items():
            ids.append(item["id"])

    assert ids == [1, 2]


@responses.activate
def test_iter_items():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 1}], "LimitedBy": 1}},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 2}]}},
        status=200,
    )

    clients = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )

    ids = []
    for item in clients().iter_items():
        ids.append(item["id"])

    assert ids == [1, 2]


@responses.activate
def test_advideos_get():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/advideos",
        json={"result": {"AdVideos": []}},
        status=200,
    )
    result = client.advideos().post(
        data={
            "method": "get",
            "params": {"SelectionCriteria": {"Ids": ["123"]}, "FieldNames": ["Id", "Status"]},
        }
    )
    assert result.data == {"result": {"AdVideos": []}}
    assert result().extract() == []


@responses.activate
def test_get_report():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/reports",
        headers={"retryIn": "0"},
        status=202,
    )
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/reports",
        headers={"retryIn": "0"},
        status=202,
    )
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/reports",
        body="col1\tcol2\nvalue1\tvalue2\nvalue10\tvalue20\n",
        status=200,
    )
    report = client.reports().post(
        data={
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Date", "CampaignId"],
                "OrderBy": [{"Field": "Date"}],
                "ReportName": "report name",
                "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                "DateRangeType": "TODAY",
                "Format": "TSV",
                "IncludeVAT": "YES",
                "IncludeDiscount": "YES",
            }
        }
    )
    assert report.columns == ["col1", "col2"]
    assert report().to_values() == [["value1", "value2"], ["value10", "value20"]]
    assert report().to_lines() == ["value1\tvalue2", "value10\tvalue20"]
    assert report().to_columns() == [["value1", "value10"], ["value2", "value20"]]
    assert report().to_dicts() == [
        {"col1": "value1", "col2": "value2"},
        {"col1": "value10", "col2": "value20"},
    ]


@responses.activate
def test_strategies_get():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/strategies",
        json={"result": {"Strategies": []}},
        status=200,
    )
    result = client.strategies().post(
        data={
            "method": "get",
            "params": {"SelectionCriteria": {}, "FieldNames": ["Id", "Name"]},
        }
    )
    assert result.data == {"result": {"Strategies": []}}
    assert result().extract() == []


@responses.activate
def test_strategies_add():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/strategies",
        json={"result": {"AddResults": [{"Id": 42}]}},
        status=200,
    )
    result = client.strategies().post(
        data={
            "method": "add",
            "params": {"Strategies": [{"Name": "s1", "Type": "MANUAL_CPC"}]},
        }
    )
    assert result.data == {"result": {"AddResults": [{"Id": 42}]}}
    assert result().extract() == [{"Id": 42}]


@responses.activate
def test_dynamicfeedadtargets_get():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/dynamicfeedadtargets",
        json={"result": {"DynamicFeedAdTargets": []}},
        status=200,
    )
    result = client.dynamicfeedadtargets().post(
        data={
            "method": "get",
            "params": {"SelectionCriteria": {}, "FieldNames": ["Id", "Name"]},
        }
    )
    assert result.data == {"result": {"DynamicFeedAdTargets": []}}
    assert result().extract() == []


@responses.activate
def test_dynamicfeedadtargets_suspend():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/dynamicfeedadtargets",
        json={"result": {"SuspendResults": [{"Id": 42}]}},
        status=200,
    )
    result = client.dynamicfeedadtargets().post(
        data={
            "method": "suspend",
            "params": {"SelectionCriteria": {"Ids": [42]}},
        }
    )
    assert result.data == {"result": {"SuspendResults": [{"Id": 42}]}}
    assert result().extract() == [{"Id": 42}]


@responses.activate
def test_agencyclients_add_passport_organization():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/agencyclients",
        json={"result": {"AddResults": [{"Login": "org-login"}]}},
        status=200,
    )
    result = client.agencyclients().post(
        data={
            "method": "addPassportOrganization",
            "params": {
                "Organization": {
                    "Name": "OrgName",
                    "Currency": "RUB",
                }
            },
        }
    )
    assert result.data == {"result": {"AddResults": [{"Login": "org-login"}]}}
    assert result().extract() == [{"Login": "org-login"}]


@responses.activate
def test_agencyclients_add_passport_organization_member():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/agencyclients",
        json={"result": {"AddResults": [{"Login": "member-login"}]}},
        status=200,
    )
    result = client.agencyclients().post(
        data={
            "method": "addPassportOrganizationMember",
            "params": {
                "Member": {
                    "PassportOrganizationLogin": "org-login",
                    "Role": "CHIEF",
                }
            },
        }
    )
    assert result.data == {"result": {"AddResults": [{"Login": "member-login"}]}}
    assert result().extract() == [{"Login": "member-login"}]


def _v5_error(code):
    # v5 errors nest under "error". The adapter reads error["code"]; the
    # exception constructor reads error_code/request_id/error_string/
    # error_detail — both sets of keys must be present.
    return {
        "error": {
            "code": code,
            "error_code": code,
            "request_id": "test-request-id",
            "error_string": "Limit exceeded",
            "error_detail": "test detail",
        }
    }


@pytest.mark.parametrize("code", [506, 56, 9000])
@responses.activate
def test_v5_persistent_limit_stops_and_raises(monkeypatch, code):
    # Regression guard for issue #23: a persistent limit code must NOT loop
    # forever. With retries_if_exceeded_limit=2 the adapter makes exactly
    # 2 HTTP calls then raises, instead of hanging. Codes 506/56/9000 each go
    # through their own elif branch but share the retries_if_exceeded_limit
    # budget, so all three are exercised.
    monkeypatch.setattr(adapter_mod.time, "sleep", lambda _s: None)

    for _ in range(5):
        responses.add(
            responses.POST,
            "https://api.direct.yandex.com/json/v5/clients",
            json=_v5_error(code),
            status=200,
        )

    local_client = YandexDirect(
        access_token="",
        retry_if_exceeded_limit=True,
        retries_if_exceeded_limit=2,
        retries_if_server_error=5,
    )
    with pytest.raises(exc.YandexDirectRequestsLimitError):
        local_client.clients().post(
            data={"method": "get", "params": {"FieldNames": ["ClientId"]}}
        )
    assert len(responses.calls) == 2


@responses.activate
def test_v5_limit_506_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(adapter_mod.time, "sleep", lambda _s: None)

    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json=_v5_error(506),
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": []}},
        status=200,
    )

    local_client = YandexDirect(
        access_token="",
        retry_if_exceeded_limit=True,
        retries_if_exceeded_limit=5,
        retries_if_server_error=5,
    )
    result = local_client.clients().post(
        data={"method": "get", "params": {"FieldNames": ["ClientId"]}}
    )
    assert result().extract() == []
    assert len(responses.calls) == 2


@responses.activate
def test_v5_limit_506_raises_when_retry_disabled():
    # Module-level `client` has retry_if_exceeded_limit=False, so a limit code
    # is raised immediately with no retry.
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json=_v5_error(506),
        status=200,
    )
    with pytest.raises(exc.YandexDirectRequestsLimitError):
        client.clients().post(
            data={"method": "get", "params": {"FieldNames": ["ClientId"]}}
        )
    assert len(responses.calls) == 1


@responses.activate
def test_v5_persistent_units_152_stops_and_raises(monkeypatch):
    # Regression guard for issue #23: code 152 ("not enough units") is opt-in
    # (retry_if_not_enough_units) and now bounded by its own
    # retries_if_not_enough_units budget — it must stop, not loop forever.
    monkeypatch.setattr(adapter_mod.time, "sleep", lambda _s: None)

    for _ in range(5):
        responses.add(
            responses.POST,
            "https://api.direct.yandex.com/json/v5/clients",
            json=_v5_error(152),
            status=200,
        )

    local_client = YandexDirect(
        access_token="",
        retry_if_not_enough_units=True,
        retries_if_not_enough_units=2,
        retries_if_server_error=5,
    )
    with pytest.raises(exc.YandexDirectNotEnoughUnitsError):
        local_client.clients().post(
            data={"method": "get", "params": {"FieldNames": ["ClientId"]}}
        )
    assert len(responses.calls) == 2
