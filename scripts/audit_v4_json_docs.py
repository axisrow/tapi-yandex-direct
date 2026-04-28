"""Audit the local v4/v4 Live JSON documentation snapshot.

The v4 WSDL tells us which operations exist. It does not describe the JSON
RPC request body accurately enough for v4 Live, where every operation goes to
one endpoint and the method-specific payload lives under ``param``. This helper
therefore treats ``docs/v4_json_contracts.json`` as the local source of truth
for method/param shape and cross-checks it against the WSDL-derived matrix.

Default mode is offline and CI-safe. ``--refresh-from-online`` only fetches the
official source pages and records a refresh timestamp; schema changes still
need a human to review and edit the JSON snapshot.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "docs" / "v4_json_contracts.json"
DEFAULT_MATRIX = ROOT / "docs" / "v4_methods_matrix.md"
AUDIT_WSDL = ROOT / "scripts" / "audit_wsdl.py"
OFFICIAL_V4_DOCS_PREFIX = "https://yandex.com/dev/direct/doc/dg-v4/en/"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VALID_VARIANTS = {"reference", "live"}
VALID_PARAM_SHAPES = {"array", "object", "optional-empty", "scalar", "unknown"}


def load_snapshot(path: Path = DEFAULT_SNAPSHOT) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_snapshot(snapshot: dict[str, Any], path: Path = DEFAULT_SNAPSHOT) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _load_audit_wsdl():
    spec = importlib.util.spec_from_file_location("audit_wsdl", AUDIT_WSDL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {AUDIT_WSDL}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_supported_methods() -> dict[str, dict[str, Any]]:
    from tapi_yandex_direct.v4 import SUPPORTED_V4_METHODS

    return SUPPORTED_V4_METHODS


def parse_matrix_statuses(path: Path = DEFAULT_MATRIX) -> dict[str, str]:
    statuses: dict[str, str] = {}
    row_re = re.compile(r"^\|\s*\d+\s*\|\s*`([^`]+)`\s*\|[^|]*\|\s*([^|]+?)\s*\|")
    in_full_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "## Full method table":
            in_full_table = True
            continue
        if in_full_table and line.startswith("## "):
            break
        if not in_full_table:
            continue
        match = row_re.match(line)
        if match:
            statuses[match.group(1)] = match.group(2).strip()
    return statuses


def contracts_by_method(snapshot: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for contract in snapshot.get("contracts", []):
        grouped.setdefault(contract.get("method"), []).append(contract)
    return grouped


def validate_snapshot(
    snapshot: dict[str, Any] | None = None,
    *,
    matrix_path: Path = DEFAULT_MATRIX,
) -> list[str]:
    snapshot = snapshot or load_snapshot()
    errors: list[str] = []
    supported = load_supported_methods()
    audit_wsdl = _load_audit_wsdl()
    matrix_statuses = parse_matrix_statuses(matrix_path)
    grouped = contracts_by_method(snapshot)

    missing = sorted(set(supported) - set(grouped))
    stale = sorted(key for key in set(grouped) - set(supported) if key is not None)
    if missing:
        errors.append(f"Snapshot misses supported methods: {missing}")
    if stale:
        errors.append(f"Snapshot has stale methods: {stale}")

    for method in sorted(supported):
        if method not in audit_wsdl.V4_TO_V5_MAP:
            errors.append(f"{method} missing from V4_TO_V5_MAP")
        elif audit_wsdl.V4_TO_V5_MAP[method] is not None:
            errors.append(
                f"{method} is supported but maps to v5 "
                f"{audit_wsdl.V4_TO_V5_MAP[method]!r}"
            )

        if matrix_statuses.get(method) != "actual_no_v5_analogue":
            errors.append(
                f"{method} matrix status is "
                f"{matrix_statuses.get(method)!r}, expected actual_no_v5_analogue"
            )

    seen_keys: set[tuple[str, str]] = set()
    for index, contract in enumerate(snapshot.get("contracts", [])):
        label = f"contracts[{index}]"
        method = contract.get("method")
        variant = contract.get("variant")
        key = (method, variant)
        if key in seen_keys:
            errors.append(f"{label} duplicates {method}/{variant}")
        seen_keys.add(key)

        if not method:
            errors.append(f"{label} missing method")
        if variant not in VALID_VARIANTS:
            errors.append(f"{label} has invalid variant {variant!r}")
        if not str(contract.get("source_url", "")).startswith(OFFICIAL_V4_DOCS_PREFIX):
            errors.append(f"{label} has invalid source_url")
        request = contract.get("request")
        if not isinstance(request, dict) or request.get("method") != method:
            errors.append(f"{label} request.method must equal method")
        if contract.get("param_shape") not in VALID_PARAM_SHAPES:
            errors.append(f"{label} has invalid param_shape")

        fields = contract.get("param_fields")
        if not isinstance(fields, list):
            errors.append(f"{label} param_fields must be a list")
            fields = []
        field_names = [field.get("name") for field in fields if isinstance(field, dict)]
        required = contract.get("required_fields")
        if not isinstance(required, list):
            errors.append(f"{label} required_fields must be a list")
            required = []
        missing_required = sorted(set(required) - set(field_names))
        if missing_required:
            errors.append(f"{label} required fields absent from param_fields: {missing_required}")

    return errors


def _fetch_text(url: str, timeout: int) -> str:
    request = Request(url, headers={"User-Agent": "tapi-yandex-direct-audit/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def refresh_from_online(snapshot: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    refreshed = json.loads(json.dumps(snapshot))
    for contract in refreshed.get("contracts", []):
        source_url = contract["source_url"]
        if not str(source_url).startswith(OFFICIAL_V4_DOCS_PREFIX):
            raise ValueError(f"Refusing to fetch unexpected URL: {source_url!r}")
        html = _fetch_text(source_url, timeout)
        contract["online_check"] = {
            "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "method_found": contract["method"] in html,
            "fields_found": [
                field["name"]
                for field in contract.get("param_fields", [])
                if isinstance(field, dict) and field.get("name") in html
            ],
        }
    refreshed.setdefault("metadata", {})["refreshed_at"] = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )
    return refreshed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--refresh-from-online", action="store_true")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args(argv)

    snapshot = load_snapshot(args.snapshot)
    if args.refresh_from_online:
        snapshot = refresh_from_online(snapshot, timeout=args.timeout)
        write_snapshot(snapshot, args.output or args.snapshot)

    errors = validate_snapshot(snapshot)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(
        f"v4 JSON docs snapshot OK: "
        f"{len(contracts_by_method(snapshot))} supported methods covered"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
