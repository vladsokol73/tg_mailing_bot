from telegram import Update
from telegram.ext import ContextTypes
from functools import wraps
from database import Session
from database.models import User

def check_auth(func):
    """Декоратор для проверки авторизации пользователя"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
            
            if not user or not user.is_authorized:
                await update.message.reply_text(
                    "У вас нет доступа к этой команде. "
                    "Дождитесь подтверждения администратора."
                )
                return
            
            return await func(update, context, *args, **kwargs)
    return wrapper

def admin_only(func):
    """Декоратор для проверки прав администратора"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
            
            if not user or not user.is_admin:
                await update.message.reply_text("У вас нет прав администратора.")
                return
            
            return await func(update, context, *args, **kwargs)
    return wrapper
