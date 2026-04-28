"""Optional live integration tests for v4 Live JSON client.

Skipped automatically unless both ``YANDEX_DIRECT_TOKEN`` and
``YANDEX_DIRECT_LOGIN`` are in the environment, so CI never hits the real API.
Run locally with::

    export YANDEX_DIRECT_TOKEN=...   (real OAuth token)
    export YANDEX_DIRECT_LOGIN=...   (account login)
    export YANDEX_DIRECT_SANDBOX=1   (optional; use sandbox endpoints)
    pytest tests/test_v4_live_integration.py -v -m live

The probes intentionally cover only **read-only** v4 Live operations and one
schema-only check for ``CheckPayment``. They double as living documentation of
the correct request shapes — call schemas come from the official Yandex Direct
v4 Live docs (https://yandex.com/dev/direct/doc/dg-v4/en/live/...).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.skipif(
    not (os.environ.get("YANDEX_DIRECT_TOKEN") and os.environ.get("YANDEX_DIRECT_LOGIN")),
    reason=(
        "set both YANDEX_DIRECT_TOKEN and YANDEX_DIRECT_LOGIN "
        "to run against the real Yandex Direct API"
    ),
)


@pytest.fixture(scope="module")
def v4_kwargs() -> dict:
    return {
        "access_token": os.environ["YANDEX_DIRECT_TOKEN"],
        "login": os.environ["YANDEX_DIRECT_LOGIN"],
        "is_sandbox": os.environ.get("YANDEX_DIRECT_SANDBOX", "").lower()
        in {"1", "true", "yes"},
    }


@pytest.fixture(scope="module")
def v4_client(v4_kwargs):
    from tapi_yandex_direct import YandexDirectV4Live
    return YandexDirectV4Live(**v4_kwargs)


@pytest.fixture(scope="module")
def real_ids(v4_kwargs) -> dict:
    """Resolve a real CampaignID and BannerID via the v5 client.

    v4 Live tag/goal probes need real entities; v5 is the cleanest source.
    """
    from tapi_yandex_direct import YandexDirect
    from tapi_yandex_direct import exceptions as exc

    v5 = YandexDirect(**v4_kwargs)
    try:
        camps = v5.campaigns().post(data={
            "method": "get",
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Id"],
                "Page": {"Limit": 1},
            },
        })
    except exc.YandexDirectClientError as err:
        pytest.skip(f"could not resolve real campaign ids via v5: {err}")
    camp_list = camps().extract()
    if not camp_list:
        pytest.skip("account has no campaigns to probe against")
    cid: int = camp_list[0]["Id"]

    try:
        ads = v5.ads().post(data={
            "method": "get",
            "params": {
                "SelectionCriteria": {"CampaignIds": [cid]},
                "FieldNames": ["Id"],
                "Page": {"Limit": 1},
            },
        })
    except exc.YandexDirectClientError as err:
        pytest.skip(f"could not resolve real banner ids via v5: {err}")
    ads_list = ads().extract()
    bid = ads_list[0]["Id"] if ads_list else None
    return {"campaign_id": cid, "banner_id": bid}


# ------- methods that work without any real entity -------

@pytest.mark.live
def test_get_clients_units(v4_client, v4_kwargs):
    res = v4_client.v4live().post(data={
        "method": "GetClientsUnits", "param": [v4_kwargs["login"]],
    })
    extracted = res().extract()
    assert isinstance(extracted, list) and extracted
    assert extracted[0]["Login"] == v4_kwargs["login"]
    assert isinstance(extracted[0]["UnitsRest"], int)


@pytest.mark.live
@pytest.mark.parametrize("method", [
    "GetWordstatReportList",
    "GetForecastList",
    "PingAPI",
    "GetVersion",
    "GetAvailableVersions",
])
def test_methods_with_empty_param(v4_client, method):
    res = v4_client.v4live().post(data={"method": method, "param": []})
    # All five succeed; payload shape varies (list/int/list-of-versions),
    # we only assert no exception and that data field is present.
    assert "data" in res.data


# ------- methods that need a real CampaignID / BannerID -------

@pytest.mark.live
def test_get_stat_goals(v4_client, real_ids):
    """Per docs: GetStatGoals takes ``CampaignIDS`` (array), not ``CampaignID``."""
    res = v4_client.v4live().post(data={
        "method": "GetStatGoals",
        "param": {"CampaignIDS": [real_ids["campaign_id"]]},
    })
    extracted = res().extract()
    assert isinstance(extracted, list)
    if extracted:
        assert "GoalID" in extracted[0]
        assert extracted[0]["CampaignID"] == real_ids["campaign_id"]


@pytest.mark.live
def test_get_retargeting_goals(v4_client, v4_kwargs):
    """Per live JSON docs: GetRetargetingGoals uses Logins."""
    res = v4_client.v4live().post(data={
        "method": "GetRetargetingGoals",
        "param": {"Logins": [v4_kwargs["login"]]},
    })
    goals = res().extract()
    assert isinstance(goals, list)
    if goals:
        assert "GoalID" in goals[0]


@pytest.mark.live
def test_get_campaigns_tags(v4_client, real_ids):
    """Per docs: ``CampaignIDS`` (capital S), not ``CampaignIDs``."""
    res = v4_client.v4live().post(data={
        "method": "GetCampaignsTags",
        "param": {"CampaignIDS": [real_ids["campaign_id"]]},
    })
    extracted = res().extract()
    # Empty list is a valid response (campaign has no tags) — only assert
    # element shape when something came back.
    assert isinstance(extracted, list)
    if extracted:
        assert extracted[0]["CampaignID"] == real_ids["campaign_id"]
        assert "Tags" in extracted[0]


@pytest.mark.live
def test_get_banners_tags(v4_client, real_ids):
    """Per docs: ``BannerIDS`` (capital S)."""
    if real_ids["banner_id"] is None:
        pytest.skip("account campaign has no ads to probe")
    res = v4_client.v4live().post(data={
        "method": "GetBannersTags",
        "param": {"BannerIDS": [real_ids["banner_id"]]},
    })
    extracted = res().extract()
    # Empty list is valid (banner has no tags).
    assert isinstance(extracted, list)
    if extracted:
        assert extracted[0]["BannerID"] == real_ids["banner_id"]


# ------- methods with non-trivial schemas -------

@pytest.mark.live
def test_get_events_log(v4_client, v4_kwargs):
    """Per docs: TimestampFrom must be ISO 8601 AND Currency is required."""
    ts = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    param = {"TimestampFrom": ts, "Currency": "RUB", "Limit": 3}
    if v4_kwargs["is_sandbox"]:
        param["Logins"] = [v4_kwargs["login"]]
    res = v4_client.v4live().post(data={
        "method": "GetEventsLog",
        "param": param,
    })
    events = res().extract()
    assert isinstance(events, list)


@pytest.mark.live
def test_get_keywords_suggestion(v4_client):
    """Per docs: parameter name is ``Keywords`` (a list of phrases)."""
    res = v4_client.v4live().post(data={
        "method": "GetKeywordsSuggestion",
        "param": {"Keywords": ["купить смартфон"]},
    })
    suggestions = res().extract()
    assert isinstance(suggestions, list)


# ------- schema-only checks: we verify the adapter doesn't crash -------

@pytest.mark.live
def test_check_payment_schema_only(v4_client):
    """CheckPayment requires real CustomTransactionID; we send a placeholder
    and expect a structured V4LiveError, not a Python exception."""
    from tapi_yandex_direct import exceptions as exc
    with pytest.raises(exc.V4LiveError) as info:
        v4_client.v4live().post(data={
            "method": "CheckPayment",
            "param": {"OperationNum": 1, "CustomTransactionID": "probe-not-real"},
        })
    assert info.value.error_code != 0


@pytest.mark.live
def test_get_credit_limits_requires_finance_token(v4_client):
    """GetCreditLimits requires a separate finance OAuth token. With a regular
    access_token Yandex returns ``error_code=350``."""
    from tapi_yandex_direct import exceptions as exc
    with pytest.raises(exc.V4LiveError) as info:
        v4_client.v4live().post(data={
            "method": "GetCreditLimits", "param": [],
        })
    # 350 = "Invalid financial transaction token"
    assert info.value.error_code == 350
