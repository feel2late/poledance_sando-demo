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
from states.add_subscription import AddSubscription
from states.change_other_settings import ChangeOtherSettings
from states.send_message_to_all_users import SendMessageToAllUsers
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from callback_factories.change_direction_status import ChangeDirectionStatus
from callback_factories.select_shedule_day import SelectScheduleDay
from bot_init import bot

router = Router()  



@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext, answer=False):
    await state.set_state()
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text='🔍 Поиск клиента', callback_data='search_client')
    builder.button(text='🕴 Преподаватели', callback_data='admin_teachers')
    builder.button(text='📊 Направления', callback_data='admin_directions')
    builder.button(text='🪪 Абонементы', callback_data='admin_subscriptions')
    builder.button(text='📨 Рассылка', callback_data='admin_send_message_to_all_users')
    builder.button(text='⚙️ Другие настройки', callback_data='admin_other_settings')
    builder.button(text='👥 Посмотреть пользователей', callback_data='view_users')
    builder.button(text='🔙 Меню', callback_data='menu')
    builder.adjust(1)
    if answer:
        await callback.message.answer('Вы в меню администратора.\nВыберите подходящий пункт меню.', reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text('Вы в меню администратора.\nВыберите подходящий пункт меню.', reply_markup=builder.as_markup())


@router.callback_query(F.data == "view_users")
async def view_users(callback: CallbackQuery, state: FSMContext):
    all_users = await db_requests.get_all_users()
    message_text = f'Количество зарегистрированных пользователей: {len(all_users)}\n\n'
    for user in all_users:
        message_text += f'{user.first_name + " " + user.last_name} - {user.phone_number}\n'
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Админ-меню', callback_data='admin_menu')

    MESS_MAX_LENGTH = 4096
    if len(message_text) < MESS_MAX_LENGTH:
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    else:
        for x in range(0, len(message_text), MESS_MAX_LENGTH):
                    mess = message_text[x: x + MESS_MAX_LENGTH]
                    await callback.message.answer(mess, reply_markup=builder.as_markup())
    


@router.callback_query(F.data == "admin_send_message_to_all_users")
async def admin_send_message_to_all_users(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SendMessageToAllUsers.text)
    message_text = 'Пришлите текст, который вы хотите разослать пользователям.'
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(SendMessageToAllUsers.text))
async def text_message_recieved(message: Message, state: FSMContext):
    await state.update_data(message_text=message.text)
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Отправить', callback_data='confirm_send_message_to_users')
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    builder.adjust(1)
    await message.answer('Проверьте текст.\n\nЕсли всё верно, нажмите "✅ Отправить"\nЕсли передумали, нажмите "❌ Отмена"\nЕсли хотите что-то исправить, просто пришлите мне новый вариант')
    await message.answer(message.text, reply_markup=builder.as_markup())


@router.callback_query(F.data == 'confirm_send_message_to_users', StateFilter(SendMessageToAllUsers.text))
async def confirm_send_message_to_users(callback: CallbackQuery, state: FSMContext):
    await state.set_state()
    await callback.message.delete()
    fsmdata = await state.get_data()
    message_text = fsmdata.get('message_text')
    users = await db_requests.get_all_users()
    users_count = 0
    for user in users:
        try:
            await bot.send_message(user.user_telegram_id, message_text)
            users_count += 1
        except:
            pass
    await callback.message.answer(f'{users_count} клиентов получили сообщение.\n\n*Сообщение получили только те клиенты, которые не заблокировали бота.')


@router.callback_query(F.data == "admin_subscriptions")
async def admin_subscriptions(callback: CallbackQuery, answer=False):
    subscriptions_options = await db_requests.get_all_subscriptions_options()
    if subscriptions_options:
        message_text = f'Для клиентов доступны следующие варианты абонементов:\n'
        for i, subsctiption_option in enumerate(subscriptions_options):
            message_text += f'{i+1}) {subsctiption_option.number_of_sessions} занятий за {subsctiption_option.price} руб.\n'
    else:
        message_text = 'В БД нет внесённых вариантов абонементов.'
    builder = InlineKeyboardBuilder()
    builder.button(text='➕ Добавить абонемент', callback_data='add_subscription')
    builder.button(text='❌ Удалить абонемент', callback_data='delete_subscription')
    builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
    builder.adjust(1)

    if answer:
        try:
            await callback.message.answer(message_text, reply_markup=builder.as_markup())
        except:
            await callback.answer(message_text, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    

@router.callback_query(F.data == "add_subscription")
async def add_subscription_option(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddSubscription.number_of_sessions)
    message_text = 'Пришлите количество занятий в абонементе.'
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(AddSubscription.number_of_sessions))
async def number_of_sessions_recieved(message: Message, state: FSMContext):
    number_of_sessions = message.text
    if not number_of_sessions.isdigit():
        await message.answer('Пришлите количество занятий числом (6, 8, 12 и т.д.)')
        return
    await state.update_data(number_of_sessions=number_of_sessions)
    await state.set_state(AddSubscription.subscription_cost)
    message_text = 'Пришлите стоимость абонемента.'
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await message.answer(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(AddSubscription.subscription_cost))
async def subscription_cost_recieved(message: Message, state: FSMContext):
    subscription_cost = message.text
    if not subscription_cost.isnumeric():
        await message.answer('Пришлите стоимость абонемента числом (1500, 1800 и т.д.)')
        return
    fsmdata = await state.get_data()
    number_of_sessions = fsmdata.get('number_of_sessions')

    add_subscription_option = await db_requests.add_subscriptions_options(number_of_sessions, subscription_cost)
    
    if add_subscription_option:
        await message.answer('Новый абонемент успешно добавлен', show_alert=True)
        await admin_subscriptions(message, answer=True)
    else:
        await message.answer('Ошибка добавления абонемента: такой абонемент уже существует.', show_alert=True)
        await admin_subscriptions(message, answer=True)
    

