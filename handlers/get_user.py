import calendar
import datetime
import traceback
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
import db_requests
import models
from states.add_coach import AddCoach
from states.edit_coach import EditCoach
from states.add_direction import AddDirection
from states.add_subscription_for_user import AddSubscriptionByAdmin
from states.get_user import GetUser
from states.add_new_client import AddClient
from states.edit_subscription import EditUserSubscription
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from callback_factories.change_direction_status import ChangeDirectionStatus
from callback_factories.select_shedule_day import SelectScheduleDay
from bot_init import bot
import time
from modules.check_sub_for_intersections import check_sub_for_intersections

router = Router()  


@router.callback_query(F.data == "search_client")
async def search_client(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(GetUser.user_phonenumber)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text('Пришлите номер телефона клиента', reply_markup=builder.as_markup())


@router.callback_query(F.data == "user_profile")
async def user_profile(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await user_phonenumber_recieved(callback.message, state, from_create=True)


@router.message(StateFilter(GetUser.user_phonenumber))
async def user_phonenumber_recieved(message: Message, state: FSMContext, from_create=False):
    await state.set_state()
    if from_create:
        fsmdata = await state.get_data()
        user_phonenumber = fsmdata.get('user_phonenumber') if fsmdata.get('user_phonenumber') else (fsmdata.get('user')).phone_number
    else:
        user_phonenumber = message.text.replace(' ', '')

    if user_phonenumber.startswith('9'):
        user_phonenumber = '7' + user_phonenumber
    elif user_phonenumber.startswith('8'):
        user_phonenumber = '7' + user_phonenumber[1:]
    elif user_phonenumber.startswith('+'):
        user_phonenumber = user_phonenumber[1:]    

    if len(user_phonenumber) != 11:
        await message.answer('Проверьте, что вы не ошиблись в номере телефона. Количество цифр не соответствует номеру телефона.\n\nЖду правильный номер.')
        await state.set_state(GetUser.user_phonenumber)
        return
    
    user = await db_requests.get_user_by_phonenumber(user_phonenumber)
    if user:
        await state.update_data(user=user)
        actual_subscription: models.Subscription = await db_requests.get_actual_subscription(user_phone=user.phone_number)
        all_actual_subscriptions = models.Subscription = await db_requests.get_all_actual_user_subscriptions(user_phone=user.phone_number)
        if actual_subscription:
            message_text = (f'Пользователь: {user.first_name + " " + user.last_name}\n'
                            'Действующий абонемент.\n'
                            f'Действует до: {datetime.datetime.strftime(actual_subscription.expiration_date, "%d.%m.%Y")}\n'
                            f'Всего занятий по абонементу: {actual_subscription.number_of_sessions}\n'
                            f'Запланировано занятий по абонементу: {len(await db_requests.get_user_enrollments(user_phone=user.phone_number, date_from=datetime.datetime.utcnow() + datetime.timedelta(hours=7), date_to=actual_subscription.expiration_date + datetime.timedelta(days=1), without_individual=True))}\n'
                            f'Использовано занятий по абонементу: {len(await db_requests.get_user_enrollments(user_phone=user.phone_number, date_from=actual_subscription.purchase_date, date_to=datetime.datetime.utcnow() + datetime.timedelta(hours=7), without_individual=True))}\n')
            if len(all_actual_subscriptions) > 1:
                message_text += '\nТакже куплен(ы) абонемент(ы):\n'
                for i, actual_subscription in enumerate(all_actual_subscriptions[1:]):
                    message_text += f'{i + 1}) {actual_subscription.number_of_sessions} занятий, с {datetime.datetime.strftime(actual_subscription.purchase_date, "%d.%m.%Y")} - {datetime.datetime.strftime(actual_subscription.expiration_date, "%d.%m.%Y")}\n'
        else:
            message_text = f'У клиента {user.first_name + " " + user.last_name} нет действующего абонемента\n'

            if all_actual_subscriptions:
                message_text += '\nНо есть ещё не активные абонементы:\n'
                for i, actual_subscription in enumerate(all_actual_subscriptions):
                    message_text += f'{i + 1}) {actual_subscription.number_of_sessions} занятий, с {datetime.datetime.strftime(actual_subscription.purchase_date, "%d.%m.%Y")} - {datetime.datetime.strftime(actual_subscription.expiration_date, "%d.%m.%Y")}\n'
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text='➕ Создать клиента', callback_data=f'add_client_{user_phonenumber}')
        builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
        builder.adjust(1)
        message_text = f'Я не нашёл пользователя с номером телефона {user_phonenumber}.\n\nХотите создать нового клиента?'
        await message.answer(message_text, reply_markup=builder.as_markup())
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text='➕ Добавить абонемент', callback_data=f'admin_add_client_sub')
    builder.button(text='➕ Записать на занятие', callback_data=f'admin_sign_up_lesson')
    builder.button(text='📝 Изменить абонемент', callback_data=f'admin_edit_user_subscription')
    builder.button(text='Запланированные занятия', callback_data=f'admin_user_scheduled_lessons')
    builder.button(text='История занятий', callback_data=f'admin_user_lessons_history')
    builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
    builder.adjust(1)
    await message.answer(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.contains('admin_user_scheduled_lessons'))
