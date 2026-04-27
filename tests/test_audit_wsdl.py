import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_wsdl.py"
spec = importlib.util.spec_from_file_location("audit_wsdl", MODULE_PATH)
audit_wsdl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_wsdl)


def test_parse_v5_service_page_extracts_methods_and_transport_urls():
    html = """
    <html>
      <body>
        <h1>AdExtensions: operations with ad extensions</h1>
        <p>Methods <a>add</a> | <a>get</a> | <a>delete</a></p>
        <p>WSDL description address</p>
        <code>https://api.direct.yandex.com/v5/adextensions?wsdl</code>
        <code>https://api.direct.yandex.com/v501/adextensions?wsdl</code>
        <p>SOAP address</p>
        <code>https://api.direct.yandex.com/v5/adextensions</code>
        <p>JSON address</p>
        <code>https://api.direct.yandex.com/json/v5/adextensions</code>
      </body>
    </html>
    """

    services = audit_wsdl.parse_v5_service_page(
        html,
        "https://yandex.com/dev/direct/doc/en/adextensions/adextensions",
    )

    assert [service.version for service in services] == ["v5", "v501"]
    assert services[0].name == "AdExtensions"
    assert services[0].endpoint == "adextensions"
    assert services[0].methods == {"add", "get", "delete"}
    assert services[0].wsdl_url == "https://api.direct.yandex.com/v5/adextensions?wsdl"
    assert services[0].soap_url == "https://api.direct.yandex.com/v5/adextensions"
    assert services[0].json_url == "https://api.direct.yandex.com/json/v5/adextensions"


def test_parse_v5_service_page_extracts_methods_from_service_method_links():
    html = """
    <html>
      <body>
        <h1>Strategies: operations with portfolio strategies</h1>
        <a href="en/strategies/strategies">Strategies: operations with portfolio strategies</a>
        <a href="en/strategies/add">add</a>
        <a href="en/strategies/archive">archive</a>
        <a href="en/strategies/get">get</a>
        <a href="en/strategies/unarchive">unarchive</a>
        <a href="en/strategies/update">update</a>
        <a href="https://api.direct.yandex.com/v5/strategies?wsdl">v5 WSDL</a>
        <a href="https://api.direct.yandex.com/v501/strategies?wsdl">v501 WSDL</a>
        <a href="https://api.direct.yandex.com/v5/strategies">v5 SOAP</a>
        <a href="https://api.direct.yandex.com/json/v5/strategies">v5 JSON</a>
      </body>
    </html>
    """

    services = audit_wsdl.parse_v5_service_page(
        html,
        "https://yandex.com/dev/direct/doc/en/strategies/strategies",
    )

    assert [service.version for service in services] == ["v5", "v501"]
    assert services[0].endpoint == "strategies"
    assert services[0].methods == {"add", "archive", "get", "unarchive", "update"}
    assert services[0].wsdl_url == "https://api.direct.yandex.com/v5/strategies?wsdl"
    assert services[0].soap_url == "https://api.direct.yandex.com/v5/strategies"
    assert services[0].json_url == "https://api.direct.yandex.com/json/v5/strategies"


def test_parse_v5_service_page_extracts_single_method_from_links():
    html = """
    <html>
      <body>
        <h1>TurboPages: getting parameters of Turbo pages</h1>
        <a href="en/turbopages/turbopages">TurboPages: getting parameters of Turbo pages</a>
        <a href="en/turbopages/get">get</a>
        <a href="https://api.direct.yandex.com/v5/turbopages?wsdl">v5 WSDL</a>
      </body>
    </html>
    """

    services = audit_wsdl.parse_v5_service_page(
        html,
        "https://yandex.com/dev/direct/doc/en/turbopages/turbopages",
    )

    assert services[0].endpoint == "turbopages"
    assert services[0].methods == {"get"}


