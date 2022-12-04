import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiResponseStatusError, ApiRequestError


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Успешная отправка сообщения в Telegram.')
    except telegram.TelegramError as error:
        logger.error('Ошибка при отправке сообщения: {}'.format(error))
        # raise BotSendingError('Ошибка при отправке сообщения.')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code != HTTPStatus.OK:
            raise ApiResponseStatusError(
                'Статус ответа не подходит: {}'.format(response.status_code)
            )
    except requests.RequestException as error:
        raise ApiRequestError('Ошибка при запросе к API') from error
    else:
        return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от API не является словарем.')
    if not all(['current_date' in response, 'homeworks' in response]):
        raise KeyError('В ответе API нет нужных ключей.')
    # Вот здесь был затык, pytest считал, что я не сделал проверку наличие
    # ключа. Решил сместить эту проверку выше и всё получилось. Получается,
    # pytest проверяет всё последовательно и падает при первой же ошибке?
    # Жаль, раньше не сообразил - наверное сэкономил бы во времени)
    if not response['homeworks']:
        raise ValueError('В ответе пришёл пустой список.')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Homeworks - не список.')
    return response['homeworks'][0]


def parse_status(homework):
    """Проверяет статус домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError as exc:
        raise KeyError('В ответе API отсутствует "homework_name".') from exc
    try:
        homework_status = homework['status']
    except KeyError as exc:
        raise KeyError('В ответе API отсутствует "status".') from exc
    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except KeyError as exc:
        raise TypeError('Недокументированный статус домашней работы.') from exc
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Токены отсутствуют!')
        sys.exit('Токены отсутствуют!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date', timestamp)
            homeworks = check_response(response)
            status = parse_status(homeworks)
            if status != last_message:
                send_message(bot, status)
                last_message = status
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logger.error(error_message)
            send_message(bot, error_message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format=('%(asctime)s -'
                '%(name)s -'
                '%(levelname)s -'
                '%(message)s -'
                '%(funcName)s -'
                '%(lineno)d'),
        level=logging.INFO
    )
    main()
