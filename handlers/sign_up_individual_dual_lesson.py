import asyncio
import calendar
import datetime
import uuid
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
import db_requests
import models
from aiogram.fsm.context import FSMContext
from yookassa import Payment

router = Router()  

@router.callback_query(F.data == 'buy_individual_dual_lesson')
async def buy_individual_lesson(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    coaches = await db_requests.get_coaches()

    if coaches:
        message_text = 'Выберите преподавателя индивидуального парного занятия.\n\n'
    else:
        message_text = 'К сожалению, на текущий момент нет доступных преподавателей.'

    builder = InlineKeyboardBuilder()
    for coach in coaches:
        builder.button(text=f'{coach.first_name} {coach.last_name}', callback_data=f'select_coach_for_individual_dual_sign_up_{coach.id}')
    builder.button(text='🔙 Личный кабинет', callback_data='profile')    
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('select_coach_for_individual_dual_sign_up_'))
async def select_coach_for_individual_sign_up(callback: CallbackQuery, state: FSMContext):
    coach = await db_requests.get_coach_by_id(callback.data[41:])
    await state.update_data(coach=coach)
    month_names = [
        "Январь", "Февраль", "Март", "Апрель",
        "Май", "Июнь", "Июль", "Август",
        "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]

    message_text = (f'Выберите месяц.\n\n'
                    f'ℹ️ {coach.first_name + " " + coach.last_name} ➔ индивидуальное парное занятие')
    available_trainings = await db_requests.get_individual_dual_trainings(coach.id, 
                                                                   datetime.datetime.utcnow() + datetime.timedelta(hours=7), 
                                                                   datetime.datetime.utcnow() + datetime.timedelta(days=100))
    available_months = set()
    for available_training in available_trainings:
        available_months.add(available_training.training_date.month)

    builder = InlineKeyboardBuilder()
    for available_month in available_months:
        year = datetime.datetime.utcnow().year if available_month >= datetime.datetime.utcnow().month else datetime.datetime.utcnow().year + 1
        builder.button(text=f'{month_names[available_month - 1]}', callback_data=f'select_month_for_individual_dual_sign_up_{available_month}.{year}')
    builder.button(text='🔙 Выбор тренера', callback_data=f'buy_individual_lesson') 
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('select_month_for_individual_dual_sign_up_'))
async def select_month_for_individual_sign_up(callback: CallbackQuery, state: FSMContext):
    selected_date = callback.data[41:].split('.')
    selected_month = selected_date[0]
    selected_year = selected_date[1]
    await state.update_data(selected_month=selected_month, selected_year=selected_year)
    builder = InlineKeyboardBuilder()
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    now = datetime.datetime.utcnow()
    if int(selected_month) > now.month:
        start_date = datetime.datetime(int(selected_year), int(selected_month), 1, 0, 0)
    else:
        start_date = now + datetime.timedelta(hours=7)
    
    message_text = (f'Выберите день.\n\n'
                    f'ℹ️ {coach.first_name + " " + coach.last_name} ➔ индивидуальное парное занятие ➔ xx.{selected_month}.{selected_year}')
    
    available_trainings = await db_requests.get_individual_dual_trainings(coach.id, 
                                                                   start_date, 
                                                                   datetime.datetime(int(selected_year), int(selected_month), calendar.monthrange(int(selected_year), int(selected_month))[1], 23, 59))
    # С помощью множества убираем дубли дат.
    available_days = set()
    for available_training in available_trainings:
        available_days.add(available_training.training_date.replace(hour=0, minute=0, second=0, microsecond=0))
    
    # Сортируем даты, для правильного вывода в меню по возрастанию
    sorted_available_days = sorted(available_days)

    for available_day in sorted_available_days:
        builder.button(text=f'{available_day.day}.{available_day.month}.{available_day.year} ({days[datetime.datetime(available_day.year, available_day.month, available_day.day).weekday()]})', 
                       callback_data=f'select_day_for_individual_dual_sign_up_{available_day.day}')
    builder.button(text='🔙 Выбор месяца', callback_data=f'select_coach_for_individual_dual_sign_up_{coach.id}') 
    builder.adjust(1)
    
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('select_day_for_individual_dual_sign_up_'))
async def select_day_for_individual_dual_sign_up(callback: CallbackQuery, state: FSMContext):
    selected_day = callback.data[39:]
    await state.update_data(selected_day=selected_day)
    fsmdata = await state.get_data()
    selected_month = fsmdata.get('selected_month')
    selected_year = fsmdata.get('selected_year')
    coach = fsmdata.get('coach')

    message_text = (f'Выберите время.\n\n'
                    f'ℹ️ {coach.first_name + " " + coach.last_name} ➔ индивидуальное парное занятие ➔ {selected_day}.{selected_month}.{selected_year}')

    available_trainings = await db_requests.get_individual_dual_trainings(coach.id, 
                                                                   datetime.datetime(2023, int(selected_month), int(selected_day)) + datetime.timedelta(hours=7),
                                                                   datetime.datetime(2023, int(selected_month), int(selected_day)) + datetime.timedelta(days=1, hours=7))

    builder = InlineKeyboardBuilder()
    for available_training in available_trainings:
        user_enrollment = await db_requests.check_user_enrollment(callback.from_user.id, available_training.id)
        builder.button(text=f'{"✅ " if user_enrollment else ""}{datetime.datetime.strftime(available_training.training_date, "%H:%M")}', callback_data=f'select_individual_dual_training_for_sign_up_{available_training.id}')
    builder.button(text='🔙 Выбор дня', callback_data=f'select_month_for_individual_dual_sign_up_{selected_month}.{selected_year}') 
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('select_individual_dual_training_for_sign_up_'))
async def select_individual_dual_training_for_sign_up(callback: CallbackQuery, state: FSMContext):
    training_id = callback.data[44:]
    training = await db_requests.get_training_by_id(training_id)
    fsmdata = await state.get_data()
    selected_direction = fsmdata.get('selected_direction')
    selected_month = fsmdata.get('selected_month')
    selected_day = fsmdata.get('selected_day')
    selected_year = fsmdata.get('selected_year')
    coach = fsmdata.get('coach')

    user_enrollment = await db_requests.check_user_enrollment(callback.from_user.id, training.id)
    if user_enrollment:
        await callback.answer('Свяжитесь с администратором, чтобы отменить или перенести тренировку.', show_alert=True)
        return 
    else:
        await db_requests.enrollment_on_training(callback.from_user.id, training.id)
        payment = Payment.create({
        "amount": {
            "value": f"{coach.for_two_lesson_price}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/Poledance_sando_bot"
        },
        "capture": True,
        "description": f"Оплата индивидуального занятия с тренером {datetime.datetime.strftime(training.training_date, '%d.%m.%Y %H:%M')}"
        }, uuid.uuid4())
    
        builder = InlineKeyboardBuilder()
        builder.button(text='Оплатить', url=payment.confirmation.confirmation_url)
        builder.button(text='🔙 Назад в профиль', callback_data='profile')
        builder.adjust(1)
        message_text = (f'Вы забронировали индивидуальное парное занятие у тренера {coach.first_name + " " + coach.last_name} на {datetime.datetime.strftime(training.training_date, "%d.%m.%Y %H:%M")}.\n\n'
                        'Пожалуйста, оплатите бронирование в течении одного часа, иначе бронь будет снята.')
        message_pay = await callback.message.edit_text(message_text, reply_markup=builder.as_markup())

        for i in range(180):
            payment_status = Payment.find_one(payment.id)
            if payment_status.status == 'succeeded':
                await message_pay.edit_reply_markup(answer_markup='')
                builder = InlineKeyboardBuilder()
                builder.button(text='🔙 Назад в профиль', callback_data='profile')
                await callback.message.answer(f'😌 Спасибо, оплата получена, бронирование подтверждено.', reply_markup=builder.as_markup()) 
                return
            elif payment_status.status == 'canceled':
                break
            else:
                await asyncio.sleep(20)
        builder = InlineKeyboardBuilder()
        builder.button(text='🔙 Назад в профиль', callback_data='profile')
        await db_requests.unenroll_training(callback.from_user.id, training.id)
        try:
            await message_pay.edit_reply_markup(answer_markup='')
        except:
            pass
        await callback.message.answer(f'🤷‍♂️ Время на оплату индивидуального парного занятия у тренера {coach.first_name + " " + coach.last_name} в {datetime.datetime.strftime(training.training_date, "%d.%m.%Y %H:%M")} вышло или платёж завершился с ошибкой.\n\nБронирование отменено.')
            
    
    