def test_parse_v5_index_extracts_service_page_links_only():
    html = """
    <a href="en/adgroups/adgroups">AdGroups</a>
    <a href="en/adgroups/adgroups#methods">AdGroups methods</a>
    <a href="/dev/direct/doc/en/adextensions/adextensions">AdExtensions</a>
    <a href="/dev/direct/doc/en/concepts/soap">SOAP protocol</a>
    <a href="/dev/direct/doc/en/campaigns/campaigns">Campaigns</a>
    <a href="/dev/direct/doc/en/reports/reports">Reports</a>
    """

    links = audit_wsdl.parse_v5_service_links(
        html,
        "https://yandex.com/dev/direct/doc/en/",
    )

    assert links == [
        "https://yandex.com/dev/direct/doc/en/adgroups/adgroups",
        "https://yandex.com/dev/direct/doc/en/adextensions/adextensions",
        "https://yandex.com/dev/direct/doc/en/campaigns/campaigns",
        "https://yandex.com/dev/direct/doc/en/reports/reports",
    ]


def test_parse_v4_index_extracts_legacy_method_links():
    html = """
    <a href="en/reference/_AllMethods">Methods</a>
    <a href="en/reference/ErrorCodes">ErrorCodes</a>
    <a href="en/reference/GetAvailableVersions">GetAvailableVersions</a>
    <a href="en/live/GetEventsLog">GetEventsLog (Live)</a>
    <a href="/dev/direct/doc/dg-v4/en/reference/CreateNewWordstatReport">CreateNewWordstatReport</a>
    <a href="/dev/direct/doc/dg-v4/en/reference/GetWordstatReport">GetWordstatReport</a>
    <a href="/dev/direct/doc/dg-v4/en/concepts/access">Access</a>
    """

    methods = audit_wsdl.parse_v4_method_links(
        html,
        "https://yandex.com/dev/direct/doc/dg-v4/en/",
    )

    assert methods == [
        audit_wsdl.LegacyMethod(
            name="GetAvailableVersions",
            docs_url="https://yandex.com/dev/direct/doc/dg-v4/en/reference/GetAvailableVersions",
        ),
        audit_wsdl.LegacyMethod(
            name="GetEventsLog (Live)",
            docs_url="https://yandex.com/dev/direct/doc/dg-v4/en/live/GetEventsLog",
        ),
        audit_wsdl.LegacyMethod(
            name="CreateNewWordstatReport",
            docs_url="https://yandex.com/dev/direct/doc/dg-v4/en/reference/CreateNewWordstatReport",
        ),
        audit_wsdl.LegacyMethod(
            name="GetWordstatReport",
            docs_url="https://yandex.com/dev/direct/doc/dg-v4/en/reference/GetWordstatReport",
        ),
    ]


def test_parse_wsdl_operations_extracts_port_type_operations():
    xml = """
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/">
      <portType name="AdExtensionsPort">
        <operation name="add" />
        <operation name="get" />
      </portType>
    </definitions>
    """

    assert audit_wsdl.parse_wsdl_operations(xml.encode()) == {"add", "get"}


def test_discover_v5_services_expands_service_links_from_fetched_pages(monkeypatch):
    pages = {
        "https://yandex.com/dev/direct/doc/en/": """
            <a href="en/adextensions/adextensions">AdExtensions</a>
        """,
        "https://yandex.com/dev/direct/doc/en/adextensions/adextensions": """
            <h1>AdExtensions: operations with ad extensions</h1>
            <a href="en/adgroups/adgroups">AdGroups</a>
            <p>Methods: <a>add</a> | <a>get</a> | <a>delete</a></p>
            <code>https://api.direct.yandex.com/v5/adextensions?wsdl</code>
            <code>https://api.direct.yandex.com/v5/adextensions</code>
            <code>https://api.direct.yandex.com/json/v5/adextensions</code>
        """,
        "https://yandex.com/dev/direct/doc/en/adgroups/adgroups": """
            <h1>AdGroups: operations with ad groups</h1>
            <p>Methods: <a>add</a> | <a>get</a> | <a>update</a> | <a>delete</a></p>
            <code>https://api.direct.yandex.com/v5/adgroups?wsdl</code>
            <code>https://api.direct.yandex.com/v5/adgroups</code>
            <code>https://api.direct.yandex.com/json/v5/adgroups</code>
        """,
    }

    def fake_get_text(url, timeout):
        return pages[url]

    monkeypatch.setattr(audit_wsdl, "_get_text", fake_get_text)

    services = audit_wsdl.discover_v5_services_from_docs(
        "https://yandex.com/dev/direct/doc/en/",
        timeout=1,
    )

    assert [service.endpoint for service in services] == ["adextensions", "adgroups"]


