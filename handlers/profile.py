import asyncio
import traceback
import uuid
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
import db_requests
import models
import datetime
from yookassa import Payment
from states.edit_subscription import UserEditSelfSubscription
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from bot_init import bot

router = Router()  



@router.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    client = await db_requests.get_user(callback.from_user.id)
    actual_subscription: models.Subscription = await db_requests.get_actual_subscription(callback.from_user.id)
    all_actual_subscriptions = models.Subscription = await db_requests.get_all_actual_user_subscriptions(callback.from_user.id)
    other_settings = await db_requests.get_other_settings()
    builder = InlineKeyboardBuilder()
    builder.button(text='📝 Записаться на занятие', callback_data='sign_up_lesson')
    builder.button(text='📆 Расписание ваших занятий', callback_data='my_lesson_schedule')
    if not actual_subscription:
        builder.button(text='👯‍♀️ Купить одно групповое занятие', callback_data='buy_one_group_lesson')
    builder.button(text='⚜️ Купить индивидуальное занятие', callback_data='buy_individual_lesson')
    #builder.button(text='👯‍♀️ Купить парное занятие', callback_data='buy_individual_dual_lesson')
    if actual_subscription:
        builder.button(text='➕ Докупить занятия в абонемент', callback_data='buy_additional_sessions')
        if other_settings.renewal_discount > 0:
            builder.button(text=f'💵 Продлить абонемент (-{other_settings.renewal_discount}%)', callback_data='renew_subscription')
        else:
            builder.button(text=f'💵 Продлить абонемент', callback_data='renew_subscription')
    else:
        builder.button(text='💵 Купить абонемент', callback_data='buy_subscription')
    builder.button(text='📔 История занятий', callback_data='history_of_lessons')
    builder.button(text='🔙 Меню', callback_data='menu')
    builder.adjust(1)
    
    if actual_subscription:
        message_text = (f'🪪 Абонемент действует до: {datetime.datetime.strftime(actual_subscription.expiration_date, "%d.%m.%Y")}\n'
                        f'Всего занятий по абонементу: {actual_subscription.number_of_sessions}\n'
                        f'Запланировано занятий по абонементу: {len(await db_requests.get_user_enrollments(user_telegram_id=callback.from_user.id, date_from=datetime.datetime.utcnow() + datetime.timedelta(hours=7), date_to=actual_subscription.expiration_date + datetime.timedelta(days=1), without_individual=True))}\n'
                        f'Использовано занятий по абонементу: {len(await db_requests.get_user_enrollments(user_telegram_id=callback.from_user.id, date_from=actual_subscription.purchase_date, date_to=datetime.datetime.utcnow() + datetime.timedelta(hours=7), without_individual=True))}\n')
        if len(all_actual_subscriptions) > 1:
            message_text += '\nТакже куплен(ы) абонемент(ы):\n'
            for i, actual_subscription in enumerate(all_actual_subscriptions[1:]):
                message_text += f'{i + 1}) {actual_subscription.number_of_sessions} занятий, с {datetime.datetime.strftime(actual_subscription.purchase_date, "%d.%m.%Y")} - {datetime.datetime.strftime(actual_subscription.expiration_date, "%d.%m.%Y")}\n'
    else:
        message_text = '⚠️ У вас нет действующего абонемента\n\nВы можете приобрести абонемент для групповых занятий или купить индивидуальное занятие с тренером.'

    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "buy_additional_sessions")