async def admin_user_scheduled_lessons(callback: CallbackQuery, state: FSMContext):
    fsmdata = await state.get_data()
    user = fsmdata.get('user')
    builder = InlineKeyboardBuilder()
    user_enrollments = await db_requests.get_user_enrollments(user_phone=user.phone_number,
                                                              date_from=datetime.datetime.utcnow() + datetime.timedelta(hours=7),
                                                              date_to=datetime.datetime.utcnow() + datetime.timedelta(days=90))
    if user_enrollments:
        message_text = 'Запланированные тренировки клиента на 90 дней:\n\n'
        for training in user_enrollments:
            message_text += (f'<b>Дата:</b> {datetime.datetime.strftime(training.training_date, "%d.%m.%Y %H:%M")}\n'
                            f'<b>Направление:</b> {training.direction_of_training}\n'
                            f'<b>Тренер:</b> {training.trainer.first_name} {training.trainer.last_name}\n\n')
        
        builder.button(text='🔙 Кабинет клиента', callback_data='user_profile')
        builder.adjust(1)
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    else:
        message_text = 'У клиента нет запланированных тренировок. 🙅‍♀️'
        builder.button(text='🔙 Кабинет клиента', callback_data='user_profile')  
        builder.adjust(1)
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.contains('admin_user_lessons_history'))
async def admin_user_lessons_history(callback: CallbackQuery, state: FSMContext):
    fsmdata = await state.get_data()
    user = fsmdata.get('user')
    user_enrollments = await db_requests.get_user_enrollments(user_phone=user.phone_number,
                                                              date_from=datetime.datetime.utcnow() - datetime.timedelta(days=90),
                                                              date_to=datetime.datetime.utcnow() + datetime.timedelta(hours=7))
    if user_enrollments:
        message_text = 'История тренировок пользователя за 90 дней:\n\n'
        for training in user_enrollments:
            message_text += (f'<b>Дата:</b> {datetime.datetime.strftime(training.training_date, "%d.%m.%Y %H:%M")}\n'
                            f'<b>Направление:</b> {training.direction_of_training}\n'
                            f'<b>Тренер:</b> {training.trainer.first_name} {training.trainer.last_name}\n\n')
    else:
        message_text = 'У клиента нет прошедших тренировок.\n\n'

    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Кабинет клиента', callback_data='user_profile')  
    builder.adjust(1)
    
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    

