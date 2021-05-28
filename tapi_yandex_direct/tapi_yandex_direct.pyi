from typing import List, Iterator, Union

from requests import Response


class YandexDirectBaseMethodsClientResponse:
    @property
    def data(self) -> dict: ...
    @property
    def request_kwargs(self) -> dict: ...
    @property
    def response(self) -> Response: ...
    @property
    def status_code(self) -> int: ...
    def __getitem__(self, item) -> Union[dict, list]: ...
    def __iter__(self) -> Iterator: ...

# Yandex Direct management.
class YandexDirectClientResponse(YandexDirectBaseMethodsClientResponse):
    def pages(
        self, *, max_pages: int = None
    ) -> Iterator["YandexDirectPageIteratorExecutor"]: ...
    def items(self, *, max_items: int = None) -> Iterator[dict]: ...
    def iter_items(
        self, *, max_pages: int = None, max_items: int = None
    ) -> Iterator[dict]: ...
    def extract(self) -> List[dict]: ...

class YandexDirectClientExecutorResponse(YandexDirectBaseMethodsClientResponse):
    def __call__(self) -> YandexDirectClientResponse: ...

class YandexDirectClientExecutor:
    def open_docs(self) -> YandexDirectClientExecutor:
        """Open API official docs of resource in browser."""
    def open_in_browser(self) -> YandexDirectClientExecutor:
        """Send a request in the browser."""
    def help(self) -> YandexDirectClientExecutor:
        """Print docs of resource."""
    def get(
        self, *, params: dict = None, data: dict = None
    ) -> YandexDirectClientExecutorResponse:
        """
        Send HTTP 'GET' request.

        :param params: querystring arguments in the URL
        :param data: send data in the body of the request
        """
    def post(
        self, *, params: dict = None, data: dict = None
    ) -> YandexDirectClientExecutorResponse:
        """
        Send HTTP 'POST' request.

        :param params: querystring arguments in the URL
        :param data: send data in the body of the request
        """

class YandexDirectPageIteratorResponse(YandexDirectBaseMethodsClientResponse):
    def items(self, *, max_items: int = None) -> Iterator[dict]: ...

class YandexDirectPageIteratorExecutor(YandexDirectBaseMethodsClientResponse):
    def __call__(self) -> YandexDirectPageIteratorResponse: ...

# Yandex Direct reports.
class YandexDirectClientReportResponse(YandexDirectBaseMethodsClientResponse):
    def iter_lines(self) -> Iterator[str]: ...
    def iter_values(self) -> Iterator[list]: ...
    def iter_dicts(self) -> Iterator[dict]: ...
    def to_lines(self) -> List[str]: ...
    def to_values(self) -> List[list]: ...
    def to_columns(self) -> List[list]: ...
    def to_dicts(self) -> List[dict]: ...

class YandexDirectClientReportExecutorResponse(YandexDirectBaseMethodsClientResponse):
    def __call__(self) -> YandexDirectClientReportResponse: ...
    @property
    def columns(self) -> List[str]: ...

class YandexDirectClientReportExecutor:
    def open_docs(self) -> YandexDirectClientReportExecutor:
        """Open API official docs of resource in browser."""
    def open_in_browser(self) -> YandexDirectClientReportExecutor:
        """Send a request in the browser."""
    def help(self) -> YandexDirectClientReportExecutor:
        """Print docs of resource."""
    def post(
        self, *, params: dict = None, data: dict = None
    ) -> YandexDirectClientReportExecutorResponse:
        """
        Send HTTP 'POST' request.

        :param params: querystring arguments in the URL
        :param data: send data in the body of the request
        """

# Main.
class YandexDirect:
    def __init__(
        self,
        *,
        access_token: str,
        login: str = None,
        is_sandbox: bool = False,
        retry_if_not_enough_units: bool = False,
        retry_if_exceeded_limit: bool = True,
        retries_if_server_error: int = 5,
        language: str = None,
        processing_mode: str = "offline",
        wait_report: bool = True,
        return_money_in_micros: bool = False,
        skip_report_header: bool = True,
        skip_column_header: bool = False,
        skip_report_summary: bool = True,
    ):
        """
        Official documentation of the reports resource: https://yandex.ru/dev/direct/doc/ref-v5/concepts/about.html
        Official documentation of other resources: https://yandex.ru/dev/direct/doc/reports/how-to.html

        :param access_token: Access token.
        :param login: If you are making inquiries from an agent account, you must be sure to specify the account login.
        :param is_sandbox: Enable sandbox.
        :param retry_if_not_enough_units: Repeat request when units run out
        :param retry_if_exceeded_limit: Repeat the request if the limits on the number of reports or requests are exceeded.
        :param retries_if_server_error: Number of retries when server errors occur.
        :param language: The language in which the data for directories and errors will be returned.

        :param processing_mode: (report resource) Report generation mode: online, offline or auto.
        :param wait_report: (report resource) When requesting a report, it will wait until the report is prepared and download it.
        :param return_money_in_micros: (report resource) Monetary values in the report are returned in currency with an accuracy of two decimal places.
        :param skip_report_header: (report resource) Do not display a line with the report name and date range in the report.
        :param skip_column_header: (report resource) Do not display a line with field names in the report.
        :param skip_report_summary: (report resource) Do not display a line with the number of statistics lines in the report.
        """
    def reports(self) -> YandexDirectClientReportExecutor: ...
    def adextensions(self) -> YandexDirectClientExecutor: ...
    def adgroups(self) -> YandexDirectClientExecutor: ...
    def adimages(self) -> YandexDirectClientExecutor: ...
    def ads(self) -> YandexDirectClientExecutor: ...
    def agencyclients(self) -> YandexDirectClientExecutor: ...
    def audiencetargets(self) -> YandexDirectClientExecutor: ...
    def bidmodifiers(self) -> YandexDirectClientExecutor: ...
    def bids(self) -> YandexDirectClientExecutor: ...
    def businesses(self) -> YandexDirectClientExecutor: ...
    def campaigns(self) -> YandexDirectClientExecutor: ...
    def changes(self) -> YandexDirectClientExecutor: ...
    def clients(self) -> YandexDirectClientExecutor: ...
    def creatives(self) -> YandexDirectClientExecutor: ...
    def debugtoken(self, *, client_id: str) -> YandexDirectClientExecutor: ...
    def dictionaries(self) -> YandexDirectClientExecutor: ...
    def dynamicads(self) -> YandexDirectClientExecutor: ...
    def feeds(self) -> YandexDirectClientExecutor: ...
    def keywordbids(self) -> YandexDirectClientExecutor: ...
    def keywords(self) -> YandexDirectClientExecutor: ...
    def keywordsresearch(self) -> YandexDirectClientExecutor: ...
    def leads(self) -> YandexDirectClientExecutor: ...
    def negativekeywordsharedsets(self) -> YandexDirectClientExecutor: ...
    def retargeting(self) -> YandexDirectClientExecutor: ...
    def sitelinks(self) -> YandexDirectClientExecutor: ...
    def smartadtargets(self) -> YandexDirectClientExecutor: ...
    def turbopages(self) -> YandexDirectClientExecutor: ...
    def vcards(self) -> YandexDirectClientExecutor: ...
