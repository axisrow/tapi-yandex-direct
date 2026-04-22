#!/usr/bin/env python3
"""
WSDL Audit Script for tapi-yandex-direct.

Compares library coverage against Yandex Direct API v5 WSDL definitions.
Prints a Markdown report to stdout. Optionally creates a GitHub issue.

Usage:
    python scripts/audit_wsdl.py
    python scripts/audit_wsdl.py --output report.md
    python scripts/audit_wsdl.py --issue
"""

import argparse
import subprocess
import sys
from datetime import date
from xml.etree import ElementTree as ET

import requests

WSDL_BASE_URL = "https://api.direct.yandex.com/v5/{service}?wsdl"
GITHUB_API_URL = "https://api.github.com/repos/dragonsigh/yandex-direct-api-docs/contents/"

WSDL_NS = "http://schemas.xmlsoap.org/wsdl/"

# Folders in the docs repo that are NOT API services
DOCS_REPO_NON_SERVICE_DIRS = {
    "concepts", "objects", "images", ".github", "examples",
    "reports", "changes", "dictionaries",
}

# Resource types for clear categorization
# wsdl       — SOAP/WSDL service, auditable
# reports    — Reports API (TSV, not SOAP), no WSDL by design
# oauth      — OAuth helper, not an API service
RESOURCE_CATALOG: dict[str, dict] = {
    # python_name -> {endpoint, type, methods}
    "adextensions":            {"endpoint": "adextensions",           "type": "wsdl", "methods": {"get", "add", "delete"}},
    "adgroups":                {"endpoint": "adgroups",               "type": "wsdl", "methods": {"get", "add", "update", "delete"}},
    "adimages":                {"endpoint": "adimages",               "type": "wsdl", "methods": {"get", "add", "delete"}},
    "advideos":                {"endpoint": "advideos",               "type": "wsdl", "methods": {"get", "add"}},
    "ads":                     {"endpoint": "ads",                    "type": "wsdl", "methods": {"get", "add", "update", "delete", "moderate", "suspend", "resume", "archive", "unarchive"}},
    "agencyclients":           {"endpoint": "agencyclients",          "type": "wsdl", "methods": {"get", "add", "update"}},
    "audiencetargets":         {"endpoint": "audiencetargets",        "type": "wsdl", "methods": {"get", "add", "delete", "suspend", "resume", "setBids"}},
    "bidmodifiers":            {"endpoint": "bidmodifiers",           "type": "wsdl", "methods": {"get", "add", "set", "delete"}},
    "bids":                    {"endpoint": "bids",                   "type": "wsdl", "methods": {"get", "set", "setAuto"}},
    "businesses":              {"endpoint": "businesses",             "type": "wsdl", "methods": {"get"}},
    "campaigns":               {"endpoint": "campaigns",              "type": "wsdl", "methods": {"get", "add", "update", "delete", "archive", "unarchive", "suspend", "resume"}},
    "changes":                 {"endpoint": "changes",                "type": "wsdl", "methods": {"check", "checkCampaigns", "checkDictionaries"}},
    "clients":                 {"endpoint": "clients",                "type": "wsdl", "methods": {"get", "update"}},
    "creatives":               {"endpoint": "creatives",              "type": "wsdl", "methods": {"get", "add"}},
    "dictionaries":            {"endpoint": "dictionaries",           "type": "wsdl", "methods": {"get"}},
    "dynamicads":              {"endpoint": "dynamictextadtargets",   "type": "wsdl", "methods": {"get", "add", "delete", "suspend", "resume", "setBids"}},
    "feeds":                   {"endpoint": "feeds",                  "type": "wsdl", "methods": {"get", "add", "update", "delete"}},
    "keywordbids":             {"endpoint": "keywordbids",            "type": "wsdl", "methods": {"get", "set", "setAuto"}},
    "keywords":                {"endpoint": "keywords",               "type": "wsdl", "methods": {"get", "add", "update", "delete", "suspend", "resume", "archive", "unarchive"}},
    "keywordsresearch":        {"endpoint": "keywordsresearch",       "type": "wsdl", "methods": {"deduplicate", "hasSearchVolume"}},
    "leads":                   {"endpoint": "leads",                  "type": "wsdl", "methods": {"get"}},
    "negativekeywordsharedsets": {"endpoint": "negativekeywordsharedsets", "type": "wsdl", "methods": {"get", "add", "update", "delete"}},
    "retargeting":             {"endpoint": "retargetinglists",       "type": "wsdl", "methods": {"get", "add", "update", "delete"}},
    "sitelinks":               {"endpoint": "sitelinks",              "type": "wsdl", "methods": {"get", "add", "delete"}},
    "smartadtargets":          {"endpoint": "smartadtargets",         "type": "wsdl", "methods": {"get", "add", "update", "delete", "suspend", "resume", "setBids"}},
    "turbopages":              {"endpoint": "turbopages",             "type": "wsdl", "methods": {"get"}},
    "vcards":                  {"endpoint": "vcards",                 "type": "wsdl", "methods": {"get", "add", "delete"}},
    # Non-WSDL resources
    "reports":                 {"endpoint": "reports",                "type": "reports", "methods": {"get"}},
    "debugtoken":              {"endpoint": "debugtoken",             "type": "oauth",   "methods": set()},
}

