from aiogram.fsm.state import State, StatesGroup


class AddDirection(StatesGroup):
    direction_name = State()
    max_students = State()