@router.callback_query(F.data == "admin_edit_user_subscription")
async def admin_edit_user_subscription(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    fsmdata = await state.get_data()
    user = fsmdata.get('user')
    user_subscriptions = await db_requests.get_all_actual_user_subscriptions(user_phone=user.phone_number)
    
    if len(user_subscriptions) == 0:
        builder.button(text='🔙 Кабинет клиента', callback_data='user_profile')
        await callback.message.edit_text('У клиента нет актуального (действующего/будущего) абонемента для редактирования.', reply_markup=builder.as_markup())
    elif len(user_subscriptions) == 1:
        await state.update_data(subscription_id=user_subscriptions[0].id)
        subscription = await db_requests.get_user_subscription(user_subscriptions[0].id)
        builder.button(text='📈 Количество занятий', callback_data='admin_edit_user_subscription_session')
        builder.button(text='🕐 Дата окончания', callback_data='admin_edit_user_subscription_validity')
        builder.button(text='🗑 Удалить', callback_data='admin_delete_user_subscription')
        builder.button(text='🔙 Кабинет клиента', callback_data='user_profile')
        builder.adjust(1)
        message_text = ('Что хотите изменить в абонементе?\n'
                    f'Дата начала: {subscription.purchase_date}\n'
                    f'Дата окончания: {subscription.expiration_date}\n'
                    f'Занятий в абонементе: {subscription.number_of_sessions}')
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    elif len(user_subscriptions) > 1:
        for subscription in user_subscriptions:
            builder.button(text=f'{datetime.datetime.strftime(subscription.purchase_date, "%d.%m.%y")} - {datetime.datetime.strftime(subscription.expiration_date, "%d.%m.%y")}', callback_data=f'admin_edit_selected_user_subscription_{subscription.id}')
        builder.button(text='🔙 Кабинет клиента', callback_data='user_profile')
        builder.adjust(1)
        await callback.message.edit_text('Выберите абонемент для редактирования.', reply_markup=builder.as_markup())

    
@router.callback_query(F.data.contains("admin_edit_selected_user_subscription_"))
async def admin_edit_user_subscription_(callback: CallbackQuery, state: FSMContext):
    subscription_id = callback.data[38:]
    await state.update_data(subscription_id=subscription_id)
    subscription = await db_requests.get_user_subscription(subscription_id)
    builder = InlineKeyboardBuilder()
    builder.button(text='📈 Количество занятий', callback_data='admin_edit_user_subscription_session')
    builder.button(text='🕐 Дата окончания', callback_data='admin_edit_user_subscription_validity')
    builder.button(text='🗑 Удалить', callback_data='admin_delete_user_subscription')
    builder.button(text='🔙 Выбор абонемента', callback_data='admin_edit_user_subscription')
    builder.adjust(1)
    message_text = ('Что хотите изменить в абонементе?\n'
                    f'Дата начала: {subscription.purchase_date}\n'
                    f'Дата окончания: {subscription.expiration_date}\n'
                    f'Занятий в абонементе: {subscription.number_of_sessions}')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "admin_delete_user_subscription")
