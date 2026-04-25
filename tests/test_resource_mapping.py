import importlib.util
from pathlib import Path

import pytest

from tapi_yandex_direct.resource_mapping import RESOURCE_MAPPING_V5


def test_no_legacy_docs_paths():
    for name, info in RESOURCE_MAPPING_V5.items():
        assert "/dg/concepts/" not in info["docs"], f"{name}: legacy /dg/concepts/ URL"
        assert ".html" not in info["docs"], f"{name}: legacy .html suffix"


def test_all_resources_have_methods_field():
    for name, info in RESOURCE_MAPPING_V5.items():
        if name == "debugtoken":
            continue
        assert "methods" in info, f"{name} missing methods field"
        assert isinstance(info["methods"], list)
        assert info["methods"], f"{name} has empty methods list"


def test_keywords_does_not_support_archive():
    """Issue #8: keywords does not support archive/unarchive."""
    methods = RESOURCE_MAPPING_V5["keywords"]["methods"]
    assert "archive" not in methods
    assert "unarchive" not in methods


@pytest.mark.parametrize("name", ["ads", "campaigns", "strategies"])
def test_archive_supporting_resources(name):
    methods = RESOURCE_MAPPING_V5[name]["methods"]
    assert "archive" in methods
    assert "unarchive" in methods


def test_reports_has_docs_pages():
    """Issue #10: reports exposes documentation sub-pages."""
    pages = RESOURCE_MAPPING_V5["reports"]["docs_pages"]
    assert set(pages) == {"type", "period", "fields-list", "headers"}
    for url in pages.values():
        assert url.startswith("https://yandex.ru/dev/direct/doc/ru/")


def test_methods_match_audit_script():
    """Sanity: scripts/audit_wsdl.py and resource_mapping should agree."""
    p = Path(__file__).resolve().parents[1] / "scripts" / "audit_wsdl.py"
    spec = importlib.util.spec_from_file_location("audit_wsdl", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name, info in RESOURCE_MAPPING_V5.items():
        if name == "debugtoken":
            continue
        if name not in mod.RESOURCE_CATALOG:
            continue
        assert set(info["methods"]) == set(mod.RESOURCE_CATALOG[name]["methods"]), (
            f"{name} methods mismatch between resource_mapping and audit_wsdl"
        )
