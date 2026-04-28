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

from __future__ import annotations

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

V4_WSDL_URL = "https://api.direct.yandex.ru/v4/wsdl/"
V4_LIVE_WSDL_URL = "https://api.direct.yandex.ru/live/v4/wsdl/"
V4_DOCS_BASE = "https://yandex.com/dev/direct/doc/dg-v4/en"

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
    "dynamicfeedadtargets":    {"endpoint": "dynamicfeedadtargets",   "type": "wsdl", "methods": {"get", "add", "delete", "suspend", "resume", "setBids"}},
    "feeds":                   {"endpoint": "feeds",                  "type": "wsdl", "methods": {"get", "add", "update", "delete"}},
    "keywordbids":             {"endpoint": "keywordbids",            "type": "wsdl", "methods": {"get", "set", "setAuto"}},
    "keywords":                {"endpoint": "keywords",               "type": "wsdl", "methods": {"get", "add", "update", "delete", "suspend", "resume"}},
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
    # Legacy v4 / v4 Live — single monolithic WSDL each. Library does not implement v4 yet,
    # so lib_methods = empty set. methods = filled at runtime from real WSDL operations.
    "v4":     {"endpoint": "v4_monolithic",      "type": "wsdl_v4",     "methods": set(), "lib_methods": set()},
    "v4live": {"endpoint": "v4_live_monolithic", "type": "wsdl_v4live", "methods": set(), "lib_methods": set()},
}

_WSDL_TYPES = frozenset({"wsdl", "wsdl_v4", "wsdl_v4live"})

WSDL_RESOURCES = {
    name: info for name, info in RESOURCE_CATALOG.items()
    if info["type"] in _WSDL_TYPES
}

# Subset for v5/v501 fallback discovery — excludes v4 placeholders that have
# their own monolithic WSDL discovery path (discover_v4_wsdl_services).
V5_WSDL_RESOURCES = {
    name: info for name, info in RESOURCE_CATALOG.items()
    if info["type"] == "wsdl"
}

# Method names that look like operations but are actually enum values
# or parameter-driven behaviors — do not flag as "missing".
KNOWN_NON_WSDL_METHODS: dict[str, set[str]] = {
    "dictionaries": {"getGeoRegions"},
}

