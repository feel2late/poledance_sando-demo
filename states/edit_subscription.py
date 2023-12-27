from aiogram.fsm.state import State, StatesGroup


class EditUserSubscription(StatesGroup):
    number_of_sessions = State()
    expiration_date = State()

class UserEditSelfSubscription(StatesGroup):
    number_of_session_to_add = State()