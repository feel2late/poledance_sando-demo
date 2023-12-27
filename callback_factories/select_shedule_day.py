from typing import Optional
from aiogram.filters.callback_data import CallbackData


class SelectScheduleDay(CallbackData, prefix="sel_sch_day"):
    day: Optional[int]
    month: Optional[str]
    year: Optional[int]