# v4 / v4 Live operation -> v5 equivalent (None means no analogue in v5).
# A key being present at all means the method has been classified.
# Methods absent from this map are reported as "unclassified" by classify_v4_method.
V4_TO_V5_MAP: dict[str, str | None] = {
    # Campaigns
    "GetCampaignsList":       "campaigns.get",
    "GetCampaignsListFilter": "campaigns.get",
    "GetCampaignsParams":     "campaigns.get",
    "GetCampaignParams":      "campaigns.get",
    "CreateOrUpdateCampaign": "campaigns.add",
    "ArchiveCampaign":        "campaigns.archive",
    "UnArchiveCampaign":      "campaigns.unarchive",
    "DeleteCampaign":         "campaigns.delete",
    "ResumeCampaign":         "campaigns.resume",
    "StopCampaign":           "campaigns.suspend",
    # Banners (= ads in v5)
    "GetBanners":             "ads.get",
    "CreateOrUpdateBanners":  "ads.add",
    "ArchiveBanners":         "ads.archive",
    "UnArchiveBanners":       "ads.unarchive",
    "DeleteBanners":          "ads.delete",
    "ModerateBanners":        "ads.moderate",
    "ResumeBanners":          "ads.resume",
    "StopBanners":            "ads.suspend",
    "GetBannerPhrases":       "keywords.get",
    "GetBannerPhrasesFilter": "keywords.get",
    "Keyword":                "keywords.add",
    # Bids
    "SetAutoPrice":           "keywordbids.setAuto",
    "UpdatePrices":           "keywordbids.set",
    # Retargeting
    "Retargeting":            "retargeting.get",
    "RetargetingCondition":   "retargeting.add",
    # Clients
    "GetClientInfo":          "clients.get",
    "UpdateClientInfo":       "clients.update",
    "GetClientsList":         "agencyclients.get",
    "GetSubClients":          "agencyclients.get",
    "CreateNewSubclient":     "agencyclients.add",
    # Dictionaries
    "GetRegions":             "dictionaries.get",
    "GetRubrics":             "dictionaries.get",
    "GetTimeZones":           "dictionaries.get",
    # Changes
    "GetChanges":             "changes.check",
    # Reports / stats
    "CreateNewReport":        "reports.get",
    "GetReportList":          "reports.get",
    "DeleteReport":           None,
    "GetSummaryStat":         "reports.get",
    "GetBannersStat":         "reports.get",
    "CreateOfflineReport":    "reports.get",
    "DeleteOfflineReport":    None,
    "GetOfflineReportList":   "reports.get",
    # API meta
    "GetAvailableVersions":   None,
    "GetVersion":             None,
    "PingAPI":                None,
    "PingAPI_X":              None,
    # Tags (Live) — no v5 equivalent
    "GetBannersTags":         None,
    "UpdateBannersTags":      None,
    "GetCampaignsTags":       None,
    "UpdateCampaignsTags":    None,
    # AdImage (Live)
    "AdImage":                "adimages.add",
    "AdImageAssociation":     None,
    # Keyword suggestions — no real v5 equivalent (deduplicate removes
    # duplicates, hasSearchVolume tests presence; neither suggests phrases).
    "GetKeywordsSuggestion":  None,
    # ===== CANDIDATES FOR IMPLEMENTATION (no v5 equivalent) =====
    "GetClientsUnits":        None,  # client points balance — v4-only
    "GetCreditLimits":        None,
    "TransferMoney":          None,
    "PayCampaigns":           None,
    "PayCampaignsByCard":     None,
    "CheckPayment":           None,
    "CreateInvoice":          None,
    "AccountManagement":      None,  # shared account (Live)
    "EnableSharedAccount":    None,  # (Live)
    "GetEventsLog":           None,  # (Live)
    "GetStatGoals":           None,  # Metrika goals
    "GetRetargetingGoals":    None,  # (Live)
    "CreateNewWordstatReport":None,
    "DeleteWordstatReport":   None,
    "GetWordstatReport":      None,
    "GetWordstatReportList":  None,
    "CreateNewForecast":      None,
    "DeleteForecastReport":   None,
    "GetForecast":            None,
    "GetForecastList":        None,
}

# Methods explicitly mentioned by the issue author as relevant / actual.
# Used to bump priority of unmapped methods to "high".
V4_HIGH_PRIORITY_HINTS: frozenset[str] = frozenset({
    "GetClientsUnits", "GetCreditLimits",
    "TransferMoney", "PayCampaigns", "PayCampaignsByCard",
    "CreateInvoice", "AccountManagement", "EnableSharedAccount",
    "GetEventsLog", "GetStatGoals", "GetRetargetingGoals",
    "CreateNewWordstatReport", "DeleteWordstatReport",
    "GetWordstatReport", "GetWordstatReportList",
    "CreateNewForecast", "DeleteForecastReport",
    "GetForecast", "GetForecastList",
})

# Methods that have no v5 equivalent but are not worth implementing in a
# Python client either: API-meta probes (PingAPI, GetVersion, ...) and
# health checks. Surfaced as "actual_no_v5_analogue" but with priority "low"
# so they do not pollute the implementation-candidates list.
V4_NO_BUSINESS_VALUE: frozenset[str] = frozenset({
    "PingAPI", "PingAPI_X", "GetVersion", "GetAvailableVersions",
})

# Methods that still appear in the v4 / v4 Live WSDL but have been disabled
# server-side by Yandex — calls return error_code=509
# ("This method is not available in this API version"). Verified live
# 2026-04-27. Keep here so the matrix can surface them honestly instead of
# advertising them as implementation candidates. v5 alternatives noted in
# README.
V4_REMOVED_FROM_LIVE: frozenset[str] = frozenset({
    "GetBalance",
})


