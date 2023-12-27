import asyncio
from aiogram import Dispatcher
import aioschedule
from bot_init import bot
import db_requests
import datetime
from handlers import (menu, start, profile, admin, cancel, sign_up_lesson, 
                      about_coach, sign_up_individual_lesson, 
                      sign_up_individual_dual_lesson, coaching, sign_up_trial_lesson, get_user, backrelation,
                      buy_one_group_lesson)
from middlewares.outer import BotInService, BotInServiceCallback


async def send_remind():
    trainings = await db_requests.get_all_available_trainings(datetime.datetime.utcnow() + datetime.timedelta(hours=10), datetime.datetime.utcnow() + datetime.timedelta(days=1, hours=7))
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    
    for training in trainings:        
        if int((training.training_date - now).seconds / 3600) == 23:
            enrollments = await db_requests.get_training_enrollments(training.id)
            for enrollment in enrollments:
                message_text = (f'Напоминаю, вы записаны на тренировку "{training.direction_of_training}" к тренеру {training.trainer.first_name + " " + training.trainer.last_name} '
                                f'на {datetime.datetime.strftime(training.training_date, "%d.%m.%Y %H:%M")} (завтра).\n\n'
                                'Будем вас ждать 😍')
                if enrollment.user.user_telegram_id:
                    try:
                        await bot.send_message(enrollment.user.user_telegram_id, message_text)
                    except:
                        continue
        

async def reminder():
    aioschedule.every().hour.at(":00").do(send_remind)
    
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup():
    asyncio.create_task(reminder())


async def main():
    dp = Dispatcher()
    #dp.message.outer_middleware(BotInService())
    #dp.callback_query.outer_middleware(BotInServiceCallback())
    dp.include_routers(menu.router,
                       start.router, 
                       profile.router,
                       admin.router,
                       cancel.router,
                       sign_up_lesson.router,
                       about_coach.router,
                       sign_up_individual_lesson.router,
                       sign_up_individual_dual_lesson.router,
                       coaching.router,
                       sign_up_trial_lesson.router, 
                       get_user.router,
                       backrelation.router,
                       buy_one_group_lesson.router)
    await on_startup()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    

if __name__ == "__main__":
    asyncio.run(main())