def test_discover_v4_methods_follows_all_methods_page(monkeypatch):
    pages = {
        "https://yandex.com/dev/direct/doc/dg-v4/en/": """
            <a href="en/reference/_AllMethods">Methods</a>
        """,
        "https://yandex.com/dev/direct/doc/dg-v4/en/reference/_AllMethods": """
            <a href="en/reference/CreateNewWordstatReport">CreateNewWordstatReport</a>
            <a href="en/live/GetEventsLog">GetEventsLog (Live)</a>
        """,
    }

    def fake_get_text(url, timeout):
        return pages[url]

    monkeypatch.setattr(audit_wsdl, "_get_text", fake_get_text)

    methods = audit_wsdl.discover_v4_methods_from_docs(
        "https://yandex.com/dev/direct/doc/dg-v4/en/",
        timeout=1,
    )

    assert methods == [
        audit_wsdl.LegacyMethod(
            name="CreateNewWordstatReport",
            docs_url="https://yandex.com/dev/direct/doc/dg-v4/en/reference/CreateNewWordstatReport",
        ),
        audit_wsdl.LegacyMethod(
            name="GetEventsLog (Live)",
            docs_url="https://yandex.com/dev/direct/doc/dg-v4/en/live/GetEventsLog",
        ),
    ]


def test_build_report_separates_v5_v501_and_v4_coverage():
    discovered = [
        audit_wsdl.DiscoveredService(
            version="v5",
            name="AdExtensions",
            endpoint="adextensions",
            docs_url="https://yandex.com/dev/direct/doc/en/adextensions/adextensions",
            methods={"add", "get", "delete", "archive"},
            wsdl_url="https://api.direct.yandex.com/v5/adextensions?wsdl",
            soap_url="https://api.direct.yandex.com/v5/adextensions",
            json_url="https://api.direct.yandex.com/json/v5/adextensions",
        ),
        audit_wsdl.DiscoveredService(
            version="v501",
            name="AdExtensions",
            endpoint="adextensions",
            docs_url="https://yandex.com/dev/direct/doc/en/adextensions/adextensions",
            methods={"add", "get", "delete", "archive", "newMethod"},
            wsdl_url="https://api.direct.yandex.com/v501/adextensions?wsdl",
            soap_url="https://api.direct.yandex.com/v501/adextensions",
            json_url=None,
        ),
    ]
    wsdl_results = {
        "https://api.direct.yandex.com/v5/adextensions?wsdl": ({"add", "get", "delete", "archive"}, True),
        "https://api.direct.yandex.com/v501/adextensions?wsdl": ({"add", "get", "delete", "archive", "newMethod"}, True),
    }
    legacy = [
        audit_wsdl.LegacyMethod(
            name="CreateNewWordstatReport",
            docs_url="https://yandex.com/dev/direct/doc/dg-v4/en/reference/CreateNewWordstatReport",
        )
    ]

    report = audit_wsdl.build_report(discovered, wsdl_results, legacy)

    assert "## v5 Coverage" in report
    assert "## v501 Coverage" in report
    assert "## v4 Legacy SOAP/WSDL" in report
    assert "Official docs services | 1" in report
    assert "Missing in library (1):** `archive`" in report
    assert "newMethod" in report
    assert "CreateNewWordstatReport" in report


def test_classify_v4_method_returns_v5_equivalent_for_mapped_method():
    status, v5_eq = audit_wsdl.classify_v4_method("GetCampaignsList")
    assert status == "deprecated_with_v5_replacement"
    assert v5_eq == "campaigns.get"


