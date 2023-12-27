import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import db_requests
from aiogram.fsm.context import FSMContext
from bot_init import bot
import json
from aiogram import types
import config


router = Router()  

@router.message(Command("menu")) 
async def menu(message: Message, state: FSMContext, callback=False):
    #await db_requests.create_other_settings()
    await state.set_state()
    await state.clear()
    user = await db_requests.get_user(message.from_user.id)
    if callback == False and not await db_requests.check_user_registation(message.from_user.id):
        builder = ReplyKeyboardBuilder()
        builder.button(text="Отправить свой номер.", request_contact=True)
        await message.answer('Нажмите кнопку "Отправить свой номер", чтобы зарегистрироваться.', reply_markup=builder.as_markup(resize_keyboard=True))
        return
    builder = InlineKeyboardBuilder()
    builder.button(text='👤 Личный кабинет', callback_data='profile')
    builder.button(text='💵 Прайс лист', callback_data='price_list')
    builder.button(text='📆 Расписание групповых занятий', callback_data='group_timetable')
    builder.button(text='📆 Расписание инд. занятий', callback_data='individual_timetable')
    builder.button(text='🦸‍♀️ Преподаватели', callback_data='teachers')
    if len(await db_requests.get_all_user_subscriptions(message.from_user.id)) == 0 and not user.was_probe:
        builder.button(text='👀 Купить пробное занятие', callback_data='trial_lesson')
    builder.button(text='⏳ Аренда школы', callback_data='school_rent')
    builder.button(text='🛍 Магазин', url=f'https://t.me/shop_poledance_sando_bot')
    #builder.button(text='🛍 Магазин', callback_data='shop')
    if message.from_user.id in await db_requests.get_coaches_telegram_id() or message.from_user.id in config.admins:
        builder.button(text='🎓 Тренерская', callback_data='coaching')
    if message.from_user.id in config.admins:
        builder.button(text='📒 Админ меню', callback_data='admin_menu')
        builder.button(text='🔍 Поиск клиента', callback_data='search_client')
    builder.adjust(1)
    
    if callback == True:
        await message.message.edit_text('Здравствуйте!\nВыберите интересующий пункт меню.', reply_markup=builder.as_markup())
    else:
        await message.answer('Здравствуйте!\nВыберите интересующий пункт меню.', reply_markup=builder.as_markup())


@router.callback_query(F.data == "menu")
async def menu_callback(callback: CallbackQuery, state: FSMContext):
    await menu(callback, state, callback=True)


@router.callback_query(F.data == "group_timetable")
async def group_timetable(callback: CallbackQuery):
    available_trainings = await db_requests.get_all_available_trainings()
    message_text = 'Расписание групповых занятий:\n\n'
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    sorted_date = {}
    for training in available_trainings:
        if training.direction_of_training in ['Индивидуальное', 'Индивидуальное парное']:
            continue
        if datetime.datetime.strftime(training.training_date, '%d.%m.%Y') in sorted_date:
            sorted_date[datetime.datetime.strftime(training.training_date, '%d.%m.%Y')].append(training)
        else:
            sorted_date[datetime.datetime.strftime(training.training_date, '%d.%m.%Y')] = [training]

    for date in sorted_date:
        strp_date = datetime.datetime.strptime(date, "%d.%m.%Y")
        message_text += f'<b>{datetime.datetime.strftime(strp_date, "%d.%m")} ({days[datetime.datetime(strp_date.year, strp_date.month, strp_date.day).weekday()]})</b>:\n'
        for training in sorted_date[date]:
            message_text += f'{datetime.datetime.strftime(training.training_date, "%H:%M")} - {training.trainer.first_name} {training.trainer.last_name} - {training.direction_of_training}\n'
        message_text += f'{"-" * 20}\n'

    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Меню', callback_data='menu')
    MESS_MAX_LENGTH = 4096
    if len(message_text) < MESS_MAX_LENGTH:
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    else:
        new_message_text = message_text.replace('<b>', '')
        new_message_text = new_message_text.replace('</b>', '')
        for x in range(0, len(new_message_text), MESS_MAX_LENGTH):
                    mess = new_message_text[x: x + MESS_MAX_LENGTH]
                    await callback.message.answer(mess)
    