@router.callback_query(F.data == "admin_teachers")
async def admin_teachers(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    coaches = await db_requests.get_coaches()
    if coaches:
        message_text = 'Для клиентов доступны следующие тренеры:\n\n'
        for coach in coaches:
            message_text += (f'<b>Имя:</b> {coach.first_name} {coach.last_name}\n'
                             f'<b>Направления:</b> '
                             f'{", ".join(direction.name for direction in coach.directions_of_teaching) if len(coach.directions_of_teaching) > 0 else "Для тренера не установлены направления!"}\n'
                             f'<b>Стоимость индивидуального занятия:</b> {coach.individual_lesson_price}\n'
                             f'<b>Стоимость индивидуального парного занятия:</b> {coach.for_two_lesson_price}\n'
                             '-----------\n')
        message_text += '\n\n✏️ Выберите тренера для редактирования.'
    else:
        message_text = 'Для клиентов нет доступных тренеров. Вы можете добавить их нажав "Добавить тренера"'
    
    builder = InlineKeyboardBuilder()
    for coach in coaches:
        builder.button(text=f'{coach.first_name} {coach.last_name}', callback_data=f'edit_coach_{coach.id}')
    builder.button(text='➕ Добавить тренера', callback_data='add_coach')
    builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "add_coach")
async def add_coach(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCoach.coach_phonenumber)
    message_text = 'Пришлите номер телефона тренера.\n❗️ Тренер должен быть зарегистрирован в боте под этим номером.'
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(AddCoach.coach_phonenumber))
async def phonenumber_recieved(message: Message, state: FSMContext):
    coach_phonenumber = message.text.replace(' ', '')

    if coach_phonenumber.startswith('9'):
        coach_phonenumber = '7' + coach_phonenumber
    elif coach_phonenumber.startswith('8'):
        coach_phonenumber = '7' + coach_phonenumber[1:]
    elif coach_phonenumber.startswith('+'):
        coach_phonenumber = coach_phonenumber[1:]    
    

    if await db_requests.get_coach_by_phonenumber(coach_phonenumber):
        await message.answer('Тренер с таким номером телефона уже добавлен в список тренеров и доступен для клиентов!')
        await state.clear()
        return
    
    coach = await db_requests.get_user_by_phonenumber(coach_phonenumber)
    if coach:
        await state.clear()
        add_coach = await db_requests.add_coach(coach.phone_number, coach.first_name, coach.last_name, coach.user_telegram_id)
        builder = InlineKeyboardBuilder()
        builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
        if add_coach:
            await message.answer('Тренер успешно добавлен.', reply_markup=builder.as_markup())
        else:
            await message.answer('Ошибка добавления тренера.', reply_markup=builder.as_markup())
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text='❌ Отмена', callback_data='cancel_from_')
        await message.answer('Пользователь с таким номером телефона не найден в БД. Вы верно указали номер телефона?\n\n'
                             'Может быть тренер не зарегистрировался в боте как пользователь?', reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('edit_coach_'))