def test_classify_v4_method_returns_none_for_actual_candidate():
    status, v5_eq = audit_wsdl.classify_v4_method("GetClientsUnits")
    assert status == "actual_no_v5_analogue"
    assert v5_eq is None


def test_classify_v4_method_returns_unclassified_for_unknown():
    status, v5_eq = audit_wsdl.classify_v4_method("SomeBrandNewOperation")
    assert status == "unclassified"
    assert v5_eq is None


def test_v4_method_priority_high_for_issue_mentioned_actual():
    assert audit_wsdl.v4_method_priority(
        "GetBalance", "actual_no_v5_analogue"
    ) == "high"
    # An actual method NOT in the issue hints AND not in V4_NO_BUSINESS_VALUE
    # should be medium. AdImageAssociation maps to None, is not in hints, and
    # is not in V4_NO_BUSINESS_VALUE — so it lands in "medium".
    # (PingAPI also maps to None but is in V4_NO_BUSINESS_VALUE → "low".)
    assert audit_wsdl.v4_method_priority(
        "AdImageAssociation", "actual_no_v5_analogue"
    ) == "medium"
    assert audit_wsdl.v4_method_priority(
        "PingAPI", "actual_no_v5_analogue"
    ) == "low"
    assert audit_wsdl.v4_method_priority(
        "GetCampaignsList", "deprecated_with_v5_replacement"
    ) == "low"
    assert audit_wsdl.v4_method_priority("Whatever", "unclassified") == "?"


def test_discover_v4_wsdl_services_uses_monolithic_endpoints(monkeypatch):
    fetched: list[str] = []

    def fake_fetch(url, timeout):
        fetched.append(url)
        if "live" in url:
            return ({"GetEventsLog", "AccountManagement", "GetBalance"}, True)
        return ({"GetBalance", "GetCampaignsList"}, True)

    monkeypatch.setattr(audit_wsdl, "fetch_wsdl_operations", fake_fetch)

    services = audit_wsdl.discover_v4_wsdl_services(timeout=5)

    assert fetched == [audit_wsdl.V4_WSDL_URL, audit_wsdl.V4_LIVE_WSDL_URL]
    assert [s.version for s in services] == ["v4", "v4live"]
    assert services[0].wsdl_url == audit_wsdl.V4_WSDL_URL
    assert services[1].wsdl_url == audit_wsdl.V4_LIVE_WSDL_URL
    assert services[0].methods == {"GetBalance", "GetCampaignsList"}
    assert services[1].methods == {"GetEventsLog", "AccountManagement", "GetBalance"}


def test_discover_v4_wsdl_services_skips_unavailable(monkeypatch, capsys):
    def fake_fetch(url, timeout):
        if "live" in url:
            return (set(), False)
        return ({"GetBalance"}, True)

    monkeypatch.setattr(audit_wsdl, "fetch_wsdl_operations", fake_fetch)

    services = audit_wsdl.discover_v4_wsdl_services(timeout=5)

    assert [s.version for s in services] == ["v4"]
    err = capsys.readouterr().err
    assert "unavailable" in err


def test_build_v4_matrix_includes_priority_and_v5_equivalent():
    DiscoveredService = audit_wsdl.DiscoveredService
    v4_svc = DiscoveredService(
        version="v4",
        name="v4",
        endpoint="v4_monolithic",
        docs_url="",
        methods={"GetCampaignsList", "GetBalance"},
        wsdl_url=audit_wsdl.V4_WSDL_URL,
        soap_url="https://api.direct.yandex.ru/v4/",
        json_url=None,
    )
    live_svc = DiscoveredService(
        version="v4live",
        name="v4live",
        endpoint="v4_live_monolithic",
        docs_url="",
        methods={"GetCampaignsList", "GetBalance", "AccountManagement", "BogusUnclassifiedOp"},
        wsdl_url=audit_wsdl.V4_LIVE_WSDL_URL,
        soap_url="https://api.direct.yandex.ru/live/v4/",
        json_url=None,
    )

    matrix = audit_wsdl.build_v4_matrix([v4_svc, live_svc])

    assert "# Yandex Direct API v4 / v4 Live — Methods Matrix" in matrix
    # Deprecated v5 mapping rendered in table
    assert "`GetCampaignsList`" in matrix
    assert "`campaigns.get`" in matrix
    assert "deprecated_with_v5_replacement" in matrix
    assert "low" in matrix
    # Actual + high priority (issue-mentioned)
    assert "`GetBalance`" in matrix
    assert "actual_no_v5_analogue" in matrix
    assert "high" in matrix
    assert "`AccountManagement`" in matrix
    # Availability column
    assert "v4 + Live" in matrix
    assert "Live only" in matrix
    # Unclassified surfaces in dedicated section
    assert "Unclassified operations" in matrix
    assert "`BogusUnclassifiedOp`" in matrix
    # Implementation candidates list
    assert "Implementation candidates" in matrix