def classify_v4_method(method: str) -> tuple[str, str | None]:
    """Classify a v4 / v4 Live operation against v5.

    Returns a (status, v5_equivalent) tuple. Status is one of:
      - "removed_from_v4_live" — method was disabled server-side (error_code 509).
      - "deprecated_with_v5_replacement" — method has a direct v5 analogue.
      - "actual_no_v5_analogue" — method is in V4_TO_V5_MAP with value None
        (= explicitly classified as "no v5 equivalent, candidate to implement").
      - "unclassified" — method is missing from V4_TO_V5_MAP entirely.
    """
    if method in V4_REMOVED_FROM_LIVE:
        return ("removed_from_v4_live", None)
    if method not in V4_TO_V5_MAP:
        return ("unclassified", None)
    v5_eq = V4_TO_V5_MAP[method]
    if v5_eq is None:
        return ("actual_no_v5_analogue", None)
    return ("deprecated_with_v5_replacement", v5_eq)


def v4_method_priority(method: str, status: str) -> str:
    """Return priority label for a v4 method."""
    if status == "removed_from_v4_live":
        return "skip"
    if status == "actual_no_v5_analogue":
        if method in V4_NO_BUSINESS_VALUE:
            return "low"
        return "high" if method in V4_HIGH_PRIORITY_HINTS else "medium"
    if status == "deprecated_with_v5_replacement":
        return "low"
    return "?"


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
    _SKIP_TAGS = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP_TAGS:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
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


def discover_v5_services_from_docs(base_url: str, timeout: int, max_pages: int = 200) -> list[DiscoveredService]:
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
    skipped_pages: int = 0

    while queued:
        if len(processed_links) >= max_pages:
            print(
                f"  Warning: reached max_pages limit ({max_pages}), "
                f"stopping crawl with {len(queued)} page(s) remaining.",
                file=sys.stderr,
            )
            break

        link = queued.popleft()
        if link in processed_links:
            continue
        processed_links.add(link)
        try:
            page_html = _get_text(link, timeout)
        except requests.RequestException as e:
            skipped_pages += 1
            status_hint = ""
            if isinstance(e, requests.HTTPError) and e.response is not None:
                if e.response.status_code in (403, 429):
                    status_hint = " (rate-limited)"
            print(f"  Warning: could not fetch service page {link}{status_hint}: {e}", file=sys.stderr)
            continue

        for discovered_link in parse_v5_service_links(page_html, base_url):
            if discovered_link not in seen_links:
                seen_links.add(discovered_link)
                queued.append(discovered_link)

        parsed = parse_v5_service_page(page_html, link)
        services.extend(parsed)
        print(f"  [{link}] {len(parsed)} WSDL URL(s)", file=sys.stderr)

    if skipped_pages > 0:
        print(
            f"  WARNING: {skipped_pages} page(s) were skipped due to fetch errors "
            f"(possibly rate-limited). Results may be incomplete.",
            file=sys.stderr,
        )

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


