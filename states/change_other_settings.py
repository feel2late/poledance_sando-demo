from aiogram.fsm.state import State, StatesGroup


class ChangeOtherSettings(StatesGroup):
    renewal_discount = State()
    trial_lesson_cost = State()
    one_hour_rent = State()
    two_hour_rent = State()
    single_lesson_cost = State()
    add_session_to_subscribe = State()
    