WSDL_RESOURCES = {
    name: info for name, info in RESOURCE_CATALOG.items()
    if info["type"] == "wsdl"
}

# Fallback service list if GitHub API is unavailable
FALLBACK_SERVICES = sorted(info["endpoint"] for info in WSDL_RESOURCES.values())


def discover_services_from_github() -> list[str]:
    """Get list of all v5 API services from dragonsigh/yandex-direct-api-docs repo structure."""
    print(f"Fetching service list from GitHub: {GITHUB_API_URL} ...")
    try:
        resp = requests.get(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github+json"},
            timeout=15,
        )
        resp.raise_for_status()
        entries = resp.json()
    except requests.RequestException as e:
        print(f"  Warning: could not fetch GitHub API: {e}")
        print("  Using fallback service list.")
        return FALLBACK_SERVICES

    services = sorted(
        entry["name"]
        for entry in entries
        if entry["type"] == "dir" and entry["name"] not in DOCS_REPO_NON_SERVICE_DIRS
    )

    if not services:
        print("  Warning: no service directories found. Using fallback list.")
        return FALLBACK_SERVICES

    print(f"  Found {len(services)} services: {', '.join(services)}")
    return services


def fetch_wsdl_operations(service: str) -> tuple[set[str], bool]:
    """Fetch WSDL for a service and extract operation names from portType."""
    url = WSDL_BASE_URL.format(service=service)
    try:
        resp = requests.get(url, timeout=15)
    except requests.RequestException as e:
        print(f"  [{service}] Request error: {e}")
        return set(), False

    if resp.status_code == 404:
        return set(), False
    if not resp.ok:
        print(f"  [{service}] HTTP {resp.status_code}")
        return set(), False

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"  [{service}] XML parse error: {e}")
        return set(), False

    operations: set[str] = set()
    for pt in root.findall(f"{{{WSDL_NS}}}portType"):
        for op in pt.findall(f"{{{WSDL_NS}}}operation"):
            name = op.get("name")
            if name:
                operations.add(name)

    return operations, True


