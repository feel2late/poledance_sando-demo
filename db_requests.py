import datetime
import json
import traceback
import secrets
import string
from models import User, Subscription, Trainer, Direction, Training, PastTraining, Enrollment, Banned, SubscriptionOptions, AboutTrainer, OtherSchoolSettings
from models import db
from sqlalchemy import and_, func, or_
import datetime

async def registration_user(user_telegram_id, phone_number, first_name, last_name):
    client = User(user_telegram_id=user_telegram_id,
                phone_number=phone_number,
                first_name=first_name,
                last_name=last_name,
                registration_date=datetime.datetime.utcnow().replace(microsecond=0))
    try:
        db.add(client)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False

async def merging_user_objects_by_phonenumber(user_telegram_id, user_phone):
    client = db.query(User).filter(User.phone_number == user_phone).first()
    client.user_telegram_id = user_telegram_id
    db.commit()

async def add_new_client(phone_number, first_name, last_name):
    client = User(phone_number=phone_number,
                first_name=first_name,
                last_name=last_name,
                registration_date=datetime.datetime.utcnow().replace(microsecond=0))
    try:
        db.add(client)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False
     
async def check_user_registation(user_telegram_id):
    client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    if client:
        return True
    else:
        return False
    
async def get_user(user_telegram_id):
    client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    if client:
        return client
    else:
        return False
    
async def get_all_users():
    users = db.query(User).all()
    return users
    
async def edit_numbers_of_sessions_for_user_subscription(subscription_id, new_value):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if subscription:
        try:
            subscription.number_of_sessions = new_value 
            db.commit()
            return True
        except:
            print(traceback.format_exc())
            return False
    else:
        return False

async def delete_user_subscription(subscription_id):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    try:
        db.delete(subscription)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False
    
async def edit_validity_for_user_subscription(subscription_id, new_value):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if subscription:
        try:
            subscription.expiration_date = new_value 
            db.commit()
            return True
        except:
            print(traceback.format_exc())
            return False
    else:
        return False
    
async def get_all_users():
    users = db.query(User).all()
    return users
    
async def change_user_probe_status(user_telegram_id, status: bool):
    client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    if client:
        client.was_probe = status
        db.commit()
    else:
        return False
    
async def get_user_by_phonenumber(phone_number):
    client = db.query(User).filter(User.phone_number == phone_number).first()
    if client:
        return client
    else:
        return False
    
async def get_user_by_id(id):
    client = db.query(User).filter(User.id == id).first()
    if client:
        return client
    else:
        return False
    
async def get_coach_by_phonenumber(phone_number):
    coach = db.query(Trainer).filter(Trainer.phone_number == phone_number).first()
    if coach:
        return coach
    else:
        return False
    
async def get_coach_by_id(id):
    coach = db.query(Trainer).filter(Trainer.id == id).first()
    if coach:
        return coach
    else:
        return False

async def get_user_subscription(subscription_id):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    return subscription

async def add_new_subscription_for_user(user_telegram_id, subscription_option_id, start_date=False, user_phone=False):
    if user_phone:
        client = db.query(User).filter(User.phone_number == user_phone).first()
    else:
        client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    subscription_option = db.query(SubscriptionOptions).filter(SubscriptionOptions.id == subscription_option_id).first()
    current_date = datetime.datetime.utcnow()
    active_subscriptions = db.query(Subscription).filter(Subscription.user == client, Subscription.expiration_date >= current_date.date()).order_by(Subscription.expiration_date).all()
    
    if start_date:
        purchase_date = start_date
        expiration_date = start_date + datetime.timedelta(days=30)
    elif active_subscriptions:
        # Если есть действующий абонемент, дату окончания нового ставим как дату окончания действующего + 30 дней.
        last_subscription = active_subscriptions[-1]
        purchase_date = last_subscription.expiration_date + datetime.timedelta(days=1)
        expiration_date = last_subscription.expiration_date + datetime.timedelta(days=31) 
    else:
        purchase_date = current_date
        expiration_date = current_date + datetime.timedelta(days=30)
    
    subscription = Subscription(
        purchase_date=purchase_date,
        number_of_sessions=subscription_option.number_of_sessions,
        expiration_date=expiration_date,
        user=client
    )
    try:
        db.add(subscription)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False

async def get_actual_subscription(user_telegram_id=False, user_phone=False):
    if user_phone:
        client = db.query(User).filter(User.phone_number == user_phone).first()
    else:
        client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()

    current_date = datetime.datetime.utcnow()
    active_subscriptions = db.query(Subscription).filter(Subscription.user == client, Subscription.expiration_date >= current_date.date()).order_by(Subscription.expiration_date)
    first_active_subscription = active_subscriptions.first()
    return first_active_subscription
    
