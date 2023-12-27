from aiogram.fsm.state import State, StatesGroup


class GetUser(StatesGroup):
    user_phonenumber = State()
    