async def cancel_state(callback: CallbackQuery, state: FSMContext):
    coach_id = callback.data[11:]
    coach = await db_requests.get_coach_by_id(coach_id)
    await state.update_data(coach=coach)
    
    builder = InlineKeyboardBuilder()
    builder.button(text='💬 Имя', callback_data=f'edit_name_coach')
    builder.button(text='🗓 Расписание', callback_data=f'edit_schedule_coach')
    builder.button(text='🗓 История занятий', callback_data=f'lessons_history_coach')
    builder.button(text='📊 Направления', callback_data=f'edit_directions_coach')
    builder.button(text='ℹ️ Описание', callback_data=f'edit_about_coach_{coach.id}')
    builder.button(text='⚜️ Стоим. инд. занятия', callback_data=f'edit_individual_cost_coach_{coach.id}')
    builder.button(text='👯‍♀️ Стоим. парн. занятия', callback_data=f'edit_cost_for_two_coach_{coach.id}')
    
    builder.button(text='🔙 Преподаватели', callback_data='admin_teachers')
    builder.adjust(1)
    await callback.message.edit_text(f'Вы выбрали тренера {coach.first_name} {coach.last_name}.\n\nЧто хотите изменить?', reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('edit_name_coach'))
async def cancel_state(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditCoach.coach_name)
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    
    await state.update_data(coach=coach)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(f'Текущее имя тренера: {coach.first_name} {coach.last_name}.\nПришлите новое имя в формате Имя Фамилия.', reply_markup=builder.as_markup())


@router.message(StateFilter(EditCoach.coach_name))
async def coach_name_recieved(message: Message, state: FSMContext):
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
    coach_first_name = message.text.split(' ')[0]
    
    try:
        coach_last_name = message.text.split(' ')[1]
    except IndexError:
        builder = InlineKeyboardBuilder()
        builder.button(text='❌ Отмена', callback_data='cancel_from_')
        await message.answer('Пожалуйста, укажите Имя и Фамилию в одном сообщении. Разделите Имя и Фамилию пробелом.\n\nНапример: Иван Петров.\n\nПопробуйте ещё раз.', reply_markup=builder.as_markup())
        return
    
    coach_fullname = coach_first_name + ' ' + coach_last_name
    edit_coach = await db_requests.edit_coach_by_id(coach.id, 'name', coach_fullname)

    if edit_coach:
        await message.answer(f'Имя тренера успешно изменено на {coach_fullname}', reply_markup=builder.as_markup())
    else:
        await message.answer(f'Ошибка изменения имени тренера.', reply_markup=builder.as_markup())
    await state.clear()


@router.callback_query(F.data == "admin_directions")
async def admin_directions(callback: CallbackQuery, answer=False):
    directions = await db_requests.get_all_directions()
    if directions:
        message_text = f'Вы можете установить следующие направления для тренеров:\n'
        for i, direction in enumerate(directions):
            message_text += f'{i+1}) {direction.name} (max {direction.maximum_students} учеников)\n'
    else:
        message_text = 'В БД нет внесённых направлений.'
    builder = InlineKeyboardBuilder()
    builder.button(text='➕ Добавить направление', callback_data='add_direction')
    builder.button(text='❌ Удалить направление', callback_data='delete_direction')
    builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
    builder.adjust(1)
    if answer:
        await callback.answer(message_text, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "delete_subscription")
async def delete_subscription(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    subscriptions_options = await db_requests.get_all_subscriptions_options()
    for subscription_option in subscriptions_options:
        builder.button(text=f'{subscription_option.number_of_sessions} / {subscription_option.price}', callback_data=f'confirm_delete_subscription_{subscription_option.id}')
    builder.button(text='🔙 Абонементы', callback_data='admin_subscriptions')
    builder.adjust(1)
    message_text = 'Выберите абонемент для удаления.'
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("confirm_delete_subscription_"))
async def confirm_delete_subscription(callback: CallbackQuery, state: FSMContext):
    subscription_id = callback.data[28:]
    delete_subscription = await db_requests.delete_subscription(subscription_id)
    if delete_subscription:
        await callback.message.answer('✅ Абонемент успешно удалён.')
    else:
        await callback.message.answer('❌ Ошибка удаления абонемента.')
    await admin_subscriptions(callback, answer=True)


@router.callback_query(F.data == "delete_direction")
async def delete_direction(callback: CallbackQuery, state: FSMContext, answer=False):
    builder = InlineKeyboardBuilder()
    directions = await db_requests.get_all_directions()
    if directions:
        message_text = f'⚠️ Выберите направление для удаления\n\n❗️ <b>ПРЕЖДЕ ЧЕМ УДАЛИТЬ НАПРАВЛЕНИЕ, УБЕДИТЕСЬ, ЧТО ПО ЭТОМУ НАПРАВЛЕНИЮ НЕТ ЗАПЛАНИРОВАННЫХ ТРЕНИРОВОК!</b>'
    else:
        message_text = 'В БД нет внесённых направлений.'
    for direction in directions:
        builder.button(text=f'{direction.name}', callback_data=f'confirm_delete_direction_{direction.id}')
    builder.button(text='🔙 Направления', callback_data='admin_directions')
    builder.adjust(1)
    if answer:
        await callback.message.answer(message_text, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("confirm_delete_direction_"))
