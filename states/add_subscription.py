from aiogram.fsm.state import State, StatesGroup


class AddSubscription(StatesGroup):
    number_of_sessions = State()
    subscription_cost = State()
    

class AddSubscriptionByAdmin(StatesGroup):
    number_of_sessions = State()
    subscription_cost = State()

