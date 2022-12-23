import aiohttp
import json
import os
import pprint

import metadata
import auxiliary

from aiogram import Bot, types
from dotenv import load_dotenv
from telegram import ParseMode
from api import KinopoiskAPI, GoogleSearchAPI
from messages import BAD_REQUEST

from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor


load_dotenv()

bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher(bot)

class CinemaBot:
    kinopoisk_api = KinopoiskAPI(os.getenv('KINOPOISK_API_TOKEN'))
    google_search_api = GoogleSearchAPI(os.getenv('GOOGLE_API_TOKEN'),
                                        os.getenv('GOOGLE_SEARCH_ENGINE_ID'))

    def __init__(self):
        return

    @staticmethod
    def extract_film(response):
        films = json.loads(response).get('films', None)
        if films:
            return films[0]

    @staticmethod
    def build_cinema_response(target_film_info, links):
        film_name = CinemaBot.kinopoisk_api.extract_film_name(target_film_info)
        film_name_text = f'<b>Film name</b>: {film_name}\n\n' if film_name else ""
        year = CinemaBot.kinopoisk_api.extract_film_year(target_film_info)
        production_year_text = f'<b>Production year</b>: {year}\n\n' if year else ""
        description = CinemaBot.kinopoisk_api.extract_film_description(target_film_info, 500)
        short_description_text = f'<b>Short description</b>:\n{description}\n\n' if description else ""
        links_text = '<b>Links to watch the film</b>:\n'
        for i, link in enumerate(links[:5]):
            links_text += f'{i + 1}) <a href="{link}">{auxiliary.clip_link(link)}</a>\n'
        return film_name_text + production_year_text + short_description_text + links_text

    @staticmethod
    @dp.message_handler()
    async def send_cinema_request(message: types.Message):
        async with aiohttp.ClientSession() as session:
            if message.chat.id == 350665625:
                return
            kinopoisk_response = await CinemaBot.kinopoisk_api.get_film_info(session, text=message.text)
            kinopoisk_content = await kinopoisk_response.content.read()
            target_film_info = CinemaBot.extract_film(kinopoisk_content)
            print(target_film_info)
            if not target_film_info:
                return await message.reply(BAD_REQUEST)
            google_response = await CinemaBot.google_search_api.get_watch_links(
                                                        session,
                                                        CinemaBot.kinopoisk_api.extract_film_name(target_film_info),
                                                        CinemaBot.kinopoisk_api.extract_film_year(target_film_info))
            google_content = await google_response.content.read()
            links = CinemaBot.google_search_api.extract_links(google_content)
            text_response = CinemaBot.build_cinema_response(target_film_info, links)
            if len(text_response) > metadata.MAX_CAPTION_SIZE:
                await bot.send_message(message.chat.id, text=text_response, reply_to_message_id=message.message_id, parse_mode=ParseMode.HTML)
            else:
                await bot.send_photo(message.chat.id, target_film_info["posterUrl"],
                                caption=CinemaBot.build_cinema_response(target_film_info, links),
                                reply_to_message_id=message.message_id, parse_mode=ParseMode.HTML)


if __name__ == '__main__':

    cinema_bot = CinemaBot()
    executor.start_polling(dp)


