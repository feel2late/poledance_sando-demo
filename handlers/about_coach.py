import asyncio
import json
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
from states.edit_about_trainer import EditTrainerDiscription
from aiogram.filters import StateFilter
from bot_init import bot
from aiogram import types


router = Router()  

@router.callback_query(F.data.startswith('edit_about_coach_'))
async def edit_about_coach_(callback: CallbackQuery, state: FSMContext):
    coach_id = callback.data[17:]
    coach = await db_requests.get_coach_by_id(coach_id)
    await state.update_data(coach=coach)
    
    builder = InlineKeyboardBuilder()
    builder.button(text='💬 О тренере', callback_data=f'discription_coach')
    builder.button(text='📷 Фото тренера', callback_data=f'edit_photo_coach')
    builder.button(text='🗂 Дипломы', callback_data=f'diplomas_coach')
    builder.button(text='🔙 Назад', callback_data=f'edit_coach_{coach.id}')
    builder.adjust(1)
    
    await callback.message.edit_text('Что хотите изменить?', reply_markup=builder.as_markup())

@router.callback_query(F.data == 'discription_coach')
async def discription_coach(callback: CallbackQuery, state: FSMContext, answer=False):
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    about_trainer = await db_requests.get_about_trainer(coach.id)
    if about_trainer:
        message_text = (f'Установлено следующее описание для тренера {coach.first_name + " " + coach.last_name}:\n\n'
                        f'"{about_trainer.about}"')
        builder = InlineKeyboardBuilder()
        builder.button(text='📝 Изменить описание', callback_data=f'edit_discription_coach')
        builder.button(text='🔙 Назад', callback_data=f'edit_about_coach_{coach.id}')
        builder.adjust(1)
    else:
        message_text = 'Для тренера не установлено описание'
        builder = InlineKeyboardBuilder()
        builder.button(text='➕ Добавить описание', callback_data=f'edit_discription_coach')
        builder.button(text='🔙 Назад', callback_data=f'edit_about_coach_{coach.id}')
        builder.adjust(1)
    
    if answer:
        await callback.answer(message_text, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    

@router.callback_query(F.data == 'edit_discription_coach')
async def edit_discription_coach(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditTrainerDiscription.discription)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_reply_markup(answer_reply_markup='')
    await callback.message.answer('Пришлите новое описание для тренера.\nЕсли нужно изменить текущее описание, скопируйте его, измените, и пришлите мне.', reply_markup=builder.as_markup())


@router.message(StateFilter(EditTrainerDiscription.discription))
async def trainer_discription_revieved(message: Message, state: FSMContext):
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    discription = message.text
    edit_discription = await db_requests.edit_trainer_discription(coach.id, discription)
    if edit_discription:
        await message.answer('✅ Описание успешно установлено.')
    else:
        await message.answer('❌ Ошибка добавления описания.')
    await discription_coach(message, state, answer=True)


@router.callback_query(F.data == 'edit_photo_coach')
async def edit_photo_coach(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.set_state(EditTrainerDiscription.photo)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.answer('Пришлите фото тренера.', reply_markup=builder.as_markup())


@router.message(F.photo, StateFilter(EditTrainerDiscription.photo))
async def trainer_discription_revieved(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id   
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    edit_photo = await db_requests.edit_trainer_photo(coach.id, photo_id)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Назад', callback_data=f'edit_about_coach_{coach.id}')
    if edit_photo:
        await message.answer('✅ Фото успешно добавлено.', reply_markup=builder.as_markup())
    else:
        await message.answer('❌ Ошибка добавления фото.', reply_markup=builder.as_markup())
    



@router.callback_query(F.data == 'diplomas_coach')
async def diplomas_coach(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(answer_reply_markup='')
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    about_trainer = await db_requests.get_about_trainer(coach.id)
    builder = InlineKeyboardBuilder()
    builder.button(text='➕ Добавить фото дипломов', callback_data=f'add_coach_diplomas')

    if about_trainer:
        if about_trainer.trainer_diplomas:
            message_text = (f'Следующие дипломы загружены для тренера {coach.first_name + " " + coach.last_name}')
            diplomas_id = json.loads(coach.about.trainer_diplomas)
            loaded_diplomas = []
            for id, diploma_id in enumerate(diplomas_id):
                loaded_diplomas.append(types.InputMediaPhoto(media=diploma_id, caption=f'{id+1}'))
            await bot.send_media_group(callback.from_user.id, loaded_diplomas)
            builder.button(text='🗑 Удалить диплом', callback_data=f'delete_coach_diplomas')
        else:
            message_text = (f'Для тренера {coach.first_name + " " + coach.last_name} нет загруженных дипломов.')
    else:
        message_text = f'Для тренера {coach.first_name + " " + coach.last_name} нет загруженных дипломов.'
    builder.button(text='🔙 Назад', callback_data=f'edit_about_coach_{coach.id}')
    builder.adjust(1)
    await callback.message.answer(message_text, reply_markup=builder.as_markup())


@router.callback_query(F.data == 'add_coach_diplomas')
async def add_coach_diplomas(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditTrainerDiscription.diploma)
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    await callback.message.edit_text('Пришлите фото дипломов.')


@router.message(F.photo, StateFilter(EditTrainerDiscription.diploma))
async def trainer_diplomas_recieved(message: Message, state: FSMContext):
    fsmdata = await state.get_data()
    fsm_photo_ids = fsmdata.get('fsm_photo_ids')
    bot_msg = fsmdata.get('bot_msg')
    
    if fsm_photo_ids:
        fsm_photo_ids.append(message.photo[-1].file_id)
        await state.update_data(fsm_photo_ids=fsm_photo_ids)
    else:
        await state.update_data(fsm_photo_ids=[message.photo[-1].file_id])
    
    fsmdata = await state.get_data()
    fsm_photo_ids = fsmdata.get('fsm_photo_ids')
    
    builder = InlineKeyboardBuilder()
    builder.button(text='💾 Сохранить', callback_data='save_diploma_picture')
    builder.button(text='❌ Отмена', callback_data='cancel_from_')
    builder.adjust(1)
    bot_msg = await message.answer(f'✅ Добавил диплом к загрузке. Итого на загрузку: {len(fsm_photo_ids)} дипломов.\n\nВы можете прислать ещё, их я тоже добавлю.', reply_markup=builder.as_markup())
    await state.update_data(bot_msg=bot_msg)
    '''if fsm_photo_ids:
        for photo_id in fsm_photo_ids:
            photos.append(types.InputMediaPhoto(media=photo_id, caption='Диплом'))
        await bot.send_media_group(message.from_user.id, photos)'''
    
    

@router.callback_query(F.data == "save_diploma_picture", StateFilter(EditTrainerDiscription.diploma))
async def save_diploma_picture(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(answer_reply_markup='')
    
    fsmdata = await state.get_data()
    coach = fsmdata.get('coach')
    fsm_photo_ids = fsmdata.get('fsm_photo_ids')
    save_diplomas = await db_requests.add_trainer_diplomas(coach.id, fsm_photo_ids)
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Назад', callback_data=f'edit_about_coach_{coach.id}')
    
    if save_diplomas:
        await callback.message.answer('Дипломы успшено добавлены.', reply_markup=builder.as_markup())
    else:
        await callback.message.answer('Ошибка добавления дипломов.', reply_markup=builder.as_markup())
    await state.update_data(fsm_photo_ids=None)
