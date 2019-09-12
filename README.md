# Python библиотека для запросов к [API Яндекс Директ](https://yandex.ru/dev/direct/)

Написано на версии python 3.5

## Установка
```
pip install --upgrade git+https://github.com/pavelmaksimov/tapioca-wrapper#egg=tapioca-wrapper-2019.9.5
pip install --upgrade git+https://github.com/pavelmaksimov/tapioca-yandex-direct.git
```

## Примеры

Примеры находятся в [Ipython Notebook](https://github.com/pavelmaksimov/tapioca-yandex-direct/blob/master/examples.ipynb)

## [Справка](https://yandex.ru/dev/direct/) Api Яндекс Директ

## Документация 
``` python
from tapioca_yandex_direct import YandexDirect

ACCESS_TOKEN = {ваш токен доступа}

api = YandexDirect(
    # Токен доступа.
    access_token=ACCESS_TOKEN, 
    # Когда False не будет повторять запрос, если закончаться баллы.
    # По умолчанию False
    retry_if_not_enough_units=False,
    # Когда True cделает несколько запросов, если кол-во идентификаторов 
    # в условиях фильтрации SelectionCriteria будет больше, 
    # чем можно запросить в одном запросе. Работает для метода "get".
    # По умолчанию True
    auto_request_generation=True,
    # Когда True будет посылать запросы, пока не получит все объекты.
    # По умолчанию True
    receive_all_objects=True,
    # True включить песочницу.
    # По умолчанию False
    is_sandbox=True,
    # Если вы делаете запросы из под агентского аккаунта, 
    # вам нужно указать логин аккаунта для которого будете делать запросы.
    #login="{логин аккаунта Я.Директ}"
    # Язык в котором будут возвращены данные справочников и ошибок. 
    # По умолчанию "ru". Доступны "en" и другие.
    language="ru",
    # Повторять запрос, если будут превышениы лимиты 
    # на кол-во отчетов или запросов.
    # По умолчанию True.
    retry_if_exceeded_limit=True,
    # Кол-во повторов при возникновении серверных ошибок.
    # По умолчанию 5 раз.
    retries_if_server_error=5,
    # =====
    # Параметры для ресурса Reports.
    # Режим формирования отчета: online, offline или auto.
    # По умолчанию "auto"
    processing_mode='offline',
    # Когда True, будет повторять запрос, пока отчет не будет готов.
    # По умолчанию True
    wait_report=True,
    # Если заголовок указан, денежные значения в отчете возвращаются в валюте 
    # с точностью до двух знаков после запятой. Если не указан, денежные 
    # значения возвращаются в виде целых чисел — сумм в валюте, 
    # умноженных на 1 000 000.
    # По умолчанию True
    return_money_in_micros=True,
    # Не выводить в отчете строку с названием отчета и диапазоном дат.
    # По умолчанию True
    skip_report_header=True,
    # Не выводить в отчете строку с названиями полей.
    # По умолчанию True
    skip_column_header=False,
    # Не выводить в отчете строку с количеством строк статистики.
    # По умолчанию True
    skip_report_summary=True,
)
```

Генерация класса **YandexDirect** происходит динамически, 
поэтому узнать о добавленных в схему ресурсах, можно так.
``` python
print(dir(api))
```

## Запрос к ресурсу API. 
Запросы к API выполняются по протоколу HTTPS методом POST.
Входные структуры данных передаются в теле запроса.

```python
# Получить все кампании.
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
result = api.campaigns().post(data=body)

# Создать кампанию.
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
result = api.campaigns().post(data=body)
```

#### Формат возвращаемых данных.
Данные возвращаются в формате объекта **Tapioca**.

```python
print(result)
print(result().status_code)
print(result().response)
print(result().response.headers)
``` 
##### Вернуть в формате **JSON**
```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
result = api.campaigns().post(data=body)
print(result().data)
[{'result': {'Campaigns': [{'Id': 338151,
                            'Name': 'Test API Sandbox campaign 1'}],
             'LimitedBy': 1}},
 {'result': {'Campaigns': [{'Id': 338152,
                            'Name': 'Test API Sandbox campaign 2'}],
             'LimitedBy': 2}},]
# В списке может находится несколько ответов.
```

```python
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
result = api.reports().post(data=body)
print(result().data)
[   
    'Date\tCampaignId\tClicks\tCost\n'
    '2019-09-02\t338151\t12578\t9210750000\n'
]
```

##### Преобразование ответа

Для ответов API Я.Директ есть функция преобразования **transform**.
Она извлечет данные из словаря и соединит все ответы в один список, 
если запросов было несколько.
Работает только запросов с методом "get" и ресурса reports.
```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
result = api.campaigns().post(data=body)
print(result().transform())
[{'Id': 338151, 'Name': 'Test API Sandbox campaign 1'},
 {'Id': 338152, 'Name': 'Test API Sandbox campaign 2'}]
```

```python
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
result = api.reports().post(data=body)
print(result().transform())
[
    ['Date', 'CampaignId', 'Clicks', 'Cost'], 
    ['2019-09-02', '338151', '12578', '9210750000'], 
]
```

## Фичи
Открыть документация метода
```python
api.campaigns().open_docs()
```

Послать запрос в браузере.
```python
api.campaigns().open_in_browser()
```


## Зависимости
- requests 
- [tapioca_wrapper](https://github.com/pavelmaksimov/tapioca-wrapper) 

## Автор
Павел Максимов

Связаться со мной можно в 
[Телеграм](https://t.me/pavel_maksimow) 
и в 
[Facebook](https://www.facebook.com/pavel.maksimow)

Удачи тебе, друг! Поставь звездочку ;)

## Другое
- Как работает обертка [Tapioca](http://tapioca-wrapper.readthedocs.org/en/stable/quickstart.html)
