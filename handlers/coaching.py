import asyncio
import uuid
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
import db_requests
import models
import datetime
from aiogram.fsm.context import FSMContext


router = Router()  

@router.callback_query(F.data == "coaching")
async def coaching(callback: CallbackQuery, state: FSMContext):
    coaches = await db_requests.get_coaches()
    builder = InlineKeyboardBuilder()
    message_text = 'Выберите тренера, чтобы увидеть его расписание на ближайшие 10 дней.'
    for coach in coaches:
        builder.button(text=f'{coach.first_name + " " + coach.last_name}', callback_data=f'coach_shchedule_{coach.id}')
    builder.button(text='🔙 Меню', callback_data='menu')
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("coach_shchedule_"))
async def coach_shchedule_(callback: CallbackQuery, state: FSMContext):
    coach_id = callback.data[16:]
    coach = await db_requests.get_coach_by_id(coach_id)
    coach_trainings = await db_requests.get_trainings_by_coach(coach.id, datetime.datetime.utcnow() + datetime.timedelta(hours=7), datetime.datetime.utcnow().replace(hour=23, minute=59) + datetime.timedelta(days=10))
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    if coach_trainings:
        message_text = f'Запланированные тренировки для {coach.first_name} {coach.last_name} на ближайшие 10 дней.\n\n'
        for training in coach_trainings:
            enrollments = await db_requests.get_training_enrollments(training.id)
            message_text += f'{datetime.datetime.strftime(training.training_date, "%d.%m %H:%M")} ({days[datetime.datetime(training.training_date.year, training.training_date.month, training.training_date.day).weekday()]}) - {training.direction_of_training}.\n'
            for i, enrollment in enumerate(enrollments):
                message_text += f'{i+1}) {enrollment.user.first_name + " " + enrollment.user.last_name} - {enrollment.user.phone_number}\n'
            message_text += '\n'
    else:
        message_text = f'Для {coach.first_name} {coach.last_name} нет запланированных тренировок в ближайшие 10 дней.\n\n'
    
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Выбор тренера', callback_data='coaching')
    builder.button(text='🔙 Меню', callback_data='menu')
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())