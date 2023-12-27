from datetime import datetime
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import db_requests
import asyncio


class BotInService(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = data.get('event_from_user').id

        if user_id == 376131047:
            return await handler(event, data) 
        else:
            await event.answer("👷‍♂️ Бот на обслуживании, попробуйте позже.")      


class BotInServiceCallback(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = data.get('event_from_user').id

        if user_id == 376131047:
            return await handler(event, data) 
        else:
            await event.answer("👷‍♂️ Бот на обслуживании, попробуйте позже.", show_alert=True)        



        