async def buy_additional_sessions(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_user_menu')
    message_text = 'Пришлите количество занятий, которое вы хотите докупить в текущий (действующий) абонемент.'
    await state.set_state(UserEditSelfSubscription.number_of_session_to_add)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.message(StateFilter(UserEditSelfSubscription.number_of_session_to_add))
async def additional_sessions_recieved(message: Message, state: FSMContext):
    number_of_session_to_add = message.text
    if not number_of_session_to_add.isnumeric():
        await message.answer('Пришлите количество занятий числом (1, 3, 5 и т.д.)')
        return
    builder = InlineKeyboardBuilder()
    await state.set_state()
    other_settings = await db_requests.get_other_settings()
    payment = Payment.create({
        "amount": {
            "value": f"{int(other_settings.add_session_to_subscribe*int(number_of_session_to_add))}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/Poledance_sando_bot"
        },
        "capture": True,
        "description": f"Добавление {number_of_session_to_add} занятий в абонемент."
        }, uuid.uuid4())
    
    builder = InlineKeyboardBuilder()
    builder.button(text='Оплатить', url=payment.confirmation.confirmation_url)
    builder.button(text='🔙 Назад в профиль', callback_data='profile')
    builder.adjust(1)
    message_text = (f'Вы выбрали добавление {number_of_session_to_add} занятий в абонемент за {other_settings.add_session_to_subscribe*int(number_of_session_to_add)} рублей.\n\n'
                    'Пожалуйста, оплатите в течении одного часа.')
    message_pay = await message.answer(message_text, reply_markup=builder.as_markup())

    for i in range(180):
        payment_status = Payment.find_one(payment.id)
        if payment_status.status == 'succeeded':
            actual_subscription: models.Subscription = await db_requests.get_actual_subscription(message.from_user.id)
            await db_requests.edit_numbers_of_sessions_for_user_subscription(actual_subscription.id, int(number_of_session_to_add) + actual_subscription.number_of_sessions)
            await message_pay.edit_reply_markup(answer_markup='')
            builder = InlineKeyboardBuilder()
            builder.button(text='🔙 Назад в профиль', callback_data='profile')
            await message.answer(f'😌 Спасибо, оплата получена. {number_of_session_to_add} занятий добавлено в ваш текущий абонемент.', reply_markup=builder.as_markup()) 
            return
        elif payment_status.status == 'canceled':
            break
        else:
            await asyncio.sleep(20)

    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Назад в профиль', callback_data='profile')
    try:
        await message.answer('🤷‍♂️ Время на оплату вышло или платёж завершился с ошибкой.', reply_markup=builder.as_markup())
    except:
        '''Ничего не нужно делать, потому что пользователь уже сам вышел из меню оплаты и ему будет недоступна старая кнопка для оплаты. 
        При входе заново он сгенерирует новый счёт'''
        pass

@router.callback_query(F.data == "buy_subscription")
async def buy_subscription_menu(callback: CallbackQuery):
    subscriptions_options = await db_requests.get_all_subscriptions_options()
    builder = InlineKeyboardBuilder()
    message_text = '❗️<b>ВНИМАНИЕ!</b> абонемент действует 30 дней с момента покупки.\n\nДоступны следующие варианты абонементов:\n\n'
    for i, subscription_option in enumerate(subscriptions_options):
        builder.button(text=f'{subscription_option.number_of_sessions} за {subscription_option.price}', callback_data=f'order_subscription_{subscription_option.id}')
        message_text += f'{i+1}) {subscription_option.number_of_sessions} занятий за {subscription_option.price} рублей ({subscription_option.price // subscription_option.number_of_sessions} руб. за занятие)\n'
    builder.button(text='🔙 Личный кабинет', callback_data='profile')
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "renew_subscription")
async def buy_subscription_menu(callback: CallbackQuery):
    subscriptions_options = await db_requests.get_all_subscriptions_options()
    other_settings = await db_requests.get_other_settings()
    renewal_discount = other_settings.renewal_discount / 100
    builder = InlineKeyboardBuilder()
    if other_settings.renewal_discount > 0:
        message_text = ('❗️<b>ВНИМАНИЕ!</b> Новый абонемент действует <b>30 дней</b> с момента окончания действия предыдущего абонемента.\n\n'
                        f'🎁 Скидка {other_settings.renewal_discount}% на абонемент при продлении!\n\n'
                        'Доступны следующие варианты абонементов:\n\n')
    else:
        message_text = ('❗️<b>ВНИМАНИЕ!</b> Новый абонемент действует <b>30 дней</b> с момента окончания действия предыдущего абонемента.\n\n'          
                        'Доступны следующие варианты абонементов:\n\n')
        
    for i, subscription_option in enumerate(subscriptions_options):
        builder.button(text=f'{subscription_option.number_of_sessions} за {int(subscription_option.price-subscription_option.price*renewal_discount)}', callback_data=f'order_renew_subscription_{subscription_option.id}')
        message_text += f'{i+1}) {subscription_option.number_of_sessions} занятий за {f"<s>{subscription_option.price}</s> " if renewal_discount > 0 else ""}<b>{int(subscription_option.price-subscription_option.price*renewal_discount)}</b> рублей ({int(subscription_option.price-subscription_option.price*renewal_discount) // subscription_option.number_of_sessions} руб. за занятие)\n'
    builder.button(text='🔙 Личный кабинет', callback_data='profile')
    builder.adjust(1)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('order_renew_subscription_'))
