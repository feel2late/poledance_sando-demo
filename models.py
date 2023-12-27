from datetime import timedelta
from sqlalchemy import BigInteger, Column, Date, ForeignKey, Integer, Float, String, Boolean, Table, create_engine, DateTime
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.orm import relationship

engine = create_engine("postgresql://:@localhost/")
class Base(DeclarativeBase): pass
with Session(autoflush=False, bind=engine) as db: pass

trainer_direction_association = Table('trainer_direction_association', Base.metadata,
    Column('trainer_id', Integer, ForeignKey('trainers.id')),
    Column('direction_id', Integer, ForeignKey('directions.id'))
)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_telegram_id = Column(BigInteger)
    phone_number = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    registration_date = Column(DateTime, nullable=False)
    was_probe = Column(Boolean, default=False)

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    purchase_date = Column(Date, nullable=False)
    number_of_sessions = Column(Integer, nullable=False)
    expiration_date = Column(Date, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship('User', backref='subscriptions')

    '''def __init__(self, purchase_date, number_of_sessions, user_id):
        self.purchase_date = purchase_date
        self.number_of_sessions = number_of_sessions
        self.user_id = user_id
        self.expiration_date = purchase_date + timedelta(days=30)  # Дата окончания абонемента (1 месяц с момента покупки)'''

class SubscriptionOptions(Base):
    __tablename__ = 'subscriptions_options'
    id = Column(Integer, primary_key=True)
    number_of_sessions = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)

class Trainer(Base):
    __tablename__ = 'trainers'
    id = Column(Integer, primary_key=True)
    phone_number = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    individual_lesson_price = Column(Integer, nullable=False)
    for_two_lesson_price = Column(Integer, nullable=False)
    user_telegram_id = Column(BigInteger)
    notification_of_entries = Column(Boolean, default=True)
    about = relationship('AboutTrainer', uselist=False, back_populates='trainer')
    directions_of_teaching = relationship(
        "Direction",
        secondary=trainer_direction_association,
        back_populates="trainers"
    )

class AboutTrainer(Base):
    __tablename__ = 'about_trainers'
    id = Column(Integer, primary_key=True)
    about = Column(String)  # Текст с информацией о тренере
    trainer_photo = Column(String)  # Путь к фото тренера
    trainer_diplomas = Column(String)  # Список id разных фото (может быть JSON-строкой)

    # Внешний ключ, связывающий таблицу AboutTrainer с таблицей Trainer
    trainer_id = Column(Integer, ForeignKey('trainers.id'))

    # Определение связи с тренером
    trainer = relationship('Trainer', back_populates='about')

class Direction(Base):
    __tablename__ = 'directions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    maximum_students = Column(Integer)
    trainers = relationship(
        "Trainer",
        secondary=trainer_direction_association,
        back_populates="directions_of_teaching"
    )

class Training(Base):
    __tablename__ = 'trainings'
    id = Column(Integer, primary_key=True)
    trainer_id = Column(Integer, ForeignKey('trainers.id'))
    direction_of_training = Column(String, nullable=False)
    direction_id = Column(Integer)
    training_date = Column(DateTime, nullable=False)
    maximum_students = Column(Integer)
    trainer = relationship('Trainer', backref='trainings')

class PastTraining(Base):
    __tablename__ = 'past_trainings'
    id = Column(Integer, primary_key=True)
    training_date = Column(Date, nullable=False)
    direction = Column(String, nullable=False)
    trainer_id = Column(Integer, ForeignKey('trainers.id'))
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship('User', backref='past_trainings')
    trainer = relationship('Trainer')

    def __init__(self, training_date, direction, trainer_id, user_id):
        self.training_date = training_date
        self.direction = direction
        self.trainer_id = trainer_id
        self.user_id = user_id

class Enrollment(Base):
    __tablename__ = 'enrollments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    training_id = Column(Integer, ForeignKey('trainings.id'))
    single_group = Column(Boolean, default=False)
    # Определение связи с пользователем
    user = relationship('User', backref='enrollments')

    # Определение связи с тренировкой
    training = relationship('Training', backref='enrollments')

class OtherSchoolSettings(Base):
    __tablename__ = "other_settings"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    trial_lesson_cost = Column(Integer)
    single_lesson_cost = Column(Integer)
    one_hour_rent = Column(Integer)
    two_hour_rent = Column(Integer)
    about_school = Column(String)
    renewal_discount = Column(Integer)
    add_session_to_subscribe = Column(Integer)

class Banned(Base):
    __tablename__ = "banned"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    user_telegram_id = Column(BigInteger)
    user_name = Column(String)
    banned_at = Column(String)
    

Base.metadata.create_all(bind=engine)
