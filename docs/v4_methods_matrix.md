# Yandex Direct API v4 / v4 Live — Methods Matrix
**Date:** 2026-04-27

Source of truth: live WSDL endpoints
- v4: `https://api.direct.yandex.ru/v4/wsdl/`
- v4 Live: `https://api.direct.yandex.ru/live/v4/wsdl/`

Status semantics:
- **deprecated_with_v5_replacement** — direct v5 analogue exists; new code should use v5.
- **actual_no_v5_analogue** — no v5 equivalent; candidate for implementation in this library.
- **unclassified** — not yet classified in `V4_TO_V5_MAP`; needs review.

## Summary

| Category | Count |
|---|---|
| Total v4 / v4 Live operations (from WSDL) | 74 |
| Operations also available in v4 Live only | 17 |
| Operations available in both v4 and Live | 57 |
| Operations available only in v4 (not Live) | 0 |
| Status: deprecated_with_v5_replacement | 41 |
| Status: actual_no_v5_analogue (candidates) | 33 |
| Status: unclassified (needs review) | 0 |
| Priority: high (issue-mentioned candidates) | 20 |
| Priority: medium (other actual candidates) | 9 |

## Full method table

| # | Method | Availability | Status | v5 equivalent | Priority |
|---|---|---|---|---|---|
| 1 | `AccountManagement` | Live only | actual_no_v5_analogue | — | high |
| 2 | `AdImage` | Live only | deprecated_with_v5_replacement | `adimages.add` | low |
| 3 | `AdImageAssociation` | Live only | actual_no_v5_analogue | — | medium |
| 4 | `ArchiveBanners` | v4 + Live | deprecated_with_v5_replacement | `ads.archive` | low |
| 5 | `ArchiveCampaign` | v4 + Live | deprecated_with_v5_replacement | `campaigns.archive` | low |
| 6 | `CheckPayment` | v4 + Live | actual_no_v5_analogue | — | medium |
| 7 | `CreateInvoice` | v4 + Live | actual_no_v5_analogue | — | high |
| 8 | `CreateNewForecast` | v4 + Live | actual_no_v5_analogue | — | high |
| 9 | `CreateNewReport` | v4 + Live | deprecated_with_v5_replacement | `reports.get` | low |
| 10 | `CreateNewSubclient` | v4 + Live | deprecated_with_v5_replacement | `agencyclients.add` | low |
| 11 | `CreateNewWordstatReport` | v4 + Live | actual_no_v5_analogue | — | high |
| 12 | `CreateOfflineReport` | Live only | deprecated_with_v5_replacement | `reports.get` | low |
| 13 | `CreateOrUpdateBanners` | v4 + Live | deprecated_with_v5_replacement | `ads.add` | low |
| 14 | `CreateOrUpdateCampaign` | v4 + Live | deprecated_with_v5_replacement | `campaigns.add` | low |
| 15 | `DeleteBanners` | v4 + Live | deprecated_with_v5_replacement | `ads.delete` | low |
| 16 | `DeleteCampaign` | v4 + Live | deprecated_with_v5_replacement | `campaigns.delete` | low |
| 17 | `DeleteForecastReport` | v4 + Live | actual_no_v5_analogue | — | high |
| 18 | `DeleteOfflineReport` | Live only | actual_no_v5_analogue | — | medium |
| 19 | `DeleteReport` | v4 + Live | actual_no_v5_analogue | — | medium |
| 20 | `DeleteWordstatReport` | v4 + Live | actual_no_v5_analogue | — | high |
| 21 | `EnableSharedAccount` | Live only | actual_no_v5_analogue | — | high |
| 22 | `GetAvailableVersions` | v4 + Live | actual_no_v5_analogue | — | low |
| 23 | `GetBalance` | v4 + Live | actual_no_v5_analogue | — | high |
| 24 | `GetBannerPhrases` | v4 + Live | deprecated_with_v5_replacement | `keywords.get` | low |
| 25 | `GetBannerPhrasesFilter` | v4 + Live | deprecated_with_v5_replacement | `keywords.get` | low |
| 26 | `GetBanners` | v4 + Live | deprecated_with_v5_replacement | `ads.get` | low |
| 27 | `GetBannersStat` | Live only | deprecated_with_v5_replacement | `reports.get` | low |
| 28 | `GetBannersTags` | Live only | actual_no_v5_analogue | — | medium |
| 29 | `GetCampaignParams` | v4 + Live | deprecated_with_v5_replacement | `campaigns.get` | low |
| 30 | `GetCampaignsList` | v4 + Live | deprecated_with_v5_replacement | `campaigns.get` | low |
| 31 | `GetCampaignsListFilter` | v4 + Live | deprecated_with_v5_replacement | `campaigns.get` | low |
| 32 | `GetCampaignsParams` | v4 + Live | deprecated_with_v5_replacement | `campaigns.get` | low |
| 33 | `GetCampaignsTags` | Live only | actual_no_v5_analogue | — | medium |
| 34 | `GetChanges` | v4 + Live | deprecated_with_v5_replacement | `changes.check` | low |
| 35 | `GetClientInfo` | v4 + Live | deprecated_with_v5_replacement | `clients.get` | low |
| 36 | `GetClientsList` | v4 + Live | deprecated_with_v5_replacement | `agencyclients.get` | low |
| 37 | `GetClientsUnits` | v4 + Live | actual_no_v5_analogue | — | high |
| 38 | `GetCreditLimits` | v4 + Live | actual_no_v5_analogue | — | high |
| 39 | `GetEventsLog` | Live only | actual_no_v5_analogue | — | high |
| 40 | `GetForecast` | v4 + Live | actual_no_v5_analogue | — | high |
| 41 | `GetForecastList` | v4 + Live | actual_no_v5_analogue | — | high |
| 42 | `GetKeywordsSuggestion` | v4 + Live | actual_no_v5_analogue | — | medium |
| 43 | `GetOfflineReportList` | Live only | deprecated_with_v5_replacement | `reports.get` | low |
| 44 | `GetRegions` | v4 + Live | deprecated_with_v5_replacement | `dictionaries.get` | low |
| 45 | `GetReportList` | v4 + Live | deprecated_with_v5_replacement | `reports.get` | low |
| 46 | `GetRetargetingGoals` | Live only | actual_no_v5_analogue | — | high |
| 47 | `GetRubrics` | v4 + Live | deprecated_with_v5_replacement | `dictionaries.get` | low |
| 48 | `GetStatGoals` | v4 + Live | actual_no_v5_analogue | — | high |
| 49 | `GetSubClients` | v4 + Live | deprecated_with_v5_replacement | `agencyclients.get` | low |
| 50 | `GetSummaryStat` | v4 + Live | deprecated_with_v5_replacement | `reports.get` | low |
| 51 | `GetTimeZones` | v4 + Live | deprecated_with_v5_replacement | `dictionaries.get` | low |
| 52 | `GetVersion` | v4 + Live | actual_no_v5_analogue | — | low |
| 53 | `GetWordstatReport` | v4 + Live | actual_no_v5_analogue | — | high |
| 54 | `GetWordstatReportList` | v4 + Live | actual_no_v5_analogue | — | high |
| 55 | `Keyword` | Live only | deprecated_with_v5_replacement | `keywords.add` | low |
| 56 | `ModerateBanners` | v4 + Live | deprecated_with_v5_replacement | `ads.moderate` | low |
| 57 | `PayCampaigns` | v4 + Live | actual_no_v5_analogue | — | high |
| 58 | `PayCampaignsByCard` | v4 + Live | actual_no_v5_analogue | — | high |
| 59 | `PingAPI` | v4 + Live | actual_no_v5_analogue | — | low |
| 60 | `PingAPI_X` | v4 + Live | actual_no_v5_analogue | — | low |
| 61 | `ResumeBanners` | v4 + Live | deprecated_with_v5_replacement | `ads.resume` | low |
| 62 | `ResumeCampaign` | v4 + Live | deprecated_with_v5_replacement | `campaigns.resume` | low |
| 63 | `Retargeting` | Live only | deprecated_with_v5_replacement | `retargeting.get` | low |
| 64 | `RetargetingCondition` | Live only | deprecated_with_v5_replacement | `retargeting.add` | low |
| 65 | `SetAutoPrice` | v4 + Live | deprecated_with_v5_replacement | `keywordbids.setAuto` | low |
| 66 | `StopBanners` | v4 + Live | deprecated_with_v5_replacement | `ads.suspend` | low |
| 67 | `StopCampaign` | v4 + Live | deprecated_with_v5_replacement | `campaigns.suspend` | low |
| 68 | `TransferMoney` | v4 + Live | actual_no_v5_analogue | — | high |
| 69 | `UnArchiveBanners` | v4 + Live | deprecated_with_v5_replacement | `ads.unarchive` | low |
| 70 | `UnArchiveCampaign` | v4 + Live | deprecated_with_v5_replacement | `campaigns.unarchive` | low |
| 71 | `UpdateBannersTags` | Live only | actual_no_v5_analogue | — | medium |
| 72 | `UpdateCampaignsTags` | Live only | actual_no_v5_analogue | — | medium |
| 73 | `UpdateClientInfo` | v4 + Live | deprecated_with_v5_replacement | `clients.update` | low |
| 74 | `UpdatePrices` | v4 + Live | deprecated_with_v5_replacement | `keywordbids.set` | low |

