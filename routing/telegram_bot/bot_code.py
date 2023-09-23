import logging
import os
import random
import string
import time

from telegram import Update
from telegram.error import Unauthorized
from telegram.ext import CallbackContext, CommandHandler, Updater

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

updater = Updater(os.environ.get("TELEGRAM_BOT_TOKEN"))
dispatcher = updater.dispatcher


CODE_LENGTH = 6
SPAM_MESSAGES = 10
SPAM_INTERVAL = 5
BAN_TIME = 300

SPAMS = {}


def is_spam(user_id):
    if int(user_id) < 0:
        return True

    now = int(time.time())
    user_spam = SPAMS.get(user_id, {"next_time": now + SPAM_INTERVAL, "messages": 0, "banned": 0})
    user_spam["messages"] += 1

    if user_spam["banned"] >= now:
        return True

    if user_spam["next_time"] >= now:
        if user_spam["messages"] >= SPAM_MESSAGES:
            SPAMS[user_id]["banned"] = now + BAN_TIME
            return True
    else:
        SPAMS[user_id] = {"next_time": now + SPAM_INTERVAL, "messages": 1, "banned": 0}

    return False


def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat_id = update.effective_message.chat_id

    if is_spam(chat_id):
        logger.warning(f"User: {chat_id} - Spam detected")
        return None

    logger.warning(f"chat_id: {chat_id} - {user.username} - {user.first_name} - Replied with ID")
    update.message.reply_markdown_v2(f"Hola {user.mention_markdown_v2()}! Su ID de telegram es {chat_id}")


def send_code(telegram_id) -> str:
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=CODE_LENGTH))
    message = f"Para vincular su usuario de telegram introduzca en la web el siguiente código: {code}"

    try:
        dispatcher.bot.send_message(chat_id=telegram_id, text=message, parse_mode="MarkdownV2")
        logger.warning(f"Código de telegram enviado a: {telegram_id} - Code: {code}")
        return code

    except Unauthorized as e:
        logger.error(f"Unauthorized user_id {telegram_id} with error: {e}")
        return None


def main() -> None:
    dispatcher.add_handler(CommandHandler("start", start))
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