def discover_v4_wsdl_services(timeout: int) -> list[DiscoveredService]:
    """Fetch the two monolithic v4 / v4 Live WSDLs and return DiscoveredService records.

    Reuses fetch_wsdl_operations — same code path as v5, just with hard-coded
    endpoints because v4 has no per-service WSDL split.
    """
    targets = [
        ("v4",     V4_WSDL_URL,      "v4_monolithic",      f"{V4_DOCS_BASE}/concepts"),
        ("v4live", V4_LIVE_WSDL_URL, "v4_live_monolithic", f"{V4_DOCS_BASE}/live/concepts"),
    ]
    services: list[DiscoveredService] = []
    for version, wsdl_url, endpoint, docs_url in targets:
        ops, available = fetch_wsdl_operations(wsdl_url, timeout)
        if not available:
            print(f"  Warning: WSDL {wsdl_url} unavailable", file=sys.stderr)
            continue
        soap_url = wsdl_url.replace("/wsdl/", "/")
        services.append(DiscoveredService(
            version=version,
            name=version,
            endpoint=endpoint,
            docs_url=docs_url,
            methods=ops,
            wsdl_url=wsdl_url,
            soap_url=soap_url,
            json_url=None,
        ))
        print(f"  [{version}] {len(ops)} operations from {wsdl_url}", file=sys.stderr)
    return services


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
    if version in {"v4", "v4live"}:
        type_key = "wsdl_v4" if version == "v4" else "wsdl_v4live"
        library_endpoints = {
            info["endpoint"] for info in RESOURCE_CATALOG.values()
            if info["type"] == type_key
        }
    else:
        library_endpoints = {info["endpoint"] for info in V5_WSDL_RESOURCES.values()}
    all_endpoints = sorted(set(services_by_endpoint) | library_endpoints)

    rows: list[dict] = []
    for endpoint in all_endpoints:
        service = services_by_endpoint.get(endpoint)
        lib_entry = _library_entry(endpoint)

        if lib_entry:
            lib_name, lib_info = lib_entry
            lib_methods = lib_info.get("lib_methods", lib_info["methods"])
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
    _version_order = {"v5": 0, "v501": 1, "v4": 2, "v4live": 3}
    versions = sorted(
        {service.version for service in discovered_services},
        key=lambda v: (_version_order.get(v, 99), v),
    )

    n_total_lib = len(RESOURCE_CATALOG)
    n_wsdl_lib = sum(1 for i in RESOURCE_CATALOG.values() if i["type"] == "wsdl")
    n_reports = sum(1 for i in RESOURCE_CATALOG.values() if i["type"] == "reports")
    n_oauth = sum(1 for i in RESOURCE_CATALOG.values() if i["type"] == "oauth")
    n_v4 = sum(1 for i in RESOURCE_CATALOG.values() if i["type"] in {"wsdl_v4", "wsdl_v4live"})

    lines = [
        "# Yandex Direct API - Official Docs WSDL/SOAP Audit Report",
        f"**Date:** {today}",
        "",
        "## Summary",
        "",
        "| Category | Count |",
        "|---|---|",
        f"| Total resources in `resource_mapping.py` | {n_total_lib} |",
        f"| — SOAP/WSDL services (v5) | {n_wsdl_lib} |",
        f"| — Reports API (non-SOAP) | {n_reports} |",
        f"| — OAuth helpers | {n_oauth} |",
        f"| — Legacy v4 / v4 Live placeholders | {n_v4} |",
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
        ((n, i) for n, i in RESOURCE_CATALOG.items() if i["type"] not in _WSDL_TYPES), start=1
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


def build_v4_matrix(v4_services: list[DiscoveredService]) -> str:
    """Render a stand-alone Markdown matrix of v4 / v4 Live operations vs v5.

    Uses real WSDL operations (not docs) as the source of truth. Each operation
    is classified via classify_v4_method against V4_TO_V5_MAP.
    """
    today = date.today().isoformat()
    by_version: dict[str, set[str]] = {svc.version: set(svc.methods) for svc in v4_services}
    v4_ops = by_version.get("v4", set())
    live_ops = by_version.get("v4live", set())
    all_ops = v4_ops | live_ops

    rows: list[dict] = []
    for op in sorted(all_ops):
        status, v5_eq = classify_v4_method(op)
        priority = v4_method_priority(op, status)
        in_v4 = op in v4_ops
        in_live = op in live_ops
        if in_v4 and in_live:
            availability = "v4 + Live"
        elif in_live:
            availability = "Live only"
        else:
            availability = "v4 only"
        rows.append({
            "method": op,
            "availability": availability,
            "status": status,
            "v5_equivalent": v5_eq,
            "priority": priority,
        })

    n_total = len(rows)
    n_actual = sum(1 for r in rows if r["status"] == "actual_no_v5_analogue")
    n_dep = sum(1 for r in rows if r["status"] == "deprecated_with_v5_replacement")
    n_unclassified = sum(1 for r in rows if r["status"] == "unclassified")
    n_removed = sum(1 for r in rows if r["status"] == "removed_from_v4_live")
    n_high = sum(1 for r in rows if r["priority"] == "high")
    n_medium = sum(1 for r in rows if r["priority"] == "medium")

    lines: list[str] = [
        "# Yandex Direct API v4 / v4 Live — Methods Matrix",
        f"**Date:** {today}",
        "",
        "Source of truth: live WSDL endpoints",
        f"- v4: `{V4_WSDL_URL}`",
        f"- v4 Live: `{V4_LIVE_WSDL_URL}`",
        "",
        "Status semantics:",
        "- **deprecated_with_v5_replacement** — direct v5 analogue exists; new code should use v5.",
        "- **actual_no_v5_analogue** — no v5 equivalent; candidate for implementation in this library.",
        "- **removed_from_v4_live** — operation is in the WSDL but Yandex disabled it server-side (error_code 509); use the v5 client.",
        "- **unclassified** — not yet classified in `V4_TO_V5_MAP`; needs review.",
        "",
        "## Summary",
        "",
        "| Category | Count |",
        "|---|---|",
        f"| Total v4 / v4 Live operations (from WSDL) | {n_total} |",
        f"| Operations also available in v4 Live only | {sum(1 for r in rows if r['availability'] == 'Live only')} |",
        f"| Operations available in both v4 and Live | {sum(1 for r in rows if r['availability'] == 'v4 + Live')} |",
        f"| Operations available only in v4 (not Live) | {sum(1 for r in rows if r['availability'] == 'v4 only')} |",
        f"| Status: deprecated_with_v5_replacement | {n_dep} |",
        f"| Status: actual_no_v5_analogue (candidates) | {n_actual} |",
        f"| Status: removed_from_v4_live | {n_removed} |",
        f"| Status: unclassified (needs review) | {n_unclassified} |",
        f"| Priority: high (issue-mentioned candidates) | {n_high} |",
        f"| Priority: medium (other actual candidates) | {n_medium} |",
        "",
        "## Full method table",
        "",
        "| # | Method | Availability | Status | v5 equivalent | Priority |",
        "|---|---|---|---|---|---|",
    ]
    for i, row in enumerate(rows, start=1):
        v5_cell = f"`{row['v5_equivalent']}`" if row["v5_equivalent"] else "—"
        lines.append(
            f"| {i} | `{row['method']}` | {row['availability']} | {row['status']} | "
            f"{v5_cell} | {row['priority']} |"
        )

    lines += [
        "",
        "## Implementation candidates",
        "",
        "Methods with no v5 analogue, sorted by priority (high → medium):",
        "",
    ]
    candidates = [r for r in rows if r["status"] == "actual_no_v5_analogue"]
    candidates.sort(key=lambda r: (0 if r["priority"] == "high" else 1, r["method"]))
    if candidates:
        lines.append("| # | Method | Availability | Priority |")
        lines.append("|---|---|---|---|")
        for i, row in enumerate(candidates, start=1):
            lines.append(
                f"| {i} | `{row['method']}` | {row['availability']} | {row['priority']} |"
            )
    else:
        lines.append("_No candidates — every method is either deprecated or unclassified._")

    if n_removed > 0:
        lines += [
            "",
            "## Removed from v4 Live",
            "",
            "These operations are still present in the WSDL but Yandex disabled them "
            "server-side. Calling them returns `V4LiveError(error_code=509)`. "
            "Use the v5 client (`YandexDirect`) for the equivalent functionality.",
            "",
        ]
        for row in rows:
            if row["status"] == "removed_from_v4_live":
                lines.append(f"- `{row['method']}` ({row['availability']})")

    if n_unclassified > 0:
        lines += [
            "",
            "## Unclassified operations",
            "",
            "These operations were found in the live WSDL but are missing from `V4_TO_V5_MAP`. "
            "Add them to the map before treating this matrix as final.",
            "",
        ]
        for row in rows:
            if row["status"] == "unclassified":
                lines.append(f"- `{row['method']}` ({row['availability']})")

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
    parser.add_argument("--max-pages", type=int, default=200,
                        help="Maximum pages to crawl in BFS discovery (default: 200)")
    parser.add_argument("--v4-matrix", metavar="FILE",
                        help="Generate the v4 / v4 Live methods matrix to a separate Markdown file")
    parser.add_argument("--legacy-v4-docs", action="store_true",
                        help="Also crawl legacy v4 docs pages (slow, often captcha-blocked)")
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
            service for service in discover_v5_services_from_docs(args.docs_base_url, args.timeout, args.max_pages)
            if service.version in requested_versions
        ]

    v4_services: list[DiscoveredService] = []
    if "v4" in requested_versions:
        v4_services = discover_v4_wsdl_services(args.timeout)
        discovered_services.extend(v4_services)
        if args.legacy_v4_docs:
            legacy_methods = discover_v4_methods_from_docs(args.v4_docs_base_url, args.timeout)

    wsdl_results: dict[str, tuple[set[str], bool]] = {}
    seen_wsdl: set[str] = set()
    # v4 services were already fetched inside discover_v4_wsdl_services — reuse their methods.
    for service in v4_services:
        wsdl_results[service.wsdl_url] = (service.methods, True)
        seen_wsdl.add(service.wsdl_url)
    v5_like = [s for s in discovered_services if s.version not in {"v4", "v4live"}]
    print(f"\nFetching WSDL for {len(v5_like)} official docs entries...", file=sys.stderr)
    for service in v5_like:
        if service.wsdl_url not in seen_wsdl:
            seen_wsdl.add(service.wsdl_url)
            ops, available = fetch_wsdl_operations(service.wsdl_url, args.timeout)
            wsdl_results[service.wsdl_url] = (ops, available)
            status = (
                f"{len(ops)} operations: {', '.join(sorted(ops))}"
                if available else "WSDL not available"
            )
            print(f"  [{service.version}/{service.endpoint}] {status}", file=sys.stderr)

    # Fallback: fetch WSDL for library resources not found in official docs
    discovered_endpoints = {s.endpoint for s in discovered_services}
    for version in requested_versions & {"v5", "v501"}:
        for name, info in V5_WSDL_RESOURCES.items():
            endpoint = info["endpoint"]
            if endpoint not in discovered_endpoints:
                wsdl_url = f"https://api.direct.yandex.com/{version}/{endpoint}?wsdl"
                if wsdl_url not in seen_wsdl:
                    seen_wsdl.add(wsdl_url)
                    ops, available = fetch_wsdl_operations(wsdl_url, args.timeout)
                    wsdl_results[wsdl_url] = (ops, available)
                    status = (
                        f"{len(ops)} operations: {', '.join(sorted(ops))}"
                        if available else "WSDL not available"
                    )
                    print(f"  [{version}/{endpoint}] (fallback) {status}", file=sys.stderr)
                    discovered_services.append(DiscoveredService(
                        version=version,
                        name=name,
                        endpoint=endpoint,
                        docs_url="",
                        methods=info["methods"],
                        wsdl_url=wsdl_url,
                        soap_url=f"https://api.direct.yandex.com/{version}/{endpoint}",
                        json_url=f"https://api.direct.yandex.com/json/{version}/{endpoint}",
                    ))

    print("\nBuilding report...", file=sys.stderr)
    report = build_report(discovered_services, wsdl_results, legacy_methods)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(report)

    if args.v4_matrix:
        if not v4_services:
            print(
                "Warning: --v4-matrix requested but v4 WSDL discovery returned nothing. "
                "Ensure 'v4' is in --versions and the WSDL endpoints are reachable.",
                file=sys.stderr,
            )
        matrix = build_v4_matrix(v4_services)
        out_dir = os.path.dirname(args.v4_matrix)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.v4_matrix, "w", encoding="utf-8") as f:
            f.write(matrix)
        print(f"v4 matrix saved to {args.v4_matrix}", file=sys.stderr)

    if args.issue:
        create_github_issue(report)


if __name__ == "__main__":
    main()