async def get_all_user_subscriptions(user_telegram_id):
    client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    subscriptions = db.query(Subscription).filter(Subscription.user == client).all()
    return subscriptions
    
async def get_all_actual_user_subscriptions(user_telegram_id=False, user_phone=False):

    if user_phone:
        client = db.query(User).filter(User.phone_number == user_phone).first()
    else:
        client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    current_date = datetime.datetime.utcnow()
    active_subscriptions = db.query(Subscription).filter(Subscription.user == client, Subscription.expiration_date >= current_date.date()).order_by(Subscription.expiration_date).all()
    return active_subscriptions
    
async def add_subscriptions_options(number_of_sessions, price):
    subscription_option = db.query(SubscriptionOptions).filter(SubscriptionOptions.number_of_sessions == number_of_sessions, price == price).first()
    if not subscription_option:
        subscription_option = SubscriptionOptions(number_of_sessions=number_of_sessions, price=price)
        db.add(subscription_option)
        db.commit()
        return True
    else:
        return False

async def get_all_subscriptions_options() -> list:
    subscriptions = db.query(SubscriptionOptions).order_by(SubscriptionOptions.number_of_sessions).all()
    return subscriptions

async def get_subscription_option(subscription_id) -> list:
    subscription = db.query(SubscriptionOptions).filter(SubscriptionOptions.id == subscription_id).first()
    return subscription

async def add_coach(phone_number, first_name, last_name, user_telegram_id):
    trainer = Trainer(
        phone_number=phone_number,
        first_name=first_name,
        last_name=last_name,
        individual_lesson_price=1200,
        for_two_lesson_price=1800,
        user_telegram_id = user_telegram_id
    )
    try:
        db.add(trainer)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False
    
async def get_coaches():
    coaches = db.query(Trainer).all()
    return coaches

async def get_coaches_telegram_id():
    users = db.query(User).all()
    coaches = db.query(Trainer).all()
    coaches_list = []
    for coach in coaches:
        for user in users:
            if coach.phone_number == user.phone_number:
                coaches_list.append(user.user_telegram_id)
    return coaches_list
    
async def edit_coach_by_id(id: int, item: str, value: [int, str]):
    coach = db.query(Trainer).filter(Trainer.id == id).first()
    if coach:
        if item == 'name':
            fullname = value.split(' ')
            coach.first_name = fullname[0]
            coach.last_name = fullname[1]
        elif item == 'individual_lesson_price':
            coach.individual_lesson_price = value
        elif item == 'for_two_lesson_price':
            coach.for_two_lesson_price = value
    try:
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False
    
async def add_direction(direction_name, max_students):
    direction = Direction(name=direction_name, maximum_students=max_students)
    try:
        db.add(direction)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False

async def delete_direction(direction_id):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    try:
        db.delete(direction)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False

async def delete_subscription(subscription_id):
    subscription = db.query(SubscriptionOptions).filter(SubscriptionOptions.id == subscription_id).first()
    try:
        db.delete(subscription)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False

async def get_all_directions():
    directions = db.query(Direction).all()
    return directions

async def get_direction_by_name(direction_name):
    direction = db.query(Direction).filter(Direction.name == direction_name).first()
    return direction

async def get_direction_by_id(direction_id):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    return direction

async def change_direction_name(old_direction_name, new_direction_name):
    direction = db.query(Direction).filter(Direction.name == old_direction_name).first()
    try:
        direction.name = new_direction_name
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False
    
async def change_direction_status_for_coach(coach_id: int, direction_id: int, status: bool):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    coach = db.query(Trainer).filter(Trainer.id == coach_id).first()
    if status == True:
        coach.directions_of_teaching.append(direction)
    elif status == False:
        coach.directions_of_teaching.remove(direction)
    db.commit()

async def add_training(coach_id: int, direction_id: int, date: datetime):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    coach = db.query(Trainer).filter(Trainer.id == coach_id).first()
    new_training = Training(trainer_id=coach.id,
                                direction_of_training=direction.name,
                                training_date=date,
                                direction_id=direction_id,
                                maximum_students=direction.maximum_students)
    try:
        db.add(new_training)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False

async def delete_training(coach_id: int, direction_id: int, date: datetime):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    training = db.query(Training).filter(Training.trainer_id == coach_id, Training.direction_of_training == direction.name, Training.training_date == date).first()
    
    try:
        db.delete(training)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False
    
async def get_training(coach_id: int, direction_id: int, date: datetime):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    training = db.query(Training).filter(Training.trainer_id == coach_id, 
                                         Training.direction_of_training == direction.name, 
                                         Training.training_date == date).first()
    return training

