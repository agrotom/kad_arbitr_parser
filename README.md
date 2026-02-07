# Запуск сервиса
Запуск через Docker: `docker run -d   -p 127.0.0.1:9001:9001   --shm-size=1gb   kad_arbitr_parser`

__Использование `--reload` строго не рекомендуется, так как этот аргумент ломает асинхронный Playwright, на котором и работает парсер__

# Использование
Сервер слушает два эндпоинта:

* ## `/getPage`
    Пример: `/getPage?url=https://kad.arbitr.ru/card?number=%D0%9063-317/2025`

    Query-параметры: url - ссылка на карточку дела.

    Возвращает `application/json` вида:
	
    ``` json
    {
        "source": "...",
        "pdf_links": [ "...", "...", "...", ... ],
    }
	```

    |Ключ|Значение|
    |:------:|:------:|
    |source|text/html|
    |pdf_links|ссылки на все определения или решения по этому делу|

* ## `/getFile`
    Пример: `/getFile?url=https://kad.arbitr.ru/Document/Pdf/18e53389-7779-49ea-9492-7ac50efea5eb/827925ad-cea5-4e1b-8f25-0271b3e8718c/A60-47901-2022_20240528anovlenija.pdf`

    Query-параметры: url - ссылка на файл PDF.

    Возвращает `application/pdf` (бинарный).