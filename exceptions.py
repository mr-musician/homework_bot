import telegram


class CommonParentError(Exception):
    """Общий родитель для всех наших исключений."""
    pass


class ApiResponseStatusError(CommonParentError):
    """Ответ был в неправильном статусе."""
    pass


class ApiRequestError(CommonParentError):
    """Не удалось получить ответ от API."""
    pass


class BotSendingError(telegram.TelegramError):
    """Ошибка, связанная с отправкой сообщений в Телеграм"""
    pass