@router.callback_query(F.data.startswith('order_subscription_'))
async def buy_subscription_menu(callback: CallbackQuery):
    if callback.data.__contains__('order_renew_subscription_'):
        subscription_id = callback.data[25:]
        subscription = await db_requests.get_subscription_option(subscription_id)
        other_settings = await db_requests.get_other_settings()
        renewal_discount = other_settings.renewal_discount / 100
        pay_value = int(subscription.price-subscription.price*renewal_discount)
    else:
        subscription_id = callback.data[19:]
        subscription = await db_requests.get_subscription_option(subscription_id)
        pay_value = subscription.price
    user = await db_requests.get_user(callback.from_user.id)
    payment = Payment.create({
        "amount": {
            "value": f"{pay_value}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/Poledance_sando_bot"
        },
        "capture": True,
        "description": f"Оплата абонемента на {subscription.number_of_sessions} занятий."
        }, uuid.uuid4())
    
    builder = InlineKeyboardBuilder()
    builder.button(text='Оплатить', url=payment.confirmation.confirmation_url)
    builder.button(text='🔙 Назад в профиль', callback_data='profile')
    builder.adjust(1)
    message_text = (f'Вы выбрали абонемент {subscription.number_of_sessions} занятий за {pay_value} рублей.\n\n'
                    'Пожалуйста, оплатите абонемент в течении одного часа.')
    message_pay = await callback.message.edit_text(message_text, reply_markup=builder.as_markup())

    for i in range(180):
        payment_status = Payment.find_one(payment.id)
        if payment_status.status == 'succeeded':
            await db_requests.add_new_subscription_for_user(callback.from_user.id, subscription_id)
            await message_pay.edit_reply_markup(answer_markup='')
            builder = InlineKeyboardBuilder()
            builder.button(text='🔙 Назад в профиль', callback_data='profile')
            await callback.message.answer(f'😌 Спасибо, оплата получена, абонемент на {subscription.number_of_sessions} занятий добавлен в ваш профиль.', reply_markup=builder.as_markup()) 
            try:
                await bot.send_message(1342357584, f'Ученик {user.first_name + " " + user.last_name} ({user.phone_number}) оплатил (продлил) абонемент на {subscription.number_of_sessions} занятий.')
            except:
                print(traceback.format_exc())
            return
        elif payment_status.status == 'canceled':
            break
        else:
            await asyncio.sleep(20)

    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Назад в профиль', callback_data='profile')
    try:
        await callback.message.edit_text('🤷‍♂️ Время на оплату вышло или платёж завершился с ошибкой.', reply_markup=builder.as_markup())
    except:
        '''Ничего не нужно делать, потому что пользователь уже сам вышел из меню оплаты и ему будет недоступна старая кнопка для оплаты. 
        При входе заново он сгенерирует новый счёт'''
        pass


@router.callback_query(F.data.contains('my_lesson_schedule'))
async def my_lesson_schedule(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    user_enrollments = await db_requests.get_user_enrollments(user_telegram_id=callback.from_user.id,
                                                              date_from=datetime.datetime.utcnow() + datetime.timedelta(hours=7),
                                                              date_to=datetime.datetime.utcnow() + datetime.timedelta(days=100),
                                                              with_single_group=True)
    if user_enrollments:
        message_text = 'Ваши запланированные тренировки:\n\n'
        for training in user_enrollments:
            message_text += (f'<b>Дата:</b> {datetime.datetime.strftime(training.training_date, "%d.%m.%Y %H:%M")}\n'
                            f'<b>Направление:</b> {training.direction_of_training}\n'
                            f'<b>Тренер:</b> {training.trainer.first_name} {training.trainer.last_name}\n\n')
        
        builder.button(text='🔙 Личный кабинет', callback_data='profile')
        builder.adjust(1)
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    else:
        message_text = 'У вас нет запланированных тренировок. 🙅‍♀️'
        builder.button(text='📝 Записаться на занятие', callback_data='sign_up_lesson')
        builder.button(text='🔙 Личный кабинет', callback_data='profile')
        builder.adjust(1)
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
        
        
@router.callback_query(F.data.contains('history_of_lessons'))
async def history_of_lessons(callback: CallbackQuery):
    user_enrollments = await db_requests.get_user_enrollments(user_telegram_id=callback.from_user.id,
                                                              date_from=datetime.datetime.utcnow() - datetime.timedelta(days=90),
                                                              date_to=datetime.datetime.utcnow() + datetime.timedelta(hours=7))
    if user_enrollments:
        message_text = 'Ваши прошедшие тренировки:\n\n'
        for training in user_enrollments:
            message_text += (f'<b>Дата:</b> {datetime.datetime.strftime(training.training_date, "%d.%m.%Y %H:%M")}\n'
                            f'<b>Направление:</b> {training.direction_of_training}\n'
                            f'<b>Тренер:</b> {training.trainer.first_name} {training.trainer.last_name}\n\n')
    else:
        message_text = 'У вас нет прошедших тренировок.\n\n'

    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Личный кабинет', callback_data='profile')
    builder.adjust(1)
    
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())