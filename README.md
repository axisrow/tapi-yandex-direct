# Python client for [API Yandex Direct](https://yandex.ru/dev/metrika/doc/api2/concept/about-docpage/)

![Supported Python Versions](https://img.shields.io/static/v1?label=python&message=>=3.9&color=green)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/vintasoftware/tapioca-wrapper/master/LICENSE)
[![Downloads](https://pepy.tech/badge/tapi-yandex-direct)](https://pepy.tech/project/tapi-yandex-direct)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

## Python version support

| Python | Installable | CI-tested | Notes |
|--------|-------------|-----------|-------|
| 3.9    | ✅ | ✅ | |
| 3.10   | ✅ | ✅ | |
| 3.11   | ✅ | ✅ | |
| 3.12   | ✅ | ✅ | |
| 3.13   | ✅ | ✅ | |
| 3.14   | ✅ | ✅ | Pre-release, `allow-prereleases: true` required |
| <3.9   | ❌ | ❌ | Not supported |

`orjson` is installed without a version pin — pip selects a compatible release automatically based on the interpreter.

## Installation

Prev version

    pip install --upgrade tapi-yandex-direct==2020.12.15

Last version. Has backward incompatible changes.

    pip install --upgrade tapi-yandex-direct==2021.5.29

## Examples

[Ipython Notebook](https://github.com/pavelmaksimov/tapi-yandex-direct/blob/master/examples.ipynb)

[Script to export data to a file](scripts/yandex_direct_export_to_file.py)

    python yandex_direct_export_to_file.py --help
    python yandex_direct_export_to_file.py --body_filepath body-clients.json --token TOKEN --resource clients --filepath clients.tsv
    python yandex_direct_export_to_file.py --body_filepath body-report.json --token TOKEN --resource reports --filepath report-with-login-column.tsv --extra_columns login
    python yandex_direct_export_to_file.py --body_filepath body-report.json --token TOKEN --resource reports --filepath report.tsv


## Documentation
[Справка](https://yandex.ru/dev/direct/) Api Яндекс Директ

### Supported methods per resource

Not all resources support the full lifecycle. For example, `keywords` does NOT support `archive`/`unarchive` — only `campaigns`, `ads` and `strategies` support archival.

Each resource entry in `RESOURCE_MAPPING_V5` exposes a `methods` list, and `reports` additionally exposes `docs_pages` for sub-page docs:

```python
from tapi_yandex_direct import RESOURCE_MAPPING_V5

print(RESOURCE_MAPPING_V5["keywords"]["methods"])
# ['get', 'add', 'update', 'delete', 'suspend', 'resume']

print(RESOURCE_MAPPING_V5["reports"]["docs_pages"])
# {'type': '...', 'period': '...', 'fields-list': '...', 'headers': '...'}
```


### Client params
```python
from tapi_yandex_direct import YandexDirect

ACCESS_TOKEN = "{your_access_token}"

client = YandexDirect(
    # Required parameters:

    access_token=ACCESS_TOKEN,
    # If you are making inquiries from an agent account, you must be sure to specify the account login.
    login="{login}",

    # Optional parameters:

    # Enable sandbox.
    is_sandbox=False,
    # Repeat request when units run out
    retry_if_not_enough_units=False,
    # The language in which the data for directories and errors will be returned.
    language="ru",
    # Repeat the request if the limits on the number of reports or requests are exceeded.
    retry_if_exceeded_limit=True,
    # Number of retries when server errors occur.
    retries_if_server_error=5
)
```

### Resource methods
```python
print(dir(client))
[
    "adextensions",
    "adgroups",
    "adimages",
    "ads",
    "agencyclients",
    "audiencetargets",
    "bidmodifiers",
    "bids",
    "businesses",
    "campaigns",
    "changes",
    "clients",
    "creatives",
    "debugtoken",
    "dictionaries",
    "dynamicads",
    "feeds",
    "keywordbids",
    "keywords",
    "keywordsresearch",
    "leads",
    "negativekeywordsharedsets",
    "reports",
    "retargeting",
    "sitelinks",
    "smartadtargets",
    "strategies",
    "turbopages",
    "vcards",
]
```
or look into [resource mapping](tapi_yandex_direct/resource_mapping.py)

### Request

API requests are made over HTTPS using the POST method.
Input data structures are passed in the body of the request.

```python
import datetime as dt

# Get campaigns.
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
campaigns = client.campaigns().post(data=body)
print(campaigns)
# <TapiClient object
# {   'result': {   'Campaigns': [   {   'Id': 338157,
#                                        'Name': 'Test API Sandbox campaign 1'},
#                                    {   'Id': 338158,
#                                        'Name': 'Test API Sandbox campaign 2'}],
#                   'LimitedBy': 2}}>


# Extract raw data.
data = campaigns.data
assert isinstance(data, dict)


# Create a campaign.
body = {
    "method": "add",
    "params": {
        "Campaigns": [
            {
                "Name": "MyCampaignTest",
                "StartDate": str(dt.datetime.now().date()),
                "TextCampaign": {
                    "BiddingStrategy": {
                        "Search": {
                            "BiddingStrategyType": "HIGHEST_POSITION"
                        },
                        "Network": {
                            "BiddingStrategyType": "SERVING_OFF"
                        }
                    },
                    "Settings": []
                }
            }
        ]
    }
}
result = client.campaigns().post(data=body)
print(result)
# <TapiClient object
# {'result': {'AddResults': [{'Id': 417065}]}}>

# Extract raw data.
data = campaigns.data
assert isinstance(data, dict)
print(result)
# {'result': {'AddResults': [{'Id': 417066}]}}
```


### Client methods

Result extraction method.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
campaigns = client.campaigns().post(data=body)

# Request response.
print(campaigns.response)
print(campaigns.request_kwargs)
print(campaigns.status_code)
print(campaigns.data)
```

### .extract()

Result extraction method.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
campaigns = client.campaigns().post(data=body)
campaigns_list = campaigns().extract()
assert isinstance(campaigns_list, list)
print(campaigns_list)
# [{'Id': 338157, 'Name': 'Test API Sandbox campaign 1'},
#  {'Id': 338158, 'Name': 'Test API Sandbox campaign 2'}]
```


### .items()

Iterating result items.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
campaigns = client.campaigns().post(data=body)

for item in campaigns().items():
    print(item)
    # {'Id': 338157, 'Name': 'Test API Sandbox campaign 1'}
    assert isinstance(item, dict)
```


### .pages()

Iterating to get all the data.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
        "Page": {"Limit": 2}
    },
}
campaigns = client.campaigns().post(data=body)

# Iterating requests data.
for page in campaigns().pages():
    assert isinstance(page.data, list)
    print(page.data)
    # [{'Id': 338157, 'Name': 'Test API Sandbox campaign 1'},
    #  {'Name': 'Test API Sandbox campaign 2', 'Id': 338158}]

    # Iterating items of page data.
    for item in page().items():
        print(item)
        # {'Id': 338157, 'Name': 'Test API Sandbox campaign 1'}
        assert isinstance(item, dict)
```


### .iter_items()

After each request, iterates over the items of the request data.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
        "Page": {"Limit": 2}
    },
}
campaigns = client.campaigns().post(data=body)

# Iterates through the elements of all data.
for item in campaigns().iter_items():
    assert isinstance(item, dict)
    print(item)

# {'Name': 'MyCampaignTest', 'Id': 417065}
# {'Name': 'MyCampaignTest', 'Id': 417066}
# {'Id': 338157, 'Name': 'Test API Sandbox campaign 1'}
# {'Name': 'Test API Sandbox campaign 2', 'Id': 338158}
# {'Id': 338159, 'Name': 'Test API Sandbox campaign 3'}
# {'Name': 'MyCampaignTest', 'Id': 415805}
# {'Id': 416524, 'Name': 'MyCampaignTest'}
# {'Id': 417056, 'Name': 'MyCampaignTest'}
# {'Id': 417057, 'Name': 'MyCampaignTest'}
# {'Id': 417058, 'Name': 'MyCampaignTest'}
# {'Id': 417065, 'Name': 'MyCampaignTest'}
# {'Name': 'MyCampaignTest', 'Id': 417066}
```


## Reports

```python
from tapi_yandex_direct import YandexDirect

ACCESS_TOKEN = "{ваш токен доступа}"

client = YandexDirect(
    # Required parameters:

    access_token=ACCESS_TOKEN,
    # If you are making inquiries from an agent account, you must be sure to specify the account login.
    login="{login}",

    # Optional parameters:

    # Enable sandbox.
    is_sandbox=False,
    # Repeat request when units run out
    retry_if_not_enough_units=False,
    # The language in which the data for directories and errors will be returned.
    language="ru",
    # Repeat the request if the limits on the number of reports or requests are exceeded.
    retry_if_exceeded_limit=True,
    # Number of retries when server errors occur.
    retries_if_server_error=5,

    # Report resource parameters:

    # Report generation mode: online, offline or auto.
    processing_mode="offline",
    # When requesting a report, it will wait until the report is prepared and download it.
    wait_report=True,
    # Monetary values in the report are returned in currency with an accuracy of two decimal places.
    return_money_in_micros=False,
    # Do not display a line with the report name and date range in the report.
    skip_report_header=True,
    # Do not display a line with field names in the report.
    skip_column_header=False,
    # Do not display a line with the number of statistics lines in the report.
    skip_report_summary=True,
)

body = {
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Date", "CampaignId", "Clicks", "Cost"],
        "OrderBy": [{
            "Field": "Date"
        }],
        "ReportName": "Actual Data",
        "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
        "DateRangeType": "LAST_WEEK",
        "Format": "TSV",
        "IncludeVAT": "YES",
        "IncludeDiscount": "YES"
    }
}
report = client.reports().post(data=body)
print(report.data)
# 'Date\tCampaignId\tClicks\tCost\n'
# '2019-09-02\t338151\t12578\t9210750000\n'
```


### .columns

Extract column names.
```python
report = client.reports().post(data=body)
print(report.columns)
# ['Date', 'CampaignId', 'Clicks', 'Cost']
```


### .to_lines()

```python
report = client.reports().post(data=body)
print(report().to_lines())
# list[str]
# [..., '2019-09-02\t338151\t12578\t9210750000']
```


### .to_values()

```python
report = client.reports().post(data=body)
print(report().to_values())
# list[list[str]]
# [..., ['2019-09-02', '338151', '12578', '9210750000']]
```


### .to_dicts()

```python
report = client.reports().post(data=body)
print(report().to_dicts())
# list[dict]
# [..., {'Date': '2019-09-02', 'CampaignId': '338151', 'Clicks': '12578', 'Cost': 9210750000'}]
```


### .to_columns()

```python
report = client.reports().post(data=body)
print(report().to_columns())
# list[list[str], list[str], list[str], list[str]]
# [[..., '2019-09-02'], [..., '338151'], [..., '12578'], [..., '9210750000']]
```


## v4 Live API

Yandex Direct API v4 / v4 Live exposes a number of operations that have **no
analogue in v5** — for example account balance and credit limits, agency
finance operations (TransferMoney, PayCampaigns), Wordstat reports, budget
forecasts, the events log, retargeting goals, and shared-account management.
This library ships a separate `YandexDirectV4Live` client that wraps the JSON
variant of v4 (`https://api.direct.yandex.ru/live/v4/json/`).

The list of supported operations is curated against `docs/v4_methods_matrix.md`
— only methods that lack a v5 equivalent are exposed. See
`tapi_yandex_direct.v4.SUPPORTED_V4_METHODS` for the full set.

### Client params

```python
from tapi_yandex_direct import YandexDirectV4Live

client = YandexDirectV4Live(
    access_token="{your_access_token}",
    # Required when calling on behalf of a sub-client (agency accounts).
    login="{login}",
    # Locale used for error messages. Defaults to "en".
    language="ru",
    # Sandbox base URL.
    is_sandbox=False,
    # Retry on rate-limit error_code in (54, 55).
    retry_if_exceeded_limit=True,
    retries_if_server_error=5,
)
```

### Request shape

v4 Live is RPC-style: there is **one endpoint** and the operation name lives in
the JSON body. The client injects the OAuth token, locale, and login (for
`param: dict` payloads only) automatically — pass `method` and `param`:

```python
# Read-only: rate-limit units balance for the account
result = client.v4live().post(data={
    "method": "GetClientsUnits",
    "param": ["{login}"],   # list-of-logins for this method
})
result.data        # → {"data": [{"UnitsRest": 32000, "Login": "..."}]}
result().extract() # → [{"UnitsRest": 32000, "Login": "..."}]

# Method with dict params (login auto-injected from client config)
result = client.v4live().post(data={
    "method": "GetEventsLog",
    "param": {"TimestampFrom": 1714200000, "Limit": 100},
})
```

### Errors

v4 Live returns HTTP 200 even on errors — the failure is signalled by a
non-zero `error_code` in the body. The client maps this into Python exceptions:

| `error_code` | Exception |
|---|---|
| 53 | `V4LiveTokenError` |
| 54, 55, 56 | `V4LiveRequestsLimitError` |
| any other | `V4LiveError` |

```python
from tapi_yandex_direct.exceptions import V4LiveError, V4LiveTokenError

try:
    client.v4live().post(data={"method": "GetBalance", "param": {...}})
except V4LiveTokenError:
    refresh_token()
except V4LiveError as e:
    print(e.error_code, e.error_str, e.error_detail)
```

### Differences from v5

| Aspect | v5 (`YandexDirect`) | v4 Live (`YandexDirectV4Live`) |
|---|---|---|
| Endpoint | per-resource (`/json/v5/<resource>`) | single (`/live/v4/json/`) |
| Method position | URL path / header | `method` field in body |
| Auth | `Authorization: Bearer …` header | header **plus** `token` field in body |
| Error transport | HTTP error codes / `{"error": …}` | always HTTP 200, `{"error_code": int, …}` |
| `error_code` type | string | integer |
| Pagination | `LimitedBy` in result, offset injection | per-method (`Limit`, `TimestampFrom`, …) — single-shot at the adapter level |

### Methods removed from v4 Live by Yandex

`GetBalance` is still in the v4 Live WSDL but Yandex disabled it server-side
— calling it returns `V4LiveError(error_code=509, error_str="This method is
not available in this API version")`. Use the v5 client instead:

```python
from tapi_yandex_direct import YandexDirect
client = YandexDirect(access_token=ACCESS_TOKEN)
campaigns = client.campaigns().post(data={
    "method": "get",
    "params": {
        "SelectionCriteria": {"Ids": [<campaign_id>]},
        "FieldNames": ["Id", "Funds"],   # Funds carries the campaign balance
    },
})
```

### Finance methods (financial_token required)

`GetCreditLimits`, `TransferMoney`, `PayCampaigns`, `PayCampaignsByCard`,
`CheckPayment` and `CreateInvoice` are finance operations and reject the
regular OAuth `access_token` with `V4LiveError(error_code=350, error_str=
"Invalid financial transaction token")`. Yandex requires a separate
**financial token** generated from the OAuth client secret + login +
operation number — see
<https://yandex.com/dev/direct/doc/dg-v4/en/concepts/finance>. Pass it
explicitly inside the `param` block of the request:

```python
client.v4live().post(data={
    "method": "TransferMoney",
    "param": {
        "Login": "<login>",
        "OperationNum": <int>,
        "FinanceToken": "<finance-token>",
        # ... other method-specific fields ...
    },
})
```

The library does **not** generate finance tokens for you — that flow involves
the OAuth client secret and is out of scope. See the issue body of #18 for
the verified live-API behaviour of every supported method.

### Common request schemas

The full call schemas come from
<https://yandex.com/dev/direct/doc/dg-v4/en/live/concepts>. A few that trip
up newcomers (verified live):

| Method | Required `param` shape |
|---|---|
| `GetClientsUnits` | list of logins, e.g. `["my-login"]` |
| `GetRetargetingGoals` | `{"Login": "my-login"}` |
| `GetStatGoals` | `{"CampaignIDS": [<int>, ...]}` (capital S) |
| `GetCampaignsTags` | `{"CampaignIDS": [<int>, ...]}` |
| `GetBannersTags` | `{"BannerIDS": [<int>, ...]}` |
| `GetEventsLog` | `{"TimestampFrom": "<ISO 8601>", "Currency": "RUB"\|"USD"\|...}` |
| `GetKeywordsSuggestion` | `{"Keywords": ["phrase 1", ...]}` |

`tests/test_v4_live_integration.py` exercises each of these against the real
API as living documentation — run with `pytest -m live` and a token in
`YANDEX_DIRECT_TOKEN`.


## Features

Information about the resource.
```python
client.campaigns().help()
```

Open resource documentation
```python
client.campaigns().open_docs()
```

Send a request in the browser.
```python
client.campaigns().open_in_browser()
```


## Dependences
- requests
- [tapi_wrapper](https://github.com/pavelmaksimov/tapi-wrapper)


## CHANGELOG
v2021.5.29
- Fix stub file (syntax highlighting)


v2021.5.25
- Add stub file (syntax highlighting)
- Add methods 'iter_dicts', 'to_dicts'


## Автор
Павел Максимов

Связаться со мной можно в
[Телеграм](https://t.me/pavel_maksimow)
и в
[Facebook](https://www.facebook.com/pavel.maksimow)

Удачи тебе, друг! Поставь звездочку ;)
