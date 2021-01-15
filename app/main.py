import asyncio
import logging
import os
import subprocess
import tempfile
import uuid

import aiofiles
import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.bot.api import TelegramAPIServer

logging.basicConfig(level=logging.ERROR)

API_TOKEN = os.getenv('API_TOKEN')
TG_API_URL = os.getenv('TG_API_URL')

local_server = TelegramAPIServer.from_base(TG_API_URL)

bot = Bot(token=API_TOKEN, server=local_server)
dp = Dispatcher(bot)

clients = []


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    hello_msg = (
        'Привет, я умею скачивать видео c https://bbb.edu.vsu.ru.\n\n'
        'Для cкачивания видео отправьте мне ссылку вида: '
        'https://bbb.edu.vsu.ru/presentation/XXX/video/webcams.webm '
        '(ссылку можно скопировать, нажав правой кнопкой по видео в *полноэкранном режиме*).'
    )
    await message.reply(hello_msg, parse_mode='Markdown')


@dp.message_handler()
async def get_link(message: types.Message):

    if message.chat.id in clients:
        await message.answer('Ваш запрос обрабатывается, подождите!')
        return

    link = message.text
    try:
        id_ = link.split('/')[4]
    except IndexError:
        async with aiofiles.open('400.mp4', 'rb') as video:
            await message.answer_video(await video.read())
        return
    link_begin = f'https://bbb.edu.vsu.ru/presentation/{id_}'
    link_audio = f'{link_begin}/video/webcams.webm'
    link_video = f'{link_begin}/deskshare/deskshare.webm'

    clients.append(message.chat.id)

    async with aiohttp.ClientSession() as session:
        await message.answer('1/4. Скачиваю видео...')
        async with session.get(link_video) as resp:
            if resp.status == 200:
                video_file = tempfile.NamedTemporaryFile(suffix='.webm')
                video_file.write(await resp.read())
            else:
                await message.answer('Что-то пошло не так :(')
                clients.remove(message.chat.id)
                return

        await message.answer('2/4. Скачиваю аудио...')
        async with session.get(link_audio) as resp:
            if resp.status == 200:
                audio_file = tempfile.NamedTemporaryFile(suffix='.webm')
                audio_file.write(await resp.read())
            else:
                await message.answer('Что-то пошло не так :(')
                clients.remove(message.chat.id)
                return

    await message.answer('3/4. Обрабатываю данные...')

    output_filename = str(uuid.uuid4()) + '.webm'

    p1 = subprocess.Popen(
        f'ffmpeg -i {video_file.name} -i {audio_file.name} -c copy -map 0:v:0 -map 1:a:0 {output_filename}',
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        shell=True
    )

    while True:
        try:
            p1.communicate(timeout=.1)
            break
        except subprocess.TimeoutExpired:
            await asyncio.sleep(1)

    if p1.returncode:
        await message.answer('Что-то пошло не так :(')
        clients.remove(message.chat.id)

    video_file.close()
    audio_file.close()

    output_file = await aiofiles.open(output_filename, 'rb')

    await message.answer('4/4. Загружаю видео в Telegram...')
    await message.answer_video(await output_file.read(), supports_streaming=True)

    await output_file.close()

    await message.answer('Готово!')

    clients.remove(message.chat.id)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
