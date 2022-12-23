import aiohttp
import asyncio
import daemon
import json
import os

from extra import auxiliary, metadata

from aiogram import Bot, types
from dotenv import load_dotenv
from telegram import ParseMode
from api import KinopoiskAPI, GoogleSearchAPI
from database import CinemaDatabaseHandler
from extra.messages import BAD_REQUEST_MESSAGE, HELP_COMMAND_MESSAGE, NOT_FOUND_HISTORY_MESSAGE, \
                           NONE_LINKS_MESSSAGE

from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

load_dotenv()


class CinemaBot:
    def __init__(self):
        self.database_dispatcher = CinemaDatabaseHandler(os.getcwd() + metadata.CINEMA_DATABASE_PATH)
        if not self.database_dispatcher.exists():
            asyncio.get_event_loop().run_until_complete(self.database_dispatcher.create_database())

        self.kinopoisk_api = KinopoiskAPI(os.getenv('KINOPOISK_API_TOKEN'))
        self.google_search_api = GoogleSearchAPI(os.getenv('GOOGLE_API_TOKEN'),
                                                 os.getenv('GOOGLE_SEARCH_ENGINE_ID'))

        self.bot = Bot(token=os.getenv('BOT_TOKEN'))
        self.dispatcher = Dispatcher(self.bot)
        self.init_dispatcher()

    def init_dispatcher(self):
        self.dispatcher.register_message_handler(self.get_history, commands=['history'])
        self.dispatcher.register_message_handler(self.get_stats, commands=['stats'])
        self.dispatcher.register_message_handler(self.get_help, commands=['start', 'help'])
        self.dispatcher.register_message_handler(self.get_cinema_info)

    def run(self):
        executor.start_polling(self.dispatcher)

    @staticmethod
    def extract_film(response):
        if not response:
            return
        films = json.loads(response).get('films', None)
        if films:
            return films[0]

    def build_get_cinema_info_response(self, target_film_info, links):
        film_name = self.kinopoisk_api.extract_film_name(target_film_info)
        film_name_text = f'<b>Название фильма:</b> {film_name}\n\n' if film_name else ""
        year = self.kinopoisk_api.extract_film_year(target_film_info)
        production_year_text = f'<b>Год выпуска:</b> {year}\n\n' if year else ""
        description = self.kinopoisk_api.extract_film_description(target_film_info, 500)
        short_description_text = f'<b>Краткое описание:</b>\n{description}\n\n' if description else ""
        links_text = '<b>Где можно посмотреть:</b>\n'            
        if links:
            for i, link in enumerate(links[:5]):
                links_text += f'{i + 1}) <a href="{link}">{auxiliary.clip_link(link)}</a>\n'
        else:
            links_text += NONE_LINKS_MESSSAGE 
        return film_name_text + production_year_text + short_description_text + links_text

    async def get_cinema_info(self, message: types.Message):
        async with aiohttp.ClientSession() as session:
            await self.database_dispatcher.update_history(message.from_user.id, message.text)
            kinopoisk_response = await self.kinopoisk_api.get_film_info(session, text=message.text)
            kinopoisk_content = await kinopoisk_response.content.read()
            target_film_info = self.kinopoisk_api.get_first_film(kinopoisk_content)
            if not target_film_info:
                return await self.bot.send_message(message.chat.id, text=BAD_REQUEST_MESSAGE,
                                                   reply_to_message_id=message.message_id, parse_mode=ParseMode.HTML)

            await self.database_dispatcher.update_stats(message.from_user.id,
                                                        self.kinopoisk_api.extract_film_name(target_film_info))

            google_response = await self.google_search_api.get_watch_links(
                                                        session,
                                                        self.kinopoisk_api.extract_film_name(target_film_info),
                                                        self.kinopoisk_api.extract_film_year(target_film_info))

            google_content = await google_response.content.read()
                
            links = self.google_search_api.extract_links(google_content) 

            response_text = self.build_get_cinema_info_response(target_film_info, 
                                                                links if links else [])
            if len(response_text) > metadata.MAX_CAPTION_SIZE:
                await self.bot.send_message(message.chat.id, text=response_text, reply_to_message_id=message.message_id,
                                            parse_mode=ParseMode.HTML)
            else:
                await self.bot.send_photo(message.chat.id, target_film_info["posterUrl"],
                                          caption=response_text,
                                          reply_to_message_id=message.message_id, parse_mode=ParseMode.HTML)

    async def get_help(self, message):
        response_text = HELP_COMMAND_MESSAGE
        await self.bot.send_message(message.chat.id, text=response_text, reply_to_message_id=message.message_id,
                                    parse_mode=ParseMode.HTML)

    @staticmethod
    def build_get_history_response(history):
        if not history:
            response_text = NOT_FOUND_HISTORY_MESSAGE
        else:
            response_text = "<b>Вот твоя история поиска:</b>\n"
            for i, query in enumerate(history):
                new_row = f'{i + 1}) {query}\n'
                if len(response_text + new_row) > metadata.MAX_MESSAGE_SIZE:
                    break
                response_text += new_row
        return response_text

    async def get_history(self, message):
        history = await self.database_dispatcher.get_user_history(message.from_user.id)
        response_text = self.build_get_history_response(history)
        await self.bot.send_message(message.chat.id, text=response_text, reply_to_message_id=message.message_id,
                                    parse_mode=ParseMode.HTML)

    @staticmethod
    def build_get_stats_response(stats):
        if not stats:
            response_text = NOT_FOUND_HISTORY_MESSAGE
        else:
            response_text = "<b>Вот какие фильмы я тебе уже показывал:</b>\n"
            for i, (film_name, count) in enumerate(stats):
                new_row = f'<b>{i + 1})</b> {film_name} <b>{count}</b> раз(а)\n'
                if len(response_text + new_row) > metadata.MAX_MESSAGE_SIZE:
                    break
                response_text += new_row
        return response_text

    async def get_stats(self, message):
        history = await self.database_dispatcher.get_user_stats(message.from_user.id)
        response_text = self.build_get_stats_response(history)
        await self.bot.send_message(message.chat.id, text=response_text, reply_to_message_id=message.message_id,
                                    parse_mode=ParseMode.HTML)


if __name__ == '__main__':
    cinema_bot = CinemaBot()
    with daemon.DaemonContext():
        cinema_bot.run()