async def confirm_delete_direction(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    direction_id = callback.data[25:]
    direction = await db_requests.get_direction_by_id(direction_id)
    if direction.name in ['Индивидуальное', 'Индивидуальное парное']:
        await callback.message.answer(f'❌ Направление {direction.name} нельзя удалить!')
        await delete_direction(callback, state, answer=True)
        return
    delete_direction_status = await db_requests.delete_direction(direction_id)

    if delete_direction_status:
        await callback.message.answer(f'✅ Направление "{direction.name}" удалено.')
    else:
        await callback.message.answer(f'❌ Ошибка удаления направления "{direction.name}"!')

    await delete_direction(callback, state, answer=True)


@router.callback_query(F.data == "add_direction")
async def add_direction(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddDirection.direction_name)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    bot_message = await callback.message.edit_text('Введите название нового направления.', reply_markup=builder.as_markup())
    await state.update_data(bot_message=bot_message)


@router.message(StateFilter(AddDirection.direction_name))
async def direction_name_recieved(message: Message, state: FSMContext):
    direction_name = message.text
    fsmdata = await state.get_data()
    bot_message = fsmdata.get('bot_message')
    await bot_message.edit_reply_markup(answer_markup='')

    if not await db_requests.get_direction_by_name(direction_name):
        await state.set_state(AddDirection.max_students)    
        builder = InlineKeyboardBuilder()
        builder.button(text='❌ Отмена', callback_data='cancel_from_')
        bot_message = await message.answer('Пришлите максимальное количество учеников на тренировке по данному направлению.', reply_markup=builder.as_markup())
        await state.update_data(direction_name=direction_name, bot_message=bot_message)
        
    else:
        await message.answer('❌ Такое направление уже существует в БД')
        await state.clear()
        await admin_directions(message, answer=True)


@router.message(StateFilter(AddDirection.max_students))
async def max_students_recieved(message: Message, state: FSMContext):
    fsmdata = await state.get_data()
    bot_message = fsmdata.get('bot_message')
    direction_name = fsmdata.get('direction_name')
    
    if message.text.isdigit():
        max_students = message.text
    await bot_message.edit_reply_markup(answer_markup='')
    
    add_direction = await db_requests.add_direction(direction_name, max_students)
    if add_direction:
        await message.answer('✅ Новое направление добавлено')
    else:
        await message.answer('❌ Ошибка добавления направления')
    
    await state.clear()
    await admin_directions(message, answer=True)


@router.callback_query(F.data.startswith('edit_directions_coach'))
async def edit_directions_coach(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    directions = await db_requests.get_all_directions()
    builder = InlineKeyboardBuilder()
    directions_of_teaching_name = [direction.name for direction in coach.directions_of_teaching]
    
    for direction in directions:
        if direction.name in directions_of_teaching_name:
            builder.button(text=f'✅ {direction.name}', callback_data=ChangeDirectionStatus(coach_id=coach.id, status='deactivate', direction_id=direction.id))
        else:
            builder.button(text=f'{direction.name}', callback_data=ChangeDirectionStatus(coach_id=coach.id, status='activate', direction_id=direction.id))
    builder.button(text=f'🔙 {coach.first_name} {coach.last_name}', callback_data=f'edit_coach_{coach.id}')
    builder.adjust(1)

    await callback.message.edit_text('Включите или отключите доступные тренеру направления.\n\n✅ - значит направление для тренера включено.', reply_markup=builder.as_markup())


@router.callback_query(ChangeDirectionStatus.filter())
async def change_direction_status(callback: CallbackQuery, callback_data: ChangeDirectionStatus, state: FSMContext):
    coach_id = callback_data.coach_id
    direction_status = callback_data.status
    direction_id = callback_data.direction_id
    await db_requests.change_direction_status_for_coach(coach_id, direction_id, True if direction_status == 'activate' else False)
    builder = InlineKeyboardBuilder()

    coach = await db_requests.get_coach_by_id(coach_id)
    directions = await db_requests.get_all_directions()

    directions_of_teaching_name = [direction.name for direction in coach.directions_of_teaching]
    
    for direction in directions:
        if direction.name in directions_of_teaching_name:
            builder.button(text=f'✅ {direction.name}', callback_data=ChangeDirectionStatus(coach_id=coach_id, status='deactivate', direction_id=direction.id))
        else:
            builder.button(text=f'{direction.name}', callback_data=ChangeDirectionStatus(coach_id=coach_id, status='activate', direction_id=direction.id))
    builder.button(text=f'🔙 {coach.first_name} {coach.last_name}', callback_data=f'edit_coach_{coach.id}')
    builder.adjust(1)
        
    await callback.message.edit_text('Включите или отключите доступные тренеру направления.\n\n✅ - значит направление для тренера включено.', reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('lessons_history_coach'))
async def edit_schedule_coach(callback: CallbackQuery, state: FSMContext):
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')

    coach_trainings = await db_requests.get_trainings_by_coach(coach.id, datetime.datetime.utcnow() - datetime.timedelta(days=60, hours=7), datetime.datetime.utcnow() + datetime.timedelta(hours=7))
    if coach_trainings:
        message_text = f'История тренировок для {coach.first_name} {coach.last_name} за 60 дней.\n\n'
        for training in coach_trainings:
            number_of_students = len(await db_requests.get_training_enrollments(training.id))
            message_text += f'{datetime.datetime.strftime(training.training_date, "%d.%m.%Y %H:%M")} - {training.direction_of_training}. Учеников - {number_of_students}\n'
    else:
        message_text = f'Для {coach.first_name} {coach.last_name} нет истории тренировок.\n\n'
    builder = InlineKeyboardBuilder()
    builder.button(text=f'🔙 Назад', callback_data=f'edit_coach_{coach.id}')
    builder.adjust(1)
    MESS_MAX_LENGTH = 4096
    if len(message_text) < MESS_MAX_LENGTH:
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    else:
        for x in range(0, len(message_text), MESS_MAX_LENGTH):
                    mess = message_text[x: x + MESS_MAX_LENGTH]
                    await callback.message.answer(mess)


@router.callback_query(F.data.startswith('edit_schedule_coach'))
async def edit_schedule_coach(callback: CallbackQuery, state: FSMContext):
    current_date = datetime.datetime.utcnow()
    month_number = current_date.month
    next_month_number = (current_date + datetime.timedelta(weeks=4)).month
    after_two_month_number = (current_date + datetime.timedelta(days=60)).month
    month_names = [
        "Январь", "Февраль", "Март", "Апрель",
        "Май", "Июнь", "Июль", "Август",
        "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
    current_month_name = month_names[month_number - 1]
    next_month_name = month_names[next_month_number - 1]
    after_two_month_name = month_names[after_two_month_number - 1]
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')

    coach_trainings = await db_requests.get_trainings_by_coach(coach.id, datetime.datetime.utcnow() + datetime.timedelta(hours=7), datetime.datetime.utcnow() + datetime.timedelta(days=100))
    if coach_trainings:
        message_text = f'Запланированные тренировки для {coach.first_name} {coach.last_name}\n\n'
        for training in coach_trainings:
            number_of_students = len(await db_requests.get_training_enrollments(training.id))
            message_text += f'{datetime.datetime.strftime(training.training_date, "%d.%m.%y %H:%M")} - {training.direction_of_training}. ({number_of_students})\n'
    else:
        message_text = f'Для {coach.first_name} {coach.last_name} нет запланированных тренировок. Создайте их!\n\n'
    builder = InlineKeyboardBuilder()
    builder.button(text=f'{current_month_name}', callback_data=f'set_shchedule_month_{month_number}')
    builder.button(text=f'{next_month_name}', callback_data=f'set_shchedule_month_{next_month_number}')
    builder.button(text=f'{after_two_month_name}', callback_data=f'set_shchedule_month_{after_two_month_number}')
    builder.button(text=f'🔙 Назад', callback_data=f'edit_coach_{coach.id}')
    builder.adjust(1)
    MESS_MAX_LENGTH = 4096
    if len(message_text) < MESS_MAX_LENGTH:
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    else:
        for x in range(0, len(message_text), MESS_MAX_LENGTH):
                    mess = message_text[x: x + MESS_MAX_LENGTH]
                    await callback.message.answer(mess)


@router.callback_query(F.data.startswith('set_shchedule_month_'))
async def set_shchedule_month(callback: CallbackQuery, state: FSMContext):
    month_number = int(callback.data[20:])
    current_date = datetime.datetime.utcnow()
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    builder = InlineKeyboardBuilder()
    for i in range(1, calendar.monthrange(current_date.year, month_number)[1] + 1):
        local_now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        year = datetime.datetime.utcnow().year if month_number >= datetime.datetime.utcnow().month else datetime.datetime.utcnow().year + 1
        available_trainings = await db_requests.get_all_available_trainings(date_from=datetime.datetime(year, month_number, i, 00, 00), date_to=datetime.datetime(year, month_number, i, 23, 59))
        if i < local_now.day and local_now.month == month_number:
            continue
        builder.button(text=f'{"✅ " if available_trainings else ""}{i}.{month_number} ({days[datetime.datetime(current_date.year, month_number, i).weekday()]})', callback_data=f'set_schedule_day_{i}.{month_number}.{current_date.year}')

    builder.button(text=f'🔙 Назад', callback_data='edit_schedule_coach')
    builder.adjust(3)
    await callback.message.edit_text('Выберите день для планирования расписания', reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('set_schedule_day_'))
async def set_shchedule_month(callback: CallbackQuery, state: FSMContext):
    select_date = callback.data[17:].split('.')
    select_day, select_month, select_year = int(select_date[0]), int(select_date[1]), int(select_date[2])
    await state.update_data(select_day=select_day, select_month=select_month, select_year=select_year)
    
    builder = InlineKeyboardBuilder()
    for i in range(10, 22):
        available_trainings = await db_requests.get_all_available_trainings(date_from=datetime.datetime(select_year, select_month, select_day, i, 00), date_to=datetime.datetime(select_year, select_month, select_day, i, 00))
        builder.button(text=f'{"✅ " if available_trainings else ""}{i}:00', callback_data=f'set_schedule_direction_{i}')
    builder.button(text=f'🔙 Назад', callback_data=f'set_shchedule_month_{select_month}')
    builder.adjust(3)
    await callback.message.edit_text('Выберите время для планирования расписания.', reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('set_schedule_direction_'))
async def set_shchedule_month(callback: CallbackQuery, state: FSMContext):
    select_hour = callback.data[23:]
    await state.update_data(select_hour=select_hour)
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    training_date = datetime.datetime(int(fsmdata.get("select_year")), int(fsmdata.get("select_month")), int(fsmdata.get("select_day")), int(select_hour), 0)
    directions_list = coach.directions_of_teaching
    
    builder = InlineKeyboardBuilder()
    for direction in directions_list:
        training = await db_requests.get_training(coach.id, direction.id, training_date)
        builder.button(text=f'{"✅ " if training else ""}{direction.name}', callback_data=f'set_schedule_training_{direction.id}')
    builder.button(text=f'🔙 Назад', callback_data=f'set_schedule_day_{fsmdata.get("select_day")}.{fsmdata.get("select_month")}.{fsmdata.get("select_year")}')
    builder.adjust(1)

    await callback.message.edit_text('Выберите направление для тренировки', reply_markup=builder.as_markup())
    
    
@router.callback_query(F.data.startswith('set_schedule_training_'))
async def set_shchedule_month(callback: CallbackQuery, state: FSMContext):
    direction_id = callback.data[22:]
    direction = await db_requests.get_direction_by_id(direction_id)
    fsmdata = await state.get_data()
    select_day, select_month, select_year, select_hour = fsmdata.get('select_day'), fsmdata.get('select_month'), fsmdata.get('select_year'), fsmdata.get('select_hour')
    coach = fsmdata.get('coach')
    training_date = datetime.datetime(int(select_year), int(select_month), int(select_day), int(select_hour), 0)
    builder = InlineKeyboardBuilder()
    training = await db_requests.get_training(coach.id, direction.id, training_date)
    
    if training:
        user_enrollments = await db_requests.get_training_enrollments(training.id)
        for user_enrollment in user_enrollments:
            client = await db_requests.get_user_by_id(user_enrollment.user_id)
            delete_enrollment = await db_requests.unenroll_training(client.user_telegram_id, training.id)
            message_text = ('⚠️ Ваша тренировка:\n'
                            f'{datetime.datetime.strftime(training.training_date, "%d.%m.%Y %H:%M")} - {training.direction_of_training} у тренера {training.trainer.first_name} {training.trainer.last_name}\n'
                            '<b>Отменена администратором.</b>')
            try:
                await bot.send_message(client.user_telegram_id, message_text)
            except:
                print(traceback.format_exc())

        delete_training = await db_requests.delete_training(coach.id, direction_id, training_date)
        
    else:
        add_training = await db_requests.add_training(coach.id, direction_id, training_date)
    
    directions_list = coach.directions_of_teaching
    
    builder = InlineKeyboardBuilder()
    for direction in directions_list:
        training = await db_requests.get_training(coach.id, direction.id, training_date)
        builder.button(text=f'{"✅ " if training else ""}{direction.name}', callback_data=f'set_schedule_training_{direction.id}')
    builder.button(text=f'🔙 Назад', callback_data=f'set_schedule_day_{fsmdata.get("select_day")}.{fsmdata.get("select_month")}.{fsmdata.get("select_year")}')
    builder.adjust(1)

    await callback.message.edit_text('Выберите направление для тренировки', reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('edit_individual_cost_coach_'))
async def edit_individual_cost_coach(callback: CallbackQuery, state: FSMContext):
    coach_id = callback.data[27:]  
    coach = await db_requests.get_coach_by_id(coach_id)
    await state.update_data(coach=coach)
    await state.set_state(EditCoach.edit_coach_individual_cost)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(f'Пришлите новую стоимость индивидуального занятия для тренера.\nТекущая: {coach.individual_lesson_price} р.', reply_markup=builder.as_markup())


@router.message(StateFilter(EditCoach.edit_coach_individual_cost))
async def coach_individual_cost_recieved(message: Message, state: FSMContext):
    if message.text.isnumeric():
        new_cost = message.text
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text='❌ Отмена', callback_data='cancel_from_')
        await message.answer('Пришлите число', reply_markup=builder.as_markup())
        return
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    edit_coach_status = await db_requests.edit_coach_by_id(coach.id, 'individual_lesson_price', new_cost)
    builder = InlineKeyboardBuilder()
    builder.button(text=f'🔙 {coach.first_name + " " + coach.last_name}', callback_data=f'edit_coach_{coach.id}')
    if edit_coach_status:
        await message.answer(f'✅ Стоимость индивидуального занятия у тренера {coach.first_name + " " + coach.last_name} успешно изменена на {new_cost}.', reply_markup=builder.as_markup())
    else:
        await message.answer(f'❌ Ошибка изменения стоимости для тренера.', reply_markup=builder.as_markup())
    await state.set_state()
        

@router.callback_query(F.data.startswith('edit_cost_for_two_coach_'))
async def edit_individual_cost_coach(callback: CallbackQuery, state: FSMContext):
    coach_id = callback.data[24:]  
    coach = await db_requests.get_coach_by_id(coach_id)
    await state.update_data(coach=coach)
    await state.set_state(EditCoach.edit_coach_cost_for_two)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(f'Пришлите новую стоимость индивидуального парного занятия для тренера.\nТекущая: {coach.for_two_lesson_price} р.', reply_markup=builder.as_markup())


@router.message(StateFilter(EditCoach.edit_coach_cost_for_two))
async def coach_individual_cost_recieved(message: Message, state: FSMContext):
    if message.text.isnumeric():
        new_cost = message.text
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text='❌ Отмена', callback_data='cancel_from_')
        await message.answer('Пришлите число', reply_markup=builder.as_markup())
        return
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    edit_coach_status = await db_requests.edit_coach_by_id(coach.id, 'for_two_lesson_price', new_cost)
    builder = InlineKeyboardBuilder()
    builder.button(text=f'🔙 {coach.first_name + " " + coach.last_name}', callback_data=f'edit_coach_{coach.id}')
    if edit_coach_status:
        await message.answer(f'✅ Стоимость индивидуального парного занятия у тренера {coach.first_name + " " + coach.last_name} успешно изменена на {new_cost}.', reply_markup=builder.as_markup())
    else:
        await message.answer(f'❌ Ошибка изменения стоимости для тренера.', reply_markup=builder.as_markup())
    await state.set_state()


@router.callback_query(F.data == "admin_other_settings")
async def add_subscription_option(callback: CallbackQuery, state: FSMContext):
    other_settings = await db_requests.get_other_settings()
    message_text = (f'Стоимость одного группового занятия: {other_settings.single_lesson_cost} р.\n\n'
                    f'Стоимость одного занятия при докупки в абонемент: {other_settings.add_session_to_subscribe} р.\n\n'
                    f'Стоимость пробного занятия: {other_settings.trial_lesson_cost} р.\n\n'
                    f'Скидка на продление абонемента: {other_settings.renewal_discount}%\n\n'
                    f'Стоимость аренды школы:\n1 час - {other_settings.one_hour_rent} р.\n2 часа - {other_settings.two_hour_rent} р.')
    builder = InlineKeyboardBuilder()
    builder.button(text='Стоимость одного группового занятия', callback_data='change_single_lesson_cost')
    builder.button(text='Стоимость докупки занятия', callback_data='change_add_one_lesson_in_subscribe_cost')
    builder.button(text='Стоимость пробного занятия', callback_data='change_cost_trial_lesson')
    builder.button(text='Скидка на продление', callback_data='change_discount')
    builder.button(text='Стоимость аренды школы', callback_data='change_rent_cost')
    builder.button(text='🔙 Админ-меню', callback_data='admin_menu')
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "change_add_one_lesson_in_subscribe_cost")
async def change_add_one_lesson_in_subscribe_cost(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChangeOtherSettings.add_session_to_subscribe)
    message_text = 'Пришлите новую стоимость занятия при добавлении его в абонемент.'
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(ChangeOtherSettings.add_session_to_subscribe))
async def new_cost_single_lesson_recieved(message: Message, state: FSMContext):
    new_cost = message.text
    if not new_cost.isdigit():
        await message.answer('Пришлите стоимость числом (250, 300, 500 и т.д.)')
        return
    await state.set_state()
    settings_changed = await db_requests.change_other_settings('add_session_to_subscribe', new_cost)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Другие настройки', callback_data='admin_other_settings')
    if settings_changed:
        await message.answer('✅ Стоимость успешно изменена', reply_markup=builder.as_markup())
    else:
        await message.answer('❌ Ошибка изменения стоимости', reply_markup=builder.as_markup())






