from typing import Optional
from aiogram.filters.callback_data import CallbackData


class ChangeDirectionStatus(CallbackData, prefix="chng_dir_status"):
    coach_id: Optional[int]
    status: Optional[str]
    direction_id: Optional[int]

