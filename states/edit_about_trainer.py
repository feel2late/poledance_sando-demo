from aiogram.fsm.state import State, StatesGroup


class EditTrainerDiscription(StatesGroup):
    discription = State()
    photo = State()
    diploma = State()