@router.callback_query(F.data == "change_single_lesson_cost")
async def change_single_lesson_cost(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChangeOtherSettings.single_lesson_cost)
    message_text = 'Пришлите новую стоимость одного группового занятия.'
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(ChangeOtherSettings.single_lesson_cost))
async def new_cost_single_lesson_recieved(message: Message, state: FSMContext):
    new_cost = message.text
    if not new_cost.isdigit():
        await message.answer('Пришлите стоимость числом (250, 300, 500 и т.д.)')
        return
    await state.set_state()
    settings_changed = await db_requests.change_other_settings('single_lesson_cost', new_cost)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Другие настройки', callback_data='admin_other_settings')
    if settings_changed:
        await message.answer('✅ Стоимость успешно изменена', reply_markup=builder.as_markup())
    else:
        await message.answer('❌ Ошибка изменения стоимости', reply_markup=builder.as_markup())


@router.callback_query(F.data == "change_cost_trial_lesson")
async def add_subscription_option(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChangeOtherSettings.trial_lesson_cost)
    message_text = 'Пришлите новую стоимость пробного занятия.'
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(ChangeOtherSettings.trial_lesson_cost))
async def new_cost_trial_lesson_recieved(message: Message, state: FSMContext):
    new_cost = message.text
    if not new_cost.isdigit():
        await message.answer('Пришлите стоимость числом (250, 300, 500 и т.д.)')
        return
    await state.set_state()
    settings_changed = await db_requests.change_other_settings('trial_lesson_cost', new_cost)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Другие настройки', callback_data='admin_other_settings')
    if settings_changed:
        await message.answer('✅ Стоимость успешно изменена', reply_markup=builder.as_markup())
    else:
        await message.answer('❌ Ошибка изменения стоимости', reply_markup=builder.as_markup())


