"""Docs-driven v4/v4 Live JSON contract tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

from tapi_yandex_direct.v4 import SUPPORTED_V4_METHODS
from tapi_yandex_direct.v4.adapter import V4LiveClientAdapter


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "docs" / "v4_json_contracts.json"
AUDIT_SCRIPT_PATH = ROOT / "scripts" / "audit_v4_json_docs.py"


spec = importlib.util.spec_from_file_location("audit_v4_json_docs", AUDIT_SCRIPT_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load audit_v4_json_docs from {AUDIT_SCRIPT_PATH}")
audit_v4_json_docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_v4_json_docs)


def _snapshot() -> dict:
    return audit_v4_json_docs.load_snapshot(SNAPSHOT_PATH)


def _contracts() -> list[dict]:
    return _snapshot()["contracts"]


def _contract(method: str, variant: str = "live") -> dict:
    matches = [
        contract
        for contract in _contracts()
        if contract["method"] == method and contract["variant"] == variant
    ]
    assert len(matches) == 1
    return matches[0]


def _field_names(contract: dict) -> set[str]:
    return {field["name"] for field in contract["param_fields"]}


def test_v4_json_docs_snapshot_is_internally_valid():
    assert audit_v4_json_docs.validate_snapshot(_snapshot()) == []


def test_v4_json_docs_snapshot_reports_missing_method_without_crashing():
    snapshot = {
        "contracts": [
            {
                "variant": "live",
                "source_url": "https://yandex.com/dev/direct/doc/dg-v4/en/live/Broken",
                "request": {"method": "Broken"},
                "param_shape": "object",
                "param_fields": [],
                "required_fields": [],
            }
        ]
    }

    errors = audit_v4_json_docs.validate_snapshot(snapshot)

    assert "contracts[0] missing method" in errors


def test_v4_json_docs_refresh_refuses_non_official_urls_before_fetch():
    snapshot = {
        "contracts": [
            {
                "method": "GetEventsLog",
                "source_url": "https://example.com/not-yandex",
                "param_fields": [],
            }
        ]
    }

    with patch.object(audit_v4_json_docs, "_fetch_text") as fetch_text:
        try:
            audit_v4_json_docs.refresh_from_online(snapshot, timeout=1)
        except ValueError as err:
            assert "Refusing to fetch unexpected URL" in str(err)
        else:
            raise AssertionError("refresh_from_online accepted a non-official URL")

    fetch_text.assert_not_called()


def test_v4_json_docs_snapshot_covers_supported_methods():
    grouped = audit_v4_json_docs.contracts_by_method(_snapshot())

    assert set(grouped) == set(SUPPORTED_V4_METHODS)
    for method, contracts in grouped.items():
        assert contracts
        for contract in contracts:
            assert contract["request"]["method"] == method
            assert contract["source_url"].startswith(
                "https://yandex.com/dev/direct/doc/dg-v4/en/"
            )


def test_supported_v4_methods_are_no_v5_analogue_in_wsdl_audit():
    audit_wsdl_path = ROOT / "scripts" / "audit_wsdl.py"
    spec = importlib.util.spec_from_file_location("audit_wsdl", audit_wsdl_path)
    audit_wsdl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit_wsdl)

    for method in SUPPORTED_V4_METHODS:
        assert method in audit_wsdl.V4_TO_V5_MAP
        assert audit_wsdl.V4_TO_V5_MAP[method] is None


def test_supported_v4_methods_are_actual_candidates_in_matrix():
    statuses = audit_v4_json_docs.parse_matrix_statuses(
        ROOT / "docs" / "v4_methods_matrix.md"
    )

    for method in SUPPORTED_V4_METHODS:
        assert statuses[method] == "actual_no_v5_analogue"


def test_get_stat_goals_keeps_reference_and_live_param_spellings():
    reference = _contract("GetStatGoals", "reference")
    live = _contract("GetStatGoals", "live")

    assert reference["required_fields"] == ["CampaignID"]
    assert _field_names(reference) == {"CampaignID"}
    assert live["required_fields"] == ["CampaignIDS"]
    assert _field_names(live) == {"CampaignIDS"}


def test_get_retargeting_goals_live_uses_logins_param():
    live = _contract("GetRetargetingGoals", "live")

    assert live["param_shape"] == "object"
    assert live["required_fields"] == ["Logins"]
    assert _field_names(live) == {"Logins"}


def test_get_events_log_live_documents_required_and_optional_fields():
    live = _contract("GetEventsLog", "live")

    assert live["required_fields"] == ["TimestampFrom", "Currency"]
    assert {
        "TimestampFrom",
        "Currency",
        "Logins",
        "Filter",
        "Filter.CampaignIDS",
        "Filter.BannerIDS",
        "Filter.Phrases",
        "Filter.EventTypes",
        "Limit",
        "Offset",
    } <= _field_names(live)


def test_adapter_adds_transport_fields_without_mutating_param_shape():
    adapter = V4LiveClientAdapter()
    api_params = {
        "access_token": "token",
        "login": "client-login",
        "language": "en",
        "is_sandbox": False,
    }
    param = {"Logins": ["client-login"]}

    request = adapter.get_request_kwargs(
        api_params,
        data={"method": "GetRetargetingGoals", "param": param},
    )
    body = json.loads(request["data"])

    assert body["method"] == "GetRetargetingGoals"
    assert body["param"] == {"Logins": ["client-login"]}
    assert param == {"Logins": ["client-login"]}
    assert body["token"] == "token"
    assert body["locale"] == "en"
    assert request["headers"]["Client-Login"] == "client-login"
