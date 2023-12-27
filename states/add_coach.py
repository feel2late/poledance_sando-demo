from aiogram.fsm.state import State, StatesGroup


class AddCoach(StatesGroup):
    coach_phonenumber = State()
    