async def get_training_by_id(id: int) -> object:
    training = db.query(Training).filter(Training.id == id).first()
    return training

async def get_trainings_by_coach(coach_id: int, date_from: datetime, date_to: datetime, direction_name: str = False) -> list[object]:
    if not direction_name:
        trainings = db.query(Training).filter(Training.trainer_id == coach_id, Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
    else:
        trainings = db.query(Training).filter(Training.trainer_id == coach_id, Training.direction_of_training == direction_name, Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
    return trainings

async def get_individual_trainings(coach_id: int, date_from: datetime, date_to: datetime, with_booking=False) -> list[object]:
    if not with_booking:
        if coach_id == False:
            individual_dual_trainings = db.query(Training).filter(Training.direction_of_training == 'Индивидуальное парное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
            individual_trainings = db.query(Training).filter(Training.direction_of_training == 'Индивидуальное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
        else:
            individual_dual_trainings = db.query(Training).filter(Training.trainer_id == coach_id, Training.direction_of_training == 'Индивидуальное парное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
            individual_trainings = db.query(Training).filter(Training.trainer_id == coach_id, Training.direction_of_training == 'Индивидуальное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
        free_individual_trainings = []
        for training in individual_trainings:
            intersection = False
            if len(await get_training_enrollments(training.id)) == 0:
                for dual_training in individual_dual_trainings:
                    if training.training_date == dual_training.training_date:
                        if len(await get_training_enrollments(dual_training.id)) > 0:
                            intersection = True
                            break
                if intersection == False:
                    free_individual_trainings.append(training)
        return free_individual_trainings
    else:
        individual_trainings = db.query(Training).filter(Training.trainer_id == coach_id, Training.direction_of_training == 'Индивидуальное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
        return individual_trainings
    
async def get_individual_dual_trainings(coach_id: int, date_from: datetime, date_to: datetime, with_booking=False) -> list[object]:
    if not with_booking:
        if coach_id == False:
            individual_dual_trainings = db.query(Training).filter(Training.direction_of_training == 'Индивидуальное парное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
            individual_trainings = db.query(Training).filter(Training.direction_of_training == 'Индивидуальное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
        else:
            individual_dual_trainings = db.query(Training).filter(Training.trainer_id == coach_id, Training.direction_of_training == 'Индивидуальное парное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
            individual_trainings = db.query(Training).filter(Training.trainer_id == coach_id, Training.direction_of_training == 'Индивидуальное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
        free_individual_dual_trainings = []
        for training in individual_dual_trainings:
            intersection = False
            if len(await get_training_enrollments(training.id)) == 0:
                for individual_training in individual_trainings:
                    if training.training_date == individual_training.training_date:
                        if len(await get_training_enrollments(individual_training.id)) > 0:
                            intersection = True
                            break
                if intersection == False:
                    free_individual_dual_trainings.append(training)
        return free_individual_dual_trainings
    else:
        individual_trainings = db.query(Training).filter(Training.trainer_id == coach_id, Training.direction_of_training == 'Индивидуальное парное', Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
        return individual_trainings
    
async def get_all_available_trainings(date_from=False, date_to=False) -> list[object]:
    if not date_from:
        date_from = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    if not date_to:
        date_to = datetime.datetime.utcnow() + datetime.timedelta(weeks=12)
    trainings = db.query(Training).filter(Training.training_date.between(date_from, date_to)).order_by(Training.training_date).all()
    return trainings

async def get_available_trainings(date_from: datetime, date_to: datetime):
    pass

async def enrollment_on_training(user_telegram_id=False, training_id=False, user_phone=False, single_group=False):
    """Записываем ученика на тренировку"""
    if user_phone:
        client = db.query(User).filter(User.phone_number == user_phone).first()
    else:
        client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    enrollment_on_training = Enrollment(user_id=client.id, training_id=training_id, single_group=single_group)
    try:
        db.add(enrollment_on_training)    
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False
    
async def unenroll_training(user_telegram_id=False, training_id=False, user_phone=False):
    """Удаляем запись ученика на тренировку"""
    if user_phone:
        client = db.query(User).filter(User.phone_number == user_phone).first()
    else:
        client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    enrollment = db.query(Enrollment).filter(Enrollment.user_id == client.id, Enrollment.training_id == training_id).first()
    try:
        db.delete(enrollment)    
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False
    
async def get_training_enrollments(training_id: int) -> list[object]:
    """Получаем записи на конкретную тренировку"""
    enrollments = db.query(Enrollment).filter(Enrollment.training_id == training_id).all()
    return enrollments

async def check_user_enrollment(user_telegram_id, training_id, user_phone=False):
    """Проверяем, записан ли ученик на тренировку"""
    if user_phone:
        client = db.query(User).filter(User.phone_number == user_phone).first()
    else:
        client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    enrollment = db.query(Enrollment).filter(Enrollment.user_id == client.id, Enrollment.training_id == training_id).first()
    if enrollment:
        return True
    else:
        return False
    
async def get_user_enrollments(user_telegram_id=False, user_phone=False, date_from=False, date_to=False, without_individual=False, with_single_group=False):
    """Получаем тренировки, на которые записан клиент, в временном интервале"""
    if user_phone:
        client = db.query(User).filter(User.phone_number == user_phone).first()
    else:
        client = db.query(User).filter(User.user_telegram_id == user_telegram_id).first()
    
    if with_single_group:
        enrollments = db.query(Enrollment).filter(Enrollment.user_id == client.id).all()
    else:
        enrollments = db.query(Enrollment).filter(Enrollment.user_id == client.id, Enrollment.single_group != True).all()

    if without_individual:
        trainings = db.query(Training).filter(Training.training_date.between(date_from, date_to), Training.direction_of_training != 'Индивидуальное', Training.direction_of_training != 'Индивидуальное парное').all()
    else:
        trainings = db.query(Training).filter(Training.training_date.between(date_from, date_to)).all()
    user_trainings_list = []
    
    for enrollment in enrollments:
        for training in trainings:
            if enrollment.training_id == training.id:
                user_trainings_list.append(training)
    
    sorted_trainings = sorted(user_trainings_list, key=lambda x: x.training_date)

    return sorted_trainings

async def get_about_trainer(trainer_id):
    about = db.query(AboutTrainer).filter(AboutTrainer.trainer_id == trainer_id).first()
    return about

async def edit_trainer_discription(trainer_id, discription):
    about = db.query(AboutTrainer).filter(AboutTrainer.trainer_id == trainer_id).first()
    if about:
        about.about = discription
        try:
            db.commit()
            return True
        except:
            print(traceback.format_exc())
            return False        
    else:
        about = AboutTrainer(about=discription, trainer_id=trainer_id)
        try:
            db.add(about)
            db.commit()
            return True
        except:
            print(traceback.format_exc())
            return False
        
async def edit_trainer_photo(trainer_id, photo_id):
    about = db.query(AboutTrainer).filter(AboutTrainer.trainer_id == trainer_id).first()
    if about:
        about.trainer_photo = photo_id
        try:
            db.commit()
            return True
        except:
            print(traceback.format_exc())
            return False        
    else:
        about = AboutTrainer(trainer_photo=photo_id, trainer_id=trainer_id)
        try:
            db.add(about)
            db.commit()
            return True
        except:
            print(traceback.format_exc())
            return False
        
async def add_trainer_diplomas(trainer_id: int, diplomas_id: list):
    about = db.query(AboutTrainer).filter(AboutTrainer.trainer_id == trainer_id).first()
    if about:
        if about.trainer_diplomas: 
            about.trainer_diplomas = json.dumps(json.loads(about.trainer_diplomas) + diplomas_id)
        else:
            about.trainer_diplomas = json.dumps(diplomas_id)
        try:
            db.commit()
            return True
        except:
            print(traceback.format_exc())
            return False
    else:
        about = AboutTrainer(trainer_diplomas=json.dumps(diplomas_id), trainer_id=trainer_id)
        try:
            db.add(about)
            db.commit()
            return True
        except:
            print(traceback.format_exc())
            return False

async def change_other_settings(setting: str, value: int):
    """Варианты настроек: trial_lesson_cost, one_hour_rent, two_hour_rent, renewal_discount, single_lesson_cost, add_session_to_subscribe"""
    settings = db.query(OtherSchoolSettings).first()
    try:
        if setting == 'trial_lesson_cost':
            settings.trial_lesson_cost = value
        elif setting == 'one_hour_rent':
            settings.one_hour_rent = value
        elif setting == 'two_hour_rent':
            settings.two_hour_rent = value
        elif setting == 'renewal_discount':
            settings.renewal_discount = value
        elif setting == 'single_lesson_cost':
            settings.single_lesson_cost = value
        elif setting == 'add_session_to_subscribe':
            settings.add_session_to_subscribe = value
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False

async def create_other_settings():
    new_settings = OtherSchoolSettings(trial_lesson_cost=300,
                                    one_hour_rent=1500,
                                    two_hour_rent=2000,
                                    renewal_discount=10)
    try:
        db.add(new_settings)
        db.commit()
        return True
    except:
        print(traceback.format_exc())
        return False
    
async def get_other_settings():
    settings = db.query(OtherSchoolSettings).first()
    return settings