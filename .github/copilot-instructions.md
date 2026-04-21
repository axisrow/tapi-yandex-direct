# Copilot instructions for `tapi-yandex-direct`

## Commands

### Build

```bash
python setup.py sdist
```

This is the checked-in packaging entrypoint. On current setuptools/Python, it emits a warning about the legacy `test_suite` metadata but still produces the source distribution.

### Test

Run the mocked suite:

```bash
python -m pytest tests/tests.py -q
```

Run a single mocked test:

```bash
python -m pytest tests/tests.py::test_sanity -q
```

`tests/tests2.py` is not part of the self-contained suite. It expects `../config.yml`, `yaml`, and real Yandex Direct credentials, so treat it as a manual/live script.

## High-level architecture

The package is a thin Yandex Direct wrapper built on top of `tapi-wrapper2`, not a hand-written client per resource.

- `tapi_yandex_direct/tapi_yandex_direct.py` defines `YandexDirectClientAdapter`, then creates the public `YandexDirect` client with `generate_wrapper_from_adapter(...)`.
- `tapi_yandex_direct/resource_mapping.py` is the source of truth for resource names exposed on the client (`client.campaigns()`, `client.reports()`, etc.). Each entry maps a public method name to the Yandex Direct v5 path and documentation URL.
- `YandexDirectClientAdapter` is where the actual client behavior lives: it chooses sandbox vs production base URLs, injects auth and report headers, serializes requests with `orjson`, translates API errors into repo-specific exceptions, and implements retry/backoff behavior for rate limits, unit exhaustion, server errors, and asynchronous report generation.
- Reports are a special path. `/json/v5/reports` returns TSV/text rather than the JSON shape used by other resources, so the adapter parses the header row into `store["columns"]` and exposes report-only helpers such as `iter_lines()`, `iter_values()`, `iter_dicts()`, `to_lines()`, `to_values()`, `to_columns()`, and `to_dicts()`.
- Non-report pagination relies on `result.LimitedBy`: `get_iterator_next_request_kwargs()` mutates `params.Page.Offset`, and higher-level wrapper helpers like `.pages()` and `.iter_items()` depend on that behavior.
- `scripts/yandex_direct_export_to_file.py` is the main end-to-end example. It uses the same client abstractions to export either paginated JSON resources or report TSV output into tab-separated files.

## Key conventions

- Keep `RESOURCE_MAPPING_V5` and `RESULT_DICTIONARY_KEYS_OF_API_METHODS` in sync. Adding or renaming a resource usually requires updates in both places, or `.extract()` will fail for that method/resource combination.
- `__init__.py` re-exports `YandexDirect` and everything from `resource_mapping`, so public resource names are part of the package surface and should be treated as stable API.
- Backward-incompatible pre-2021 behavior is intentionally blocked. Deprecated parameters like `receive_all_objects` and `auto_request_generation`, and the old `transform()` method, should raise `BackwardCompatibilityError` rather than being silently supported.
- Error handling is explicit and typed: token issues, request-limit issues, and unit-exhaustion issues are converted into dedicated exception classes in `tapi_yandex_direct/exceptions.py`.
- The checked-in automated tests are response-mocked and fast; live API exploration belongs in scripts or the manual `tests/tests2.py` flow, not in the mocked suite.
