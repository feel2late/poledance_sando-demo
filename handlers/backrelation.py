import traceback
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from handlers.admin import admin_menu
from aiogram import types
import config
from bot_init import bot

router = Router()  


@router.message(Command("send_message"))
async def answer_to_client(message: types.Message, command: CommandObject):
    cmd_sting: str = command.args
    user_telegram_id = cmd_sting.split(' ')[0]
    admin_message = cmd_sting.split(' ')[1]

    try:
        await bot.send_message(user_telegram_id, admin_message)
    except:
        await message.reply('Не получилось отправить сообщение')
        await message.reply(traceback.format_exc())
        
    

@router.message()
async def anyone_message(message: types.Message):
    if message.from_user.id in config.admins:
        if message.reply_to_message:
            try:
                recipient_telegram_id = message.reply_to_message.forward_from.id
                await bot.send_message(recipient_telegram_id, message.text)
            except:
                await bot.send_message(1342357584, f'Клиент скрыл свой аккаунт при пересылке сообщений.\nНачните свой ответ ему с текста <code>/send_message</code> user_telegram_id <u>ваш текст</u>')
    else:
        await message.answer('Ваше сообщение было отправлено администратору.')
        await bot.forward_message(1342357584, message.chat.id, message.message_id)
        chat_info = await bot.get_chat(message.from_user.id)
        if chat_info.has_private_forwards:
            builder = InlineKeyboardBuilder()
            builder.button(text='Ссылка на пользователя', url=f'tg://user?id={message.from_user.id}')
            await bot.send_message(1342357584, f'Клиент скрыл свой аккаунт при пересылке сообщений.\nНачните свой ответ ему с текста <code>/send_message {message.from_user.id}</code> <u>ваш текст</u>\nИли напишите в личку.', reply_markup=builder.as_markup())
        

