from aiogram.fsm.state import State, StatesGroup
    

class AddSubscriptionByAdmin(StatesGroup):
    number_of_sessions = State()
    subscription_cost = State()
    start_date = State()
