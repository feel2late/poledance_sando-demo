from aiogram.fsm.state import State, StatesGroup


class AddClient(StatesGroup):
    user_name = State()
    


