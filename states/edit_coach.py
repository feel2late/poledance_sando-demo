from aiogram.fsm.state import State, StatesGroup


class EditCoach(StatesGroup):
    coach_name = State()
    edit_coach_individual_cost = State()
    edit_coach_cost_for_two = State()