## Implementation candidates

Methods with no v5 analogue, sorted by priority (high → medium):

| # | Method | Availability | Priority |
|---|---|---|---|
| 1 | `AccountManagement` | Live only | high |
| 2 | `CreateInvoice` | v4 + Live | high |
| 3 | `CreateNewForecast` | v4 + Live | high |
| 4 | `CreateNewWordstatReport` | v4 + Live | high |
| 5 | `DeleteForecastReport` | v4 + Live | high |
| 6 | `DeleteWordstatReport` | v4 + Live | high |
| 7 | `EnableSharedAccount` | Live only | high |
| 8 | `GetBalance` | v4 + Live | high |
| 9 | `GetClientsUnits` | v4 + Live | high |
| 10 | `GetCreditLimits` | v4 + Live | high |
| 11 | `GetEventsLog` | Live only | high |
| 12 | `GetForecast` | v4 + Live | high |
| 13 | `GetForecastList` | v4 + Live | high |
| 14 | `GetRetargetingGoals` | Live only | high |
| 15 | `GetStatGoals` | v4 + Live | high |
| 16 | `GetWordstatReport` | v4 + Live | high |
| 17 | `GetWordstatReportList` | v4 + Live | high |
| 18 | `PayCampaigns` | v4 + Live | high |
| 19 | `PayCampaignsByCard` | v4 + Live | high |
| 20 | `TransferMoney` | v4 + Live | high |
| 21 | `AdImageAssociation` | Live only | medium |
| 22 | `CheckPayment` | v4 + Live | medium |
| 23 | `DeleteOfflineReport` | Live only | medium |
| 24 | `DeleteReport` | v4 + Live | medium |
| 25 | `GetAvailableVersions` | v4 + Live | low |
| 26 | `GetBannersTags` | Live only | medium |
| 27 | `GetCampaignsTags` | Live only | medium |
| 28 | `GetKeywordsSuggestion` | v4 + Live | medium |
| 29 | `GetVersion` | v4 + Live | low |
| 30 | `PingAPI` | v4 + Live | low |
| 31 | `PingAPI_X` | v4 + Live | low |
| 32 | `UpdateBannersTags` | Live only | medium |
| 33 | `UpdateCampaignsTags` | Live only | medium |
