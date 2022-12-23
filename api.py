import metadata
import json


class KinopoiskAPI:
    def __init__(self, api_token):
        self.api_token = api_token
        self.url = metadata.KINOPOISK_URL

    @staticmethod
    def extract_film_name(film_info):
        return film_info.get("nameRu", "") if film_info.get("nameRu", "") else film_info.get("nameEn", "")

    @staticmethod
    def extract_film_year(film_info):
        return film_info.get("year", "")

    @staticmethod
    def get_first_film(data):
        films = json.loads(data).get('films', None)
        if films:
            return films[0]

    @staticmethod
    def extract_film_description(film_info, symbols):
        clipped_description = film_info.get("description", "")[:symbols]
        return clipped_description[:clipped_description.rfind(".")+1]

    async def get_film_info(self, session, text, pages=1):
        response = await session.request(
            method='GET',
            url=self.url,
            headers={
                'X-API-KEY': self.api_token,
                'Content-Type': 'application/json'
            },
            params={
                'keyword': text,
                'pages': pages
            }
        )
        return response


class GoogleSearchAPI:
    def __init__(self, api_token, engine_id):
        self.api_token = api_token
        self.engine_id = engine_id
        self.url = metadata.GOOGLE_URL

    @staticmethod
    def extract_links(data):
        items = json.loads(data).get('items', None)
        if items:
            return [item['link'] for item in items]

    async def get_watch_links(self, session, name, year):
        response = await session.request(
            method='GET',
            url=self.url,
            headers={
                'Content-Type': 'application/json'
            },
            params={
                'key': self.api_token,
                'cx': self.engine_id,
                'q': f'{name} {year} смотреть онлайн'
            }
        )
        return response