@router.callback_query(F.data == "change_discount")
async def add_subscription_option(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChangeOtherSettings.renewal_discount)
    message_text = 'Пришлите новый размер скидки на продление абонемента. Или пришлите 0 (ноль) если скидку за продление нужно отключить.'
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(ChangeOtherSettings.renewal_discount))
async def new_cost_trial_lesson_recieved(message: Message, state: FSMContext):
    new_cost = message.text
    if not new_cost.isdigit():
        await message.answer('Пришлите скидку в виде числа от 0 до 99')
        return
    if not 0 <= int(new_cost) <= 99:
        await message.answer('Скидка не может быть меньше 0 и больше 99')
        return
    await state.set_state()
    settings_changed = await db_requests.change_other_settings('renewal_discount', new_cost)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Другие настройки', callback_data='admin_other_settings')
    if settings_changed:
        await message.answer('✅ Скидка за продление абонемента успешно изменена.', reply_markup=builder.as_markup())
    else:
        await message.answer('❌ Ошибка изменения скидки.', reply_markup=builder.as_markup())


@router.callback_query(F.data == "change_rent_cost")
async def add_subscription_option(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChangeOtherSettings.one_hour_rent)
    message_text = 'Пришлите стоимость часа аренды школы'
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(ChangeOtherSettings.one_hour_rent))
async def new_cost_trial_lesson_recieved(message: Message, state: FSMContext):
    new_cost = message.text
    if not new_cost.isdigit():
        await message.answer('Новая стоимость должна быть числом.')
        return
    settings_changed = await db_requests.change_other_settings('one_hour_rent', new_cost)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Другие настройки', callback_data='admin_other_settings')
    if settings_changed:
        await state.set_state(ChangeOtherSettings.two_hour_rent)
        builder = InlineKeyboardBuilder()
        builder.button(text='❌ Отмена', callback_data='cancel_from_')
        await message.answer('✅ Стоимость 1 часа аренды школы изменена.\n\nТеперь пришлите стоимость двух часов аренды, или нажмите "Отмена", если не планируете её менять.', reply_markup=builder.as_markup())
    else:
        await state.set_state()
        await message.answer('❌ Ошибка изменения стоимости аренды школы.', reply_markup=builder.as_markup())


@router.message(StateFilter(ChangeOtherSettings.two_hour_rent))
async def new_cost_trial_lesson_recieved(message: Message, state: FSMContext):
    new_cost = message.text
    if not new_cost.isdigit():
        await message.answer('Новая стоимость должна быть числом.')
        return
    await state.set_state()
    settings_changed = await db_requests.change_other_settings('two_hour_rent', new_cost)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Другие настройки', callback_data='admin_other_settings')
    if settings_changed:
        await message.answer('✅ Стоимость 2-х часов аренды изменена.', reply_markup=builder.as_markup())
    else:
        await message.answer('❌ Ошибка изменения стоимости.', reply_markup=builder.as_markup())