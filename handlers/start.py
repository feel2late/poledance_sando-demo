from aiogram import Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters.command import Command
from aiogram import F
import db_requests
from aiogram import Router
from aiogram.fsm.context import FSMContext
from handlers.menu import menu
router = Router()  

@router.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    user = await db_requests.check_user_registation(message.from_user.id)
    if not user:
        builder = ReplyKeyboardBuilder()
        builder.row(
            types.KeyboardButton(text="Отправить свой номер.", request_contact=True)
            )
        await message.answer('Привет!\nЧтобы зарегистрироваться, нажми кнопку \"Отправить свой номер\".', reply_markup=builder.as_markup(resize_keyboard=True))
    else:
        await message.answer('Добро пожаловать обратно!', reply_markup=types.ReplyKeyboardRemove())
        await menu(message, state)


@router.message(F.contact)
async def on_user_shared(message: types.Message, state: FSMContext):
    if message.from_user.id == message.contact.user_id:
        check_registartion = await db_requests.check_user_registation(message.from_user.id)
        user_object = await db_requests.get_user_by_phonenumber(message.contact.phone_number[1:] if message.contact.phone_number.startswith('+') else message.contact.phone_number)
        if user_object:
            await db_requests.merging_user_objects_by_phonenumber(message.from_user.id, user_object.phone_number)
            await message.answer('Вы успешно зарегистрировались!\nВсе данные о ваших абонементах, тренировках и записях синхронизированы.', reply_markup=types.ReplyKeyboardRemove())
            await menu(message, state) 
            return
        if not check_registartion:
            registration = await db_requests.registration_user(message.from_user.id, 
                                                message.contact.phone_number[1:] if message.contact.phone_number.startswith('+') else message.contact.phone_number, 
                                                message.from_user.first_name, 
                                                message.from_user.last_name if message.from_user.last_name else '')
            if registration:
                await message.answer('Вы успешно зарегистрировались!\nВоспользуйтесь меню, чтобы узнать информацию о школе или записаться на пробное занятие.', reply_markup=types.ReplyKeyboardRemove())
                await menu(message, state) 