@router.callback_query(F.data == "individual_timetable")
async def individual_timetable(callback: CallbackQuery):
    available_trainings = await db_requests.get_individual_trainings(coach_id=False, date_from=datetime.datetime.utcnow() + datetime.timedelta(hours=7), date_to=datetime.datetime.utcnow() + datetime.timedelta(days=30, hours=7))
    message_text = 'Расписание индивидуальных занятий:\n\n'
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    sorted_date = {}
    for training in available_trainings:
        if datetime.datetime.strftime(training.training_date, '%d.%m.%Y') in sorted_date:
            sorted_date[datetime.datetime.strftime(training.training_date, '%d.%m.%Y')].append(training)
        else:
            sorted_date[datetime.datetime.strftime(training.training_date, '%d.%m.%Y')] = [training]

    for date in sorted_date:
        strp_date = datetime.datetime.strptime(date, "%d.%m.%Y")
        message_text += f'<b>{datetime.datetime.strftime(strp_date, "%d.%m")} ({days[datetime.datetime(strp_date.year, strp_date.month, strp_date.day).weekday()]})</b>:\n'
        for training in sorted_date[date]:
            message_text += f'{datetime.datetime.strftime(training.training_date, "%H:%M")} {training.trainer.first_name} {training.trainer.last_name}\n'
        message_text += f'{"-" * 20}\n'

    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Меню', callback_data='menu')
    MESS_MAX_LENGTH = 4096
    if len(message_text) < MESS_MAX_LENGTH:
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    else:
        new_message_text = message_text.replace('<b>', '')
        new_message_text = new_message_text.replace('</b>', '')
        for x in range(0, len(new_message_text), MESS_MAX_LENGTH):
                    mess = new_message_text[x: x + MESS_MAX_LENGTH]
                    await callback.message.answer(mess)


@router.callback_query(F.data == "price_list")
async def price_list(callback: CallbackQuery):
    subscriptions_options = await db_requests.get_all_subscriptions_options()
    message_text = 'Стоимость абонементов и направлений:\n\n<b>Абонементы:</b>\n'
    other_settings = await db_requests.get_other_settings()
    coaches = await db_requests.get_coaches()
    for i, subscription in enumerate(subscriptions_options):
        message_text += f'{i+1}) {subscription.number_of_sessions} занятий - {subscription.price} рублей ({int(subscription.price / subscription.number_of_sessions)} р. занятие)\n'
    message_text += '\n<b>Индивидуальные занятия у тренеров:</b>\n'
    for i, coach in enumerate(coaches):
        message_text += (f'{i+1}) {coach.first_name + " " + coach.last_name}:\n'
                         f'- Индивидуальное: {coach.individual_lesson_price} р.\n'
                         f'- Индивидуальное парное: {coach.for_two_lesson_price} р. (для записи свяжитесь с администратором или тренером)\n\n')

    message_text += (f'<b>Пробное занятие</b> - {other_settings.trial_lesson_cost} рублей\n\n'
                     f'<b>Аренда студии</b>:\n1 час - {other_settings.one_hour_rent} рублей\n2 часа - {other_settings.two_hour_rent} рублей')
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Меню', callback_data='menu')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "school_rent")
async def school_rent(callback: CallbackQuery):
    other_settings = await db_requests.get_other_settings()
    builder = InlineKeyboardBuilder()
    builder.button(text='📲 Написать руководителю', url=f'tg://user?id={1342357584}')
    builder.button(text='🔙 Меню', callback_data='menu')
    builder.adjust(1)
    message_text = ('Стоимость аренды помещения школы:\n'
                    f'1 час - {other_settings.one_hour_rent} рублей.\n'
                    f'2 часа - {other_settings.two_hour_rent} рублей.\n\n'
                    'Для бронирования свяжитесь с руководителем студии: <code>+79996573909</code> Яна Сергеевна\n'
                    'Или отправьте ей сообщение:')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "teachers")
async def teachers(callback: CallbackQuery):
    trainers = await db_requests.get_coaches()
    about_counter = 0
    builder = InlineKeyboardBuilder()
    for trainer in trainers:
        if trainer.about:
            about_counter += 1
            builder.button(text=f'{trainer.first_name + " " + trainer.last_name}', callback_data=f'extended_trainer_discription_{trainer.id}')
    builder.button(text='🔙 Меню', callback_data='menu')
    message_text = '💃 Наши преподаватели:\n\n'
    for trainer in trainers:
        message_text += f'🔆 <b>{trainer.first_name + " " + trainer.last_name}</b>\n'
        if trainer.about:
            message_text += f'{trainer.about.about}\n\n'
        else:
            message_text += '\n'
    if about_counter > 0:
        message_text += '⬇️ Посмотреть фото и дипломы тренера вы можете выбрав его в меню ниже.'
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("extended_trainer_discription_"))
async def extended_trainer_discription(callback: CallbackQuery):
    await callback.message.delete()
    coach_id = callback.data[29:]
    coach = await db_requests.get_coach_by_id(coach_id)
    if coach.about.trainer_photo:
        await bot.send_photo(callback.from_user.id, coach.about.trainer_photo)
    if coach.about.trainer_diplomas:
        diplomas_id = json.loads(coach.about.trainer_diplomas)
        loaded_diplomas = []
        for id, diploma_id in enumerate(diplomas_id):
            loaded_diplomas.append(types.InputMediaPhoto(media=diploma_id, caption=f'{id+1}'))
        await bot.send_media_group(callback.from_user.id, loaded_diplomas)

    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Меню', callback_data='menu')
    message_text = f'<b>{coach.first_name + " " + coach.last_name}</b>\n'
    if coach.about.about:
        message_text += f'{coach.about.about}\n\n'

    await callback.message.answer(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "shop")
async def shop(callback: CallbackQuery):
    await callback.answer('Скоро будет 🎀', show_alert=True)


@router.message(Command('my_id'))
async def get_chat_id(message: types.Message):
    await message.answer(f'You telegram id: {message.from_user.id}')