def test_build_v4_matrix_handles_empty_input():
    matrix = audit_wsdl.build_v4_matrix([])
    assert "Total v4 / v4 Live operations (from WSDL) | 0" in matrix
    assert "No candidates" in matrix


def test_v4_to_v5_map_covers_all_known_v4_live_operations():
    # Source of truth: real WSDL operation list captured at the time this audit
    # was authored (74 ops). The set is static — Yandex-side additions are NOT
    # detected automatically; only a manual update to known_v4_live_ops or to
    # V4_TO_V5_MAP triggers this guard. If you grow either set and forget the
    # other, the assertion below catches the desync.
    known_v4_live_ops = {
        "AccountManagement", "AdImage", "AdImageAssociation", "ArchiveBanners",
        "ArchiveCampaign", "CheckPayment", "CreateInvoice", "CreateNewForecast",
        "CreateNewReport", "CreateNewSubclient", "CreateNewWordstatReport",
        "CreateOfflineReport", "CreateOrUpdateBanners", "CreateOrUpdateCampaign",
        "DeleteBanners", "DeleteCampaign", "DeleteForecastReport",
        "DeleteOfflineReport", "DeleteReport", "DeleteWordstatReport",
        "EnableSharedAccount", "GetAvailableVersions", "GetBalance",
        "GetBannerPhrases", "GetBannerPhrasesFilter", "GetBanners",
        "GetBannersStat", "GetBannersTags", "GetCampaignParams",
        "GetCampaignsList", "GetCampaignsListFilter", "GetCampaignsParams",
        "GetCampaignsTags", "GetChanges", "GetClientInfo", "GetClientsList",
        "GetClientsUnits", "GetCreditLimits", "GetEventsLog", "GetForecast",
        "GetForecastList", "GetKeywordsSuggestion", "GetOfflineReportList",
        "GetRegions", "GetReportList", "GetRetargetingGoals", "GetRubrics",
        "GetStatGoals", "GetSubClients", "GetSummaryStat", "GetTimeZones",
        "GetVersion", "GetWordstatReport", "GetWordstatReportList", "Keyword",
        "ModerateBanners", "PayCampaigns", "PayCampaignsByCard", "PingAPI",
        "PingAPI_X", "ResumeBanners", "ResumeCampaign", "Retargeting",
        "RetargetingCondition", "SetAutoPrice", "StopBanners", "StopCampaign",
        "TransferMoney", "UnArchiveBanners", "UnArchiveCampaign",
        "UpdateBannersTags", "UpdateCampaignsTags", "UpdateClientInfo",
        "UpdatePrices",
    }
    missing = known_v4_live_ops - set(audit_wsdl.V4_TO_V5_MAP)
    assert not missing, (
        f"V4_TO_V5_MAP must classify every known v4 / v4 Live WSDL operation. "
        f"Add entries for: {sorted(missing)}"
    )
    extra = set(audit_wsdl.V4_TO_V5_MAP) - known_v4_live_ops
    assert not extra, (
        f"V4_TO_V5_MAP contains entries not in known_v4_live_ops "
        f"(possible typos in keys): {sorted(extra)}"
    )
