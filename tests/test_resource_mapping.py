from tapi_yandex_direct.resource_mapping import RESOURCE_MAPPING_V5


def test_no_legacy_docs_paths():
    for name, info in RESOURCE_MAPPING_V5.items():
        assert "/dg/concepts/" not in info["docs"], f"{name}: legacy /dg/concepts/ URL"
        assert ".html" not in info["docs"], f"{name}: legacy .html suffix"
