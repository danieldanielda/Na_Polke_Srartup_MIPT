from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    waiting_for_agreement = State()
    waiting_for_photo = State()
    waiting_for_analysis_type = State()
    analysis_finished = State()
    
    waiting_for_recommendation_query = State()
    waiting_for_routine_query = State()

    waiting_for_rating = State()