async def admin_delete_user_subscription(callback: CallbackQuery, state: FSMContext):
    fsmdata = await state.get_data()
    subscription = await db_requests.get_user_subscription(fsmdata.get('subscription_id'))
    delete_status = await db_requests.delete_user_subscription(subscription.id) 
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Кабинет клиента', callback_data='user_profile') 
    if delete_status:
        await callback.message.edit_text(f'✅ Абонемент успешно удалён.', reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text('❌ Ошибка удаления абонемента.', reply_markup=builder.as_markup())
        

@router.callback_query(F.data == "admin_edit_user_subscription_validity")
async def admin_edit_user_subscription_validity(callback: CallbackQuery, state: FSMContext):
    fsmdata = await state.get_data()
    subscription = await db_requests.get_user_subscription(fsmdata.get('subscription_id'))
    await state.set_state(EditUserSubscription.expiration_date)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(f'Пришлите новую дату окончания действия абонемента в формате дд.мм.гггг.\n\nТекущая дата окончани: {datetime.datetime.strftime(subscription.expiration_date, "%d.%m.%Y")}', reply_markup=builder.as_markup())


@router.message(EditUserSubscription.expiration_date)
async def new_expiration_date_recieved(message: Message, state: FSMContext):
    expiration_date = message.text
    try:
        expiration_date = datetime.datetime.strptime(message.text, '%d.%m.%Y').date()
    except ValueError:
        builder = InlineKeyboardBuilder()
        builder.button(text='❌ Отмена', callback_data='cancel_from_')
        await message.answer('Указанная дата не подходит под формат дд.мм.гггг (должна быть, например, 01.08.2023)\n\nПопробуйте ещё раз.', reply_markup=builder.as_markup())
        return
    await state.set_state()
    fsmdata = await state.get_data()
    subscription_id = fsmdata.get('subscription_id')
    edit_subscription = await db_requests.edit_validity_for_user_subscription(subscription_id, expiration_date)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Кабинет клиента', callback_data='user_profile') 
    
    if edit_subscription:
        await message.answer(f'✅ Дата окончания абонемента изменена на {datetime.datetime.strftime(expiration_date, "%d.%m.%Y")}.', reply_markup=builder.as_markup())
    else:
        await message.answer('❌ Ошибка изменения даты окончания абонемента.', reply_markup=builder.as_markup())


@router.callback_query(F.data == "admin_edit_user_subscription_session")
async def admin_edit_user_subscription_session(callback: CallbackQuery, state: FSMContext):
    fsmdata = await state.get_data()
    subscription = await db_requests.get_user_subscription(fsmdata.get('subscription_id'))
    await state.set_state(EditUserSubscription.number_of_sessions)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(f'Пришлите новое количество занятий для абонемента\n\nСейчас в абонементе {subscription.number_of_sessions} занятий.', reply_markup=builder.as_markup())


@router.message(EditUserSubscription.number_of_sessions)
async def new_number_of_sessions_recieved(message: Message, state: FSMContext):
    new_number_of_sessions = message.text
    if not new_number_of_sessions.isdigit():
        await message.answer('Пришлите количество занятий числом (6, 8, 12 и т.д.)')
        return
    await state.set_state()
    fsmdata = await state.get_data()
    subscription_id = fsmdata.get('subscription_id')
    edit_subscription = await db_requests.edit_numbers_of_sessions_for_user_subscription(subscription_id, new_number_of_sessions)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Кабинет клиента', callback_data='user_profile') 
    
    if edit_subscription:
        await message.answer(f'✅ Количество занятий в абонементе изменено на {new_number_of_sessions}.', reply_markup=builder.as_markup())
    else:
        await message.answer('❌ Ошибка изменения количества занятий.', reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("add_client_"))
async def add_client(callback: CallbackQuery, state: FSMContext):
    user_phonenumber = callback.data[11:]
    await state.update_data(user_phonenumber=user_phonenumber)
    await state.set_state(AddClient.user_name)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text('Пришлите Фамилию и Имя клиента', reply_markup=builder.as_markup())


@router.message(AddClient.user_name)
async def user_name_recieved(message: Message, state: FSMContext):
    user_name = message.text.split(' ')

    if len(user_name) != 2:
        await message.answer('Пришлите, пожалуйста, только фамилию и имя разделённые пробелом.')
        return
    
    await state.set_state()
    fsmdata = await state.get_data()
    user_phonenumber = fsmdata.get('user_phonenumber')
    create_new_user = await db_requests.add_new_client(user_phonenumber, user_name[1], user_name[0])
    if create_new_user:
        await message.answer('✅ Новый пользователь успешно создан!')
        await user_phonenumber_recieved(message, state, from_create=True)
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
        await message.answer('❌ Ошибка создания пользователя', reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin_add_client_sub"))
async def admin_add_client_sub_(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddSubscriptionByAdmin.start_date)
    builder = InlineKeyboardBuilder()
    builder.button(text='Сегодня', callback_data='select_start_subscription_date_today')
    builder.button(text='Завтра', callback_data='select_start_subscription_date_tomorrow')
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    builder.adjust(1)
    await callback.message.edit_text('Пришлите дату начала действия абонемента в формате дд.мм.гггг', reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("select_start_subscription_date_"))
@router.message(StateFilter(AddSubscriptionByAdmin.start_date))
async def start_date_recieved(message: Message, state: FSMContext):
    try:
        day = message.data[31:]
        if day == 'today':
            start_subscription_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).date()
        elif day == 'tomorrow':
            start_subscription_date = (datetime.datetime.utcnow() + datetime.timedelta(days=1, hours=7)).date()
        from_callback = True
        await message.message.edit_reply_markup(answer_reply_markup='')
    except:
        try:
            start_subscription_date = datetime.datetime.strptime(message.text, '%d.%m.%Y').date()
            from_callback = False
        except ValueError:
            builder = InlineKeyboardBuilder()
            builder.button(text='❌ Отмена', callback_data='cancel_from_')
            await message.answer('Указанная дата не подходит под формат дд.мм.гггг (должна быть, например, 01.08.2023)\n\nПопробуйте ещё раз.', reply_markup=builder.as_markup())
            return
    
    end_subscription_date = start_subscription_date + datetime.timedelta(days=30)
    fsmdata = await state.get_data()
    user = fsmdata.get('user')
    user_subscriptions = await db_requests.get_all_actual_user_subscriptions(user_phone=user.phone_number)

    if user_subscriptions:
        for user_subscription in user_subscriptions:
            if check_sub_for_intersections(start_subscription_date, end_subscription_date, user_subscription.purchase_date, user_subscription.expiration_date):
                builder = InlineKeyboardBuilder()
                builder.button(text='❌ Отмена', callback_data='cancel_from_')
                message_text = ('Начало действия абонемента в эту дату создаст пересечение с другим абонементом клиента:\n\n'
                                f'Начало действующего абонемента: {datetime.datetime.strftime(user_subscription.purchase_date, "%d.%m.%Y")}\n'
                                f'Конец действующего абонемента: {datetime.datetime.strftime(user_subscription.expiration_date, "%d.%m.%Y")}\n\n'
                                'Выберите дату начала, которая не будет создавать пересечения.')
                if from_callback:
                    await message.message.answer(message_text, reply_markup=builder.as_markup())
                else:
                    await message.answer(message_text, reply_markup=builder.as_markup())
                return
    await state.update_data(start_subscription_date=start_subscription_date)
    builder = InlineKeyboardBuilder()
    available_subscriptions = await db_requests.get_all_subscriptions_options()
    for subscription in available_subscriptions:
        builder.button(text=f'{subscription.number_of_sessions} за {subscription.price}', callback_data=f'admin_add_user_subscription_{subscription.id}')
    builder.adjust(1)
    
    if from_callback:
        await message.message.answer('Выберите вариант абонемента', reply_markup=builder.as_markup())
    else:
        await message.answer('Выберите вариант абонемента', reply_markup=builder.as_markup())
    await state.set_state()


@router.callback_query(F.data.startswith("admin_add_user_subscription_"))
async def admin_add_user_subscription(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(answer_reply_markup='')
    subscription_option_id = callback.data[28:]
    fsmdata = await state.get_data()
    user = fsmdata.get('user')
    start_subscription_date = fsmdata.get('start_subscription_date')
    builder = InlineKeyboardBuilder()

    add_user_subscription = await db_requests.add_new_subscription_for_user(user.user_telegram_id, subscription_option_id, start_subscription_date, user_phone=user.phone_number)
    if add_user_subscription:
        await callback.message.answer('✅ Абонемент успешно добавлен пользователю.')
        await state.update_data(user_phonenumber=user.phone_number)
        await user_phonenumber_recieved(callback.message, state, from_create=True)
    else:
        builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
        await callback.message.answer('❌ Ошибка добавления абонемента.', reply_markup=builder.as_markup())
    

@router.callback_query(F.data == 'admin_sign_up_lesson')
async def sign_up_lesson(callback: CallbackQuery, state: FSMContext):
    coaches = await db_requests.get_coaches()
    
    if coaches:
        message_text = 'Выберите преподавателя группового занятия.\n\n'
    else:
        message_text = 'К сожалению, на текущий момент нет доступных преподавателей.'

    builder = InlineKeyboardBuilder()
    for coach in coaches:
        builder.button(text=f'{coach.first_name} {coach.last_name}', callback_data=f'select_coach_for_admin_sign_up_{coach.id}')
    builder.button(text='🔙 Кабинет клиента', callback_data='user_profile')    
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('select_coach_for_admin_sign_up_'))
async def select_coach_for_sign_up(callback: CallbackQuery, state: FSMContext):
    coach = await db_requests.get_coach_by_id(callback.data[31:])
    await state.update_data(coach=coach)
    message_text = 'Выберите направление:\n\n'
    date_from = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    date_to = date_from + datetime.timedelta(weeks=12)
    available_directions = 0
    for i, direction in enumerate(coach.directions_of_teaching):
        if (direction.name in ['Индивидуальное', 'Индивидуальное парное'] or 
            len(await db_requests.get_trainings_by_coach(coach.id, date_from, date_to, direction.name)) == 0):
            continue
        message_text += f'🔹 {direction.name}\n'
        available_directions += 1

    if available_directions > 0:
        message_text += f'\nℹ️ {coach.first_name + " " + coach.last_name} ➔'
    else:
        message_text = '⛔️ Для данного тренера не установлено расписание.\nНет доступных направлений.'
    
    builder = InlineKeyboardBuilder()
    for direction in coach.directions_of_teaching:
        if (direction.name in ['Индивидуальное', 'Индивидуальное парное'] or 
            len(await db_requests.get_trainings_by_coach(coach.id, date_from, date_to, direction.name)) == 0):
            continue
        try:
            builder.button(text=f'{direction.name.split("(")[0]}', callback_data=f'select_direction_for_admin_sign_up_{direction.id}')     
        except:
            builder.button(text=f'{direction.name}', callback_data=f'select_direction_for_admin_sign_up_{direction.id}')
    builder.button(text='🔙 Выбор тренера', callback_data='admin_sign_up_lesson') 
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('select_direction_for_admin_sign_up_'))
async def select_direction_for_admin_sign_up(callback: CallbackQuery, state: FSMContext):
    direction = await db_requests.get_direction_by_id(callback.data[35:])
    await state.update_data(selected_direction=direction)
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    month_names = [
        "Январь", "Февраль", "Март", "Апрель",
        "Май", "Июнь", "Июль", "Август",
        "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]

    message_text = (f'Выберите месяц.\n\n'
                    f'ℹ️ {coach.first_name + " " + coach.last_name} ➔ {direction.name}')
    available_trainings = await db_requests.get_trainings_by_coach(coach.id, 
                                                                   datetime.datetime.utcnow() + datetime.timedelta(hours=7), 
                                                                   datetime.datetime.utcnow() + datetime.timedelta(days=100), 
                                                                   direction.name)
    available_months = set()
    for available_training in available_trainings:
        available_months.add(available_training.training_date.month)

    builder = InlineKeyboardBuilder()
    for available_month in available_months:
        year = datetime.datetime.utcnow().year if available_month >= datetime.datetime.utcnow().month else datetime.datetime.utcnow().year + 1
        builder.button(text=f'{month_names[available_month - 1]}', callback_data=f'select_month_for_admin_sign_up_{available_month}.{year}')
    builder.button(text='🔙 Выбор направления', callback_data=f'select_coach_for_admin_sign_up_{coach.id}') 
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('select_month_for_admin_sign_up_'))
async def select_month_for_admin_sign_up(callback: CallbackQuery, state: FSMContext):
    selected_date = callback.data[31:].split('.')
    selected_month = selected_date[0]
    selected_year = selected_date[1]
    await state.update_data(selected_month=selected_month, selected_year=selected_year)
    builder = InlineKeyboardBuilder()

    fsmdata = await state.get_data()
    selected_direction = fsmdata.get('selected_direction')
    coach = fsmdata.get('coach')
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    now = datetime.datetime.utcnow()
    if int(selected_month) > now.month:
        start_date = datetime.datetime(int(selected_year), int(selected_month), 1, 0, 0)
    else:
        start_date = now + datetime.timedelta(hours=7)

    message_text = (f'Выберите день.\n\n'
                    f'ℹ️ {coach.first_name + " " + coach.last_name} ➔ {selected_direction.name} ➔ xx.{selected_month}.{selected_year}')
    
    available_trainings = await db_requests.get_trainings_by_coach(coach.id, 
                                                                   start_date, 
                                                                   datetime.datetime(int(selected_year), int(selected_month), calendar.monthrange(int(selected_year), int(selected_month))[1], 23, 59), 
                                                                   selected_direction.name)
    

    # С помощью множества убираем дубли дат.
    available_days = set()
    for available_training in available_trainings:
        available_days.add(available_training.training_date.replace(hour=0, minute=0, second=0, microsecond=0))
    
    # Сортируем даты, для правильного вывода в меню по возрастанию
    sorted_available_days = sorted(available_days)

    for available_day in sorted_available_days:
        builder.button(text=f'{available_day.day}.{available_day.month}.{available_day.year} ({days[datetime.datetime(available_day.year, available_day.month, available_day.day).weekday()]})', callback_data=f'select_day_for_admin_sign_up_{available_day.day}')
    builder.button(text='🔙 Выбор месяца', callback_data=f'select_direction_for_admin_sign_up_{selected_direction.id}') 
    builder.adjust(1)
    
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('select_day_for_admin_sign_up_'))
async def select_day_for_admin_sign_up(callback: CallbackQuery, state: FSMContext):
    selected_day = callback.data[29:]
    await state.update_data(selected_day=selected_day)
    fsmdata = await state.get_data()
    selected_direction = fsmdata.get('selected_direction')
    selected_month = fsmdata.get('selected_month')
    selected_year = fsmdata.get('selected_year')
    coach = fsmdata.get('coach')
    user = fsmdata.get('user')

    message_text = (f'Выберите время.\n\n'
                    f'ℹ️ {coach.first_name + " " + coach.last_name} ➔ {selected_direction.name} ➔ {selected_day}.{selected_month}.{selected_year}')

    available_trainings = await db_requests.get_trainings_by_coach(coach.id, 
                                                                   datetime.datetime(2023, int(selected_month), int(selected_day)) + datetime.timedelta(hours=7),
                                                                   datetime.datetime(2023, int(selected_month), int(selected_day)) + datetime.timedelta(days=1, hours=7), 
                                                                   selected_direction.name)

    builder = InlineKeyboardBuilder()
    for available_training in available_trainings:
        user_enrollment = await db_requests.check_user_enrollment(callback.from_user.id, available_training.id, user_phone=user.phone_number)
        builder.button(text=f'{"✅ " if user_enrollment else ""}{datetime.datetime.strftime(available_training.training_date, "%H:%M")}', callback_data=f'select_training_for_admin_sign_up_{available_training.id}')
    builder.button(text='🔙 Выбор дня', callback_data=f'select_month_for_admin_sign_up_{selected_month}.{selected_year}') 
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('select_training_for_admin_sign_up_'))
async def select_day_for_sign_up_(callback: CallbackQuery, state: FSMContext):
    training_id = callback.data[34:]
    training = await db_requests.get_training_by_id(training_id)
    fsmdata = await state.get_data()
    selected_direction = fsmdata.get('selected_direction')
    selected_month = fsmdata.get('selected_month')
    selected_day = fsmdata.get('selected_day')
    selected_year = fsmdata.get('selected_year')
    coach = fsmdata.get('coach')
    user = fsmdata.get('user')
    
    user_subscriptions = await db_requests.get_all_actual_user_subscriptions(user_phone=user.phone_number)
    user_enrollment = await db_requests.check_user_enrollment(user_telegram_id=callback.from_user.id, user_phone=user.phone_number, training_id=training.id)
    if user_enrollment:
        if (training.training_date - (datetime.datetime.utcnow() + datetime.timedelta(hours=7))).total_seconds() / 3600 < 15:
            await callback.answer('Я отменю бронь, но до конца тренировки меньше 15 часов.', show_alert=True) 
        await db_requests.unenroll_training(user_phone=user.phone_number, training_id=training.id)
    else:
        training_date = datetime.date(int(selected_year), int(selected_month), int(selected_day))
        enrollment = False
        if user_subscriptions:
            for user_subscription in user_subscriptions:
                # Проверяем, попадает ли дата тренировки в даты действия любого из абонементов.
                if user_subscription.purchase_date <= training_date <= user_subscription.expiration_date:
                    user_enrollments_in_period = await db_requests.get_user_enrollments(user_phone=user.phone_number, date_from=user_subscription.purchase_date, date_to=user_subscription.expiration_date)
                    # Проверяем, достаточно ли занятий внутри абонемента для бронирования текущего занятия.
                    if len(user_enrollments_in_period) >= user_subscription.number_of_sessions:
                        await callback.answer('У клиента кончились занятия в абонементе. Но я всё равно его запишу, под вашу ответственность.', show_alert=True)
                    await db_requests.enrollment_on_training(user_phone=user.phone_number, training_id=training.id)
                    enrollment = True
                    break
        else:
            await callback.answer('У клиента нет абонемента. Но я всё равно его запишу, под вашу ответственность.', show_alert=True)
            await db_requests.enrollment_on_training(user_phone=user.phone_number, training_id=training.id)
            enrollment = True
        if enrollment == False:
            await db_requests.enrollment_on_training(user_phone=user.phone_number, training_id=training.id)
            await callback.answer('У клиента нет действующего абонемента на эту дату. Но я всё равно его запишу, под вашу ответственность.', show_alert=True)
            
    
    message_text = (f'Выберите время.\n\n'
                    f'ℹ️ {coach.first_name + " " + coach.last_name} ➔ {selected_direction.name} ➔ {selected_day}.{selected_month}.{selected_year}')
    
    available_trainings = await db_requests.get_trainings_by_coach(coach.id, 
                                                                   datetime.datetime(2023, int(selected_month), int(selected_day)) + datetime.timedelta(hours=7),
                                                                   datetime.datetime(2023, int(selected_month), int(selected_day)) + datetime.timedelta(days=1, hours=7), 
                                                                   selected_direction.name)

    builder = InlineKeyboardBuilder()
    for available_training in available_trainings:
        user_enrollment = await db_requests.check_user_enrollment(callback.from_user.id, available_training.id, user_phone=user.phone_number)
        builder.button(text=f'{"✅ " if user_enrollment else ""}{datetime.datetime.strftime(available_training.training_date, "%H:%M")}', callback_data=f'select_training_for_admin_sign_up_{available_training.id}')
    builder.button(text='🔙 Выбор дня', callback_data=f'select_month_for_admin_sign_up_{selected_month}.{selected_year}') 
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())