def build_report(
    discovered_services: list[str],
    wsdl_results: dict[str, tuple[set[str], bool]],
) -> str:
    today = date.today().isoformat()

    # All endpoints confirmed via WSDL response
    wsdl_endpoints = {name: info for name, info in WSDL_RESOURCES.items()}
    library_endpoints = {info["endpoint"] for info in wsdl_endpoints.values()}

    all_candidates = set(discovered_services) | library_endpoints
    confirmed_endpoints = {
        ep for ep in all_candidates
        if wsdl_results.get(ep, (set(), False))[1]
    }

    # Missing: confirmed via WSDL but not in library
    missing_endpoints = confirmed_endpoints - library_endpoints
    # Extra: in library but WSDL unavailable
    extra_endpoints = library_endpoints - confirmed_endpoints

    # Build per-resource diff table
    # All resources: library wsdl resources + missing (new API services)
    all_resource_endpoints = library_endpoints | missing_endpoints

    rows: list[dict] = []
    for ep in sorted(all_resource_endpoints):
        wsdl_ops, available = wsdl_results.get(ep, (set(), False))

        # Find library entry by endpoint
        lib_entry = next(
            ((name, info) for name, info in WSDL_RESOURCES.items()
             if info["endpoint"] == ep),
            None,
        )

        if lib_entry:
            lib_name, lib_info = lib_entry
            lib_methods = lib_info["methods"]
        else:
            lib_name = None
            lib_methods = set()

        missing_methods = wsdl_ops - lib_methods if available else set()
        extra_methods = lib_methods - wsdl_ops if available else set()
        status = "ok" if available and not missing_methods else ("no_wsdl" if not available else "gap")

        rows.append({
            "endpoint": ep,
            "lib_name": lib_name,
            "lib_methods": lib_methods,
            "wsdl_ops": wsdl_ops,
            "available": available,
            "missing_methods": missing_methods,
            "extra_methods": extra_methods,
            "status": status,
            "in_library": lib_entry is not None,
        })

    n_total_lib = len(RESOURCE_CATALOG)
    n_wsdl_lib = len(WSDL_RESOURCES)
    n_reports = sum(1 for i in RESOURCE_CATALOG.values() if i["type"] == "reports")
    n_oauth = sum(1 for i in RESOURCE_CATALOG.values() if i["type"] == "oauth")
    n_confirmed = len(confirmed_endpoints)
    n_missing_svc = len(missing_endpoints)
    n_extra_svc = len(extra_endpoints)
    n_gap_methods = sum(1 for r in rows if r["missing_methods"])
    n_total_missing_methods = sum(len(r["missing_methods"]) for r in rows)

    lines = [
        "# Yandex Direct API v5 — WSDL Audit Report",
        f"**Date:** {today}",
        "",
        "## Summary",
        "",
        f"| Category | Count |",
        f"|---|---|",
        f"| Total resources in `resource_mapping.py` | {n_total_lib} |",
        f"| — SOAP/WSDL services | {n_wsdl_lib} |",
        f"| — Reports API (non-SOAP) | {n_reports} |",
        f"| — OAuth helpers | {n_oauth} |",
        f"| WSDL-confirmed API services (live check) | {n_confirmed} |",
        f"| Missing services (in API, not in library) | {n_missing_svc} |",
        f"| Extra services (in library, WSDL unavailable) | {n_extra_svc} |",
        f"| Services with missing methods | {n_gap_methods} |",
        f"| Total missing methods | {n_total_missing_methods} |",
        "",
    ]

    # Non-WSDL resources explanation
    lines += [
        "## Non-WSDL Resources",
        "",
        "These resources are implemented in the library but have no WSDL (not SOAP services):",
        "",
    ]
    for i, (name, info) in enumerate(
        ((n, i) for n, i in RESOURCE_CATALOG.items() if i["type"] != "wsdl"), start=1
    ):
        type_label = {"reports": "Reports API (TSV, async)", "oauth": "OAuth helper"}[info["type"]]
        lines.append(f"{i}. **{name}** (`{info['endpoint']}`) — {type_label}")
    lines.append("")

    # Full per-resource diff
    lines += [
        "## Full Resource Diff",
        "",
        "Every SOAP/WSDL resource with its method coverage.",
        "",
    ]

    for i, row in enumerate(rows, start=1):
        ep = row["endpoint"]
        lib_name = row["lib_name"] or "_(not in library)_"
        available = row["available"]
        wsdl_ops = row["wsdl_ops"]
        lib_methods = row["lib_methods"]
        missing_methods = row["missing_methods"]
        extra_methods = row["extra_methods"]

        if not row["in_library"]:
            status_icon = "🆕"
            status_label = "NEW — not in library"
        elif not available:
            status_icon = "❓"
            status_label = "WSDL unavailable"
        elif missing_methods:
            status_icon = "⚠️"
            status_label = "method gap"
        else:
            status_icon = "✅"
            status_label = "ok"

        lines.append(f"### {i}. `{ep}` (lib: `{lib_name}`) {status_icon} {status_label}")
        lines.append("")

        if available:
            lines.append(f"- **WSDL operations ({len(wsdl_ops)}):** `{'`, `'.join(sorted(wsdl_ops))}`")
        else:
            lines.append("- **WSDL:** not available")

        if lib_methods:
            lines.append(f"- **Library declared ({len(lib_methods)}):** `{'`, `'.join(sorted(lib_methods))}`")
        else:
            lines.append("- **Library declared:** none")

        if missing_methods:
            lines.append(f"- **Missing in library ({len(missing_methods)}):** `{'`, `'.join(sorted(missing_methods))}`")

        if extra_methods:
            lines.append(f"- **In library but not in WSDL ({len(extra_methods)}):** `{'`, `'.join(sorted(extra_methods))}`")

        lines.append("")

    return "\n".join(lines)


def create_github_issue(report: str) -> None:
    today = date.today().isoformat()
    title = f"WSDL Audit: API coverage gaps {today}"

    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", report],
            capture_output=True, text=True, check=True,
        )
        print(f"\nGitHub issue created: {result.stdout.strip()}")
    except FileNotFoundError:
        print("\nError: 'gh' CLI not found. Install it from https://cli.github.com/")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\nError creating GitHub issue:\n{e.stderr}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Yandex Direct WSDL coverage")
    parser.add_argument("--issue", action="store_true",
                        help="Create a GitHub issue with the report (requires gh CLI)")
    parser.add_argument("--output", metavar="FILE",
                        help="Save report to file instead of printing to stdout")
    args = parser.parse_args()

    api_services = discover_services_from_github()

    # Fetch WSDL for all candidates: discovered + library endpoints
    library_endpoints = {info["endpoint"] for info in WSDL_RESOURCES.values()}
    all_services = sorted(set(api_services) | library_endpoints)

    wsdl_results: dict[str, tuple[set[str], bool]] = {}
    print(f"\nFetching WSDL for {len(all_services)} services...")
    for service in all_services:
        ops, available = fetch_wsdl_operations(service)
        wsdl_results[service] = (ops, available)
        status = (
            f"{len(ops)} operations: {', '.join(sorted(ops))}"
            if available else "WSDL not available"
        )
        print(f"  [{service}] {status}")

    print("\nBuilding report...")
    report = build_report(api_services, wsdl_results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)

    if args.issue:
        create_github_issue(report)


if __name__ == "__main__":
    main()
