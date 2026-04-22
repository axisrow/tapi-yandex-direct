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
