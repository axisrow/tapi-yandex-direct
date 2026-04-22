#!/usr/bin/env python3
"""
WSDL Audit Script for tapi-yandex-direct.

Compares library coverage against official live Yandex Direct API docs and
WSDL definitions.
Prints a Markdown report to stdout. Optionally creates a GitHub issue.

Usage:
    python scripts/audit_wsdl.py
    python scripts/audit_wsdl.py --output report.md
    python scripts/audit_wsdl.py --versions v5,v501,v4
    python scripts/audit_wsdl.py --issue
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections import deque
from datetime import date
from html.parser import HTMLParser
from typing import NamedTuple
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import requests

DOCS_BASE_URL = "https://yandex.com/dev/direct/doc/en/"
V4_DOCS_BASE_URL = "https://yandex.com/dev/direct/doc/dg-v4/en/"

WSDL_NS = "http://schemas.xmlsoap.org/wsdl/"
SERVICE_LINK_RE = re.compile(r"/dev/direct/doc/en/([^/#?]+)/\1(?:[#?].*)?$")
V4_METHOD_LINK_RE = re.compile(r"/dev/direct/doc/dg-v4/en/(?:reference|live)/([^/#?]+)")
WSDL_URL_RE = re.compile(r"https://api\.direct\.yandex\.com/(v\d+)/([^/?#]+)\?wsdl")
SOAP_URL_RE = re.compile(r"https://api\.direct\.yandex\.com/(?!json/)(v\d+)/([^/?#\s]+)")
JSON_URL_RE = re.compile(r"https://api\.direct\.yandex\.com/json/(v\d+)/([^/?#\s]+)")
METHOD_NAME_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)?\b")

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
    "agencyclients":           {"endpoint": "agencyclients",          "type": "wsdl", "methods": {"get", "add", "update", "addPassportOrganization", "addPassportOrganizationMember"}},
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
    "strategies":              {"endpoint": "strategies",             "type": "wsdl", "methods": {"get", "add", "update", "archive", "unarchive"}},
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

# Method names that look like operations but are actually enum values
# or parameter-driven behaviors — do not flag as "missing".
KNOWN_NON_WSDL_METHODS: dict[str, set[str]] = {
    "dictionaries": {"getGeoRegions"},
}


class DiscoveredService(NamedTuple):
    version: str
    name: str
    endpoint: str
    docs_url: str
    methods: set[str]
    wsdl_url: str
    soap_url: str | None
    json_url: str | None


class LegacyMethod(NamedTuple):
    name: str
    docs_url: str


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href:
            text = " ".join(" ".join(self._current_text).split())
            self.links.append((self._current_href, text))
            self._current_href = None
            self._current_text = []


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)

    @property
    def text(self) -> str:
        return " ".join(self.parts)


def _html_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    return parser.text


def _docs_root(base_url: str, lang: str = "en") -> str:
    marker = f"/{lang}/"
    if marker in base_url:
        return base_url.split(marker, 1)[0] + "/"
    return base_url if base_url.endswith("/") else base_url + "/"


def _normalize_docs_url(href: str, base_url: str, lang: str = "en") -> str:
    if re.match(rf"^{lang}/", href):
        absolute = urljoin(_docs_root(base_url, lang), href)
    else:
        absolute = urljoin(base_url, href)

    parsed = urlparse(absolute)
    return parsed._replace(query="", fragment="").geturl()


def _extract_service_name(text: str, docs_url: str) -> str:
    match = re.search(r"(?:^|\s)([A-Z][A-Za-z0-9]+):", text)
    if match:
        return match.group(1).strip()

    path_parts = [part for part in urlparse(docs_url).path.split("/") if part]
    endpoint = path_parts[-1] if path_parts else "unknown"
    return endpoint[:1].upper() + endpoint[1:]


def _extract_methods(text: str) -> set[str]:
    match = re.search(r"Methods[:.]?\s*(.*?)(?:WSDL|SOAP|JSON|Request|Restrictions|$)", text)
    if not match:
        return set()

    methods = set()
    for candidate in METHOD_NAME_RE.findall(match.group(1)):
        if candidate.lower() in {"methods", "method", "and", "or"}:
            continue
        methods.add(candidate)
    return methods


def _extract_methods_from_links(links: list[tuple[str, str]], docs_url: str) -> set[str]:
    path_parts = [part for part in urlparse(docs_url).path.split("/") if part]
    if not path_parts:
        return set()

    endpoint = path_parts[-1]
    methods: set[str] = set()
    for href, text in links:
        path = urlparse(_normalize_docs_url(href, docs_url)).path
        parts = [part for part in path.split("/") if part]
        if len(parts) < 2 or parts[-2] != endpoint:
            continue

        method = parts[-1]
        if method == endpoint:
            continue
        if not METHOD_NAME_RE.fullmatch(method):
            continue
        methods.add(method)

    return methods


def parse_v5_service_links(html: str, base_url: str = DOCS_BASE_URL) -> list[str]:
    """Extract official v5 service page links from Yandex docs navigation."""
    parser = _LinkParser()
    parser.feed(html)

    links: list[str] = []
    seen: set[str] = set()
    for href, _text in parser.links:
        absolute = _normalize_docs_url(href, base_url)
        if not SERVICE_LINK_RE.search(urlparse(absolute).path):
            continue
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)

    return links


def parse_v4_method_links(html: str, base_url: str = V4_DOCS_BASE_URL) -> list[LegacyMethod]:
    """Extract legacy v4 method links from official Yandex Direct v4 docs."""
    parser = _LinkParser()
    parser.feed(html)

    methods: list[LegacyMethod] = []
    seen: set[str] = set()
    for href, text in parser.links:
        absolute = _normalize_docs_url(href, base_url)
        match = V4_METHOD_LINK_RE.search(urlparse(absolute).path)
        if not match:
            continue
        slug = match.group(1)
        if slug in {"_AllMethods", "ErrorCodes"}:
            continue
        name = text.strip() or slug
        if not name or name in seen:
            continue
        seen.add(name)
        methods.append(LegacyMethod(name=name, docs_url=absolute))

    return methods


def parse_v5_service_page(html: str, docs_url: str) -> list[DiscoveredService]:
    """Extract versioned WSDL/SOAP/JSON service records from a service docs page."""
    text = _html_text(html)
    link_parser = _LinkParser()
    link_parser.feed(html)
    link_text = " ".join(href for href, _text in link_parser.links)
    all_text = f"{text} {link_text}"
    name = _extract_service_name(text, docs_url)
    methods = _extract_methods_from_links(link_parser.links, docs_url) or _extract_methods(text)

    soap_urls: dict[tuple[str, str], str] = {}
    for version, endpoint in SOAP_URL_RE.findall(all_text):
        soap_urls.setdefault((version, endpoint), f"https://api.direct.yandex.com/{version}/{endpoint}")

    json_urls: dict[tuple[str, str], str] = {}
    for version, endpoint in JSON_URL_RE.findall(all_text):
        json_urls[(version, endpoint)] = f"https://api.direct.yandex.com/json/{version}/{endpoint}"

    services: list[DiscoveredService] = []
    seen: set[tuple[str, str]] = set()
    for version, endpoint in WSDL_URL_RE.findall(all_text):
        key = (version, endpoint)
        if key in seen:
            continue
        seen.add(key)
        services.append(DiscoveredService(
            version=version,
            name=name,
            endpoint=endpoint,
            docs_url=docs_url,
            methods=set(methods),
            wsdl_url=f"https://api.direct.yandex.com/{version}/{endpoint}?wsdl",
            soap_url=soap_urls.get(key),
            json_url=json_urls.get(key),
        ))

    return services


def _get_text(url: str, timeout: int) -> str:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def discover_v5_services_from_docs(base_url: str, timeout: int) -> list[DiscoveredService]:
    """Load official Yandex docs and extract all versioned service records."""
    print(f"Fetching official Yandex Direct docs index: {base_url} ...", file=sys.stderr)
    try:
        index_html = _get_text(base_url, timeout)
    except requests.RequestException as e:
        raise RuntimeError(f"Could not discover services from official Yandex docs: {e}") from e

    service_links = parse_v5_service_links(index_html, base_url)
    if not service_links:
        raise RuntimeError("Could not discover services from official Yandex docs: no service links found")

    print(f"  Found {len(service_links)} seed service page(s).", file=sys.stderr)
    services: list[DiscoveredService] = []
    queued = deque(service_links)
    seen_links = set(service_links)
    processed_links: set[str] = set()

    while queued:
        link = queued.popleft()
        if link in processed_links:
            continue
        processed_links.add(link)
        try:
            page_html = _get_text(link, timeout)
        except requests.RequestException as e:
            print(f"  Warning: could not fetch service page {link}: {e}", file=sys.stderr)
            continue

        for discovered_link in parse_v5_service_links(page_html, base_url):
            if discovered_link not in seen_links:
                seen_links.add(discovered_link)
                queued.append(discovered_link)

        parsed = parse_v5_service_page(page_html, link)
        services.extend(parsed)
        print(f"  [{link}] {len(parsed)} WSDL URL(s)", file=sys.stderr)

    if not services:
        raise RuntimeError("Could not discover services from official Yandex docs: no WSDL URLs found")

    # Deduplicate by (version, endpoint), keeping the first occurrence (canonical page)
    seen: set[tuple[str, str]] = set()
    deduped: list[DiscoveredService] = []
    for svc in services:
        key = (svc.version, svc.endpoint)
        if key not in seen:
            seen.add(key)
            deduped.append(svc)
    return deduped


def discover_v4_methods_from_docs(base_url: str, timeout: int) -> list[LegacyMethod]:
    """Load official Yandex Direct v4 docs and extract legacy method records."""
    print(f"Fetching official Yandex Direct v4 docs index: {base_url} ...", file=sys.stderr)
    try:
        index_html = _get_text(base_url, timeout)
    except requests.RequestException as e:
        print(f"  Warning: could not fetch v4 docs: {e}", file=sys.stderr)
        return []

    methods = parse_v4_method_links(index_html, base_url)
    all_methods_url = _normalize_docs_url("en/reference/_AllMethods", base_url)
    try:
        all_methods_html = _get_text(all_methods_url, timeout)
    except requests.RequestException as e:
        print(f"  Warning: could not fetch v4 methods page {all_methods_url}: {e}", file=sys.stderr)
    else:
        known = {method.docs_url for method in methods}
        for method in parse_v4_method_links(all_methods_html, base_url):
            if method.docs_url not in known:
                methods.append(method)
                known.add(method.docs_url)

    print(f"  Found {len(methods)} v4 method links.", file=sys.stderr)
    return methods


def parse_wsdl_operations(content: bytes) -> set[str]:
    root = ET.fromstring(content)
    operations: set[str] = set()
    for pt in root.findall(f"{{{WSDL_NS}}}portType"):
        for op in pt.findall(f"{{{WSDL_NS}}}operation"):
            name = op.get("name")
            if name:
                operations.add(name)
    return operations


def fetch_wsdl_operations(wsdl_url: str, timeout: int = 15) -> tuple[set[str], bool]:
    """Fetch WSDL URL and extract operation names from portType."""
    try:
        resp = requests.get(wsdl_url, timeout=timeout)
    except requests.RequestException as e:
        print(f"  [{wsdl_url}] Request error: {e}", file=sys.stderr)
        return set(), False

    if resp.status_code == 404:
        return set(), False
    if not resp.ok:
        print(f"  [{wsdl_url}] HTTP {resp.status_code}", file=sys.stderr)
        return set(), False

    try:
        operations = parse_wsdl_operations(resp.content)
    except ET.ParseError as e:
        print(f"  [{wsdl_url}] XML parse error: {e}", file=sys.stderr)
        return set(), False

    return operations, True


def _library_entry(endpoint: str) -> tuple[str, dict] | None:
    return next(
        ((name, info) for name, info in WSDL_RESOURCES.items() if info["endpoint"] == endpoint),
        None,
    )


def _coverage_rows(
    version: str,
    discovered_services: list[DiscoveredService],
    wsdl_results: dict[str, tuple[set[str], bool]],
) -> list[dict]:
    services_by_endpoint = {
        service.endpoint: service
        for service in discovered_services
        if service.version == version
    }
    library_endpoints = {info["endpoint"] for info in WSDL_RESOURCES.values()}
    all_endpoints = sorted(set(services_by_endpoint) | library_endpoints)

    rows: list[dict] = []
    for endpoint in all_endpoints:
        service = services_by_endpoint.get(endpoint)
        lib_entry = _library_entry(endpoint)

        if lib_entry:
            lib_name, lib_info = lib_entry
            lib_methods = lib_info["methods"]
        else:
            lib_name = None
            lib_methods = set()

        if service:
            wsdl_ops, available = wsdl_results.get(service.wsdl_url, (set(), False))
            official_methods = wsdl_ops if available else service.methods
        else:
            wsdl_ops, available = set(), False
            official_methods = set()

        pseudo = KNOWN_NON_WSDL_METHODS.get(lib_name, set()) if lib_name else set()
        missing_methods = official_methods - lib_methods - pseudo
        extra_methods = lib_methods - official_methods if available else set()
        doc_wsdl_mismatch = service.methods ^ wsdl_ops if service and available else set()

        rows.append({
            "endpoint": endpoint,
            "service": service,
            "lib_name": lib_name,
            "lib_methods": lib_methods,
            "wsdl_ops": wsdl_ops,
            "official_methods": official_methods,
            "available": available,
            "missing_methods": missing_methods,
            "extra_methods": extra_methods,
            "doc_wsdl_mismatch": doc_wsdl_mismatch,
            "in_library": lib_entry is not None,
            "in_docs": service is not None,
        })

    return rows


def _append_coverage_section(lines: list[str], version: str, rows: list[dict]) -> None:
    official_count = sum(1 for row in rows if row["in_docs"])
    missing_services = sum(1 for row in rows if row["in_docs"] and not row["in_library"])
    extra_services = sum(1 for row in rows if row["in_library"] and not row["in_docs"])
    gap_services = sum(1 for row in rows if row["missing_methods"])
    missing_methods = sum(len(row["missing_methods"]) for row in rows)

    lines += [
        f"## {version} Coverage",
        "",
        "| Category | Count |",
        "|---|---|",
        f"| Official docs services | {official_count} |",
        f"| Missing services (in live API, not in library) | {missing_services} |",
        f"| Extra services (in library, not in live API docs) | {extra_services} |",
        f"| Services with missing methods | {gap_services} |",
        f"| Total missing methods | {missing_methods} |",
        "",
    ]

    for i, row in enumerate(rows, start=1):
        service = row["service"]
        endpoint = row["endpoint"]
        lib_name = row["lib_name"] or "_(not in library)_"

        if row["in_docs"] and not row["in_library"]:
            status_label = "NEW - not in library"
        elif row["in_library"] and not row["in_docs"]:
            status_label = "not in official docs"
        elif not row["available"]:
            status_label = "WSDL unavailable"
        elif row["missing_methods"]:
            status_label = "method gap"
        else:
            status_label = "ok"

        lines.append(f"### {i}. `{endpoint}` (lib: `{lib_name}`) - {status_label}")
        lines.append("")
        if service:
            lines.append(f"- **Docs:** {service.docs_url}")
            lines.append(f"- **WSDL:** {service.wsdl_url}")
            if service.soap_url:
                lines.append(f"- **SOAP:** {service.soap_url}")
            if service.json_url:
                lines.append(f"- **JSON:** {service.json_url}")
            if service.methods:
                lines.append(f"- **Official docs methods ({len(service.methods)}):** `{'`, `'.join(sorted(service.methods))}`")
        else:
            lines.append("- **Docs:** not found in official live docs")

        if row["available"]:
            lines.append(f"- **WSDL operations ({len(row['wsdl_ops'])}):** `{'`, `'.join(sorted(row['wsdl_ops']))}`")
        elif service:
            lines.append("- **WSDL operations:** unavailable")

        if row["lib_methods"]:
            lines.append(f"- **Library declared ({len(row['lib_methods'])}):** `{'`, `'.join(sorted(row['lib_methods']))}`")
        else:
            lines.append("- **Library declared:** none")

        if row["missing_methods"]:
            lines.append(f"- **Missing in library ({len(row['missing_methods'])}):** `{'`, `'.join(sorted(row['missing_methods']))}`")
        if row["extra_methods"]:
            lines.append(f"- **In library but not in live API ({len(row['extra_methods'])}):** `{'`, `'.join(sorted(row['extra_methods']))}`")
        if row["doc_wsdl_mismatch"]:
            lines.append(f"- **Docs/WSDL mismatch ({len(row['doc_wsdl_mismatch'])}):** `{'`, `'.join(sorted(row['doc_wsdl_mismatch']))}`")
        lines.append("")


def build_report(
    discovered_services: list[DiscoveredService],
    wsdl_results: dict[str, tuple[set[str], bool]],
    legacy_methods: list[LegacyMethod] | None = None,
) -> str:
    today = date.today().isoformat()
    legacy_methods = legacy_methods or []
    versions = sorted({service.version for service in discovered_services}, key=lambda v: (v != "v5", v))

    n_total_lib = len(RESOURCE_CATALOG)
    n_wsdl_lib = len(WSDL_RESOURCES)
    n_reports = sum(1 for i in RESOURCE_CATALOG.values() if i["type"] == "reports")
    n_oauth = sum(1 for i in RESOURCE_CATALOG.values() if i["type"] == "oauth")

    lines = [
        "# Yandex Direct API - Official Docs WSDL/SOAP Audit Report",
        f"**Date:** {today}",
        "",
        "## Summary",
        "",
        "| Category | Count |",
        "|---|---|",
        f"| Total resources in `resource_mapping.py` | {n_total_lib} |",
        f"| — SOAP/WSDL services | {n_wsdl_lib} |",
        f"| — Reports API (non-SOAP) | {n_reports} |",
        f"| — OAuth helpers | {n_oauth} |",
        f"| Official docs versions | {', '.join(versions) if versions else 'none'} |",
        f"| Official docs WSDL entries | {len(discovered_services)} |",
        f"| Legacy v4 methods | {len(legacy_methods)} |",
        "",
    ]

    lines += [
        "## Non-WSDL Resources",
        "",
        "These resources are implemented in the library but have no WSDL (not SOAP services):",
        "",
    ]
    for i, (name, info) in enumerate(
        ((n, i) for n, i in RESOURCE_CATALOG.items() if i["type"] != "wsdl"), start=1
    ):
        type_label = {"reports": "Reports API (TSV, async)", "oauth": "OAuth helper"}.get(info["type"], info["type"])
        lines.append(f"{i}. **{name}** (`{info['endpoint']}`) — {type_label}")
    lines.append("")

    for version in versions:
        _append_coverage_section(lines, version, _coverage_rows(version, discovered_services, wsdl_results))

    if legacy_methods:
        lines += [
            "## v4 Legacy SOAP/WSDL",
            "",
            "These methods come from the official legacy Direct API v4 documentation and are reported separately from v5 resource coverage.",
            "",
        ]
        for i, method in enumerate(legacy_methods, start=1):
            lines.append(f"{i}. **{method.name}** — {method.docs_url}")
        lines.append("")

    return "\n".join(lines)


def create_github_issue(report: str) -> None:
    today = date.today().isoformat()
    title = f"WSDL Audit: API coverage gaps {today}"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
            tmp.write(report)
            tmp_path = tmp.name
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body-file", tmp_path],
            capture_output=True, text=True, check=True, timeout=60,
        )
        print(f"\nGitHub issue created: {result.stdout.strip()}", file=sys.stderr)
    except FileNotFoundError:
        print("\nError: 'gh' CLI not found. Install it from https://cli.github.com/", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\nError creating GitHub issue:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("\nError: gh CLI timed out after 60 seconds.", file=sys.stderr)
        sys.exit(1)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Yandex Direct WSDL coverage")
    parser.add_argument("--issue", action="store_true",
                        help="Create a GitHub issue with the report (requires gh CLI)")
    parser.add_argument("--output", metavar="FILE",
                        help="Save report to file instead of printing to stdout")
    parser.add_argument("--versions", default="v5,v501,v4",
                        help="Comma-separated versions to audit: v5,v501,v4")
    parser.add_argument("--docs-base-url", default=DOCS_BASE_URL,
                        help="Official Yandex Direct v5 documentation base URL")
    parser.add_argument("--v4-docs-base-url", default=V4_DOCS_BASE_URL,
                        help="Official Yandex Direct v4 documentation base URL")
    parser.add_argument("--timeout", type=int, default=15,
                        help="HTTP timeout in seconds")
    args = parser.parse_args()

    requested_versions = {version.strip() for version in args.versions.split(",") if version.strip()}
    supported_versions = {"v5", "v501", "v4"}
    unsupported = requested_versions - supported_versions
    if unsupported:
        parser.error(f"unsupported version(s): {', '.join(sorted(unsupported))}")

    discovered_services: list[DiscoveredService] = []
    legacy_methods: list[LegacyMethod] = []

    if requested_versions & {"v5", "v501"}:
        discovered_services = [
            service for service in discover_v5_services_from_docs(args.docs_base_url, args.timeout)
            if service.version in requested_versions
        ]

    if "v4" in requested_versions:
        legacy_methods = discover_v4_methods_from_docs(args.v4_docs_base_url, args.timeout)

    wsdl_results: dict[str, tuple[set[str], bool]] = {}
    seen_wsdl: set[str] = set()
    print(f"\nFetching WSDL for {len(discovered_services)} official docs entries...", file=sys.stderr)
    for service in discovered_services:
        if service.wsdl_url not in seen_wsdl:
            seen_wsdl.add(service.wsdl_url)
            ops, available = fetch_wsdl_operations(service.wsdl_url, args.timeout)
            wsdl_results[service.wsdl_url] = (ops, available)
            status = (
                f"{len(ops)} operations: {', '.join(sorted(ops))}"
                if available else "WSDL not available"
            )
            print(f"  [{service.version}/{service.endpoint}] {status}", file=sys.stderr)

    print("\nBuilding report...", file=sys.stderr)
    report = build_report(discovered_services, wsdl_results, legacy_methods)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(report)

    if args.issue:
        create_github_issue(report)


if __name__ == "__main__":
    main()
