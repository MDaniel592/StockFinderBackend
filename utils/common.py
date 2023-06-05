import logging
import re
import time
from collections import defaultdict

import server as server
import utils.error_messages as errors
from utils.unalix.core.url_cleaner import clear_url

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True


SHOPS = [
    "aussar.es",
    "coolmod.com",
    "casemod.es",
    "izarmicro.net",
    "neobyte.es",
    "ldlc.com",
    "pccomponentes.com",
    "speedler.es",
    "vsgamers.es",
]
REGEX_EMAILS = "@gmail.com|@hotmail.com|@hotmail.es|@outlook.com|@outlook.es|@\S+.mozmail.com"

MIN_LEN_EMAIL = 10
MAX_LEN_EMAIL = 40
MIN_LEN_PASS = 8
MAX_LEN_PASS = 24


########################
# Anti-spam
########################

SPAM_MAX_MESSAGES = 15
SPAM_MAX_INTERVAL = 5  # Seconds
SPAM_BAN_TIME = 900  # Seconds


def is_spam(user_ip=None, email=None):
    if not user_ip:
        return False, 0

    user_ip = str(user_ip)
    spam_data = server.spams.get(user_ip, defaultdict(dict))

    current_time = time.time()
    if spam_data.get("banned", current_time) > current_time:
        return True, spam_data["banned"]

    messages = spam_data.get("messages", 0)
    last_time = spam_data.get("last_time", current_time)
    now = current_time

    if messages >= SPAM_MAX_MESSAGES and (now - last_time) < SPAM_MAX_INTERVAL:
        spam_data["banned"] = now + SPAM_BAN_TIME
        spam_data["messages"] = 0
        return True, spam_data["banned"]

    spam_data["messages"] = messages + 1
    spam_data["last_time"] = now

    server.spams[user_ip] = spam_data

    return False, 0


########################
# Anti-bad-url
########################
def check_url_is_valid(url):
    REGEX_FUNC = "(buscar)|(search)|(media.)|(sort=)|(busqueda)"

    try:
        pattern = re.compile(REGEX_FUNC)
        result = pattern.search(url)
        if result:
            return False
        else:
            return True
    except:
        return True


########################
# Email check
########################
def is_email_valid(email):
    try:
        provider = email[email.index("@") :]
    except:
        return errors.EMAIL_NOT_VALID, False

    if (
        not re.match(r"[^@]+@[^@]+\.[^@]+", email)
        or not re.match(REGEX_EMAILS, provider)
        or not re.fullmatch(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", email)
    ):
        return errors.EMAIL_NOT_VALID, False

    if len(email) < MIN_LEN_EMAIL:
        return errors.EMAIL_TOO_SHORT, False
    elif len(email) > MAX_LEN_EMAIL:
        return errors.EMAIL_TOO_LONG, False

    return "", True


########################
# Password check
########################
def is_password_valid(password):
    if len(password) < MIN_LEN_PASS:
        return errors.PASSWORD_TOO_SHORT, False
    elif len(password) > MAX_LEN_PASS:
        return errors.PASSWORD_TOO_LONG, False
    elif password.find(" ") != -1:
        return errors.PASSWORD_WITH_NO_SPACES, False
    else:
        return "", True


########################
# Shop check
########################
def extract_shop(url):
    shop_name = "Unknown"
    for tienda in SHOPS:
        if url.find(tienda) != -1:
            pos = tienda.find(".")
            shop_name = tienda[:pos]
            shop_name = shop_name.upper()

    if shop_name == "Unknown":
        return False

    return shop_name


########################
# URL clear
########################
def fix_clear_url(shop_name, url):
    if shop_name == "Unknown":
        url = url.rstrip("/")  # Remove trailing slash if present
        return url

    url = clear_url(url)

    if shop_name == "PCCOMPONENTES" and "/amp/" in url:
        url = url.replace("/amp/", "/")

    if "?" in url:
        url = url.split("?")[0]  # Remove query parameters

    url = url.rstrip("/")  # Remove trailing slash if present
    return url


########################
# parseNumber
########################
def parseNumber(text):
    """
    Return the first number in the given text for any locale.
    TODO we actually don't take into account spaces for only
    3-digited numbers (like "1 000") so, for now, "1 0" is 10.
    TODO parse cases like "125,000.1,0.2" (125000.1).
    :example:
    >>> parseNumber("a 125,00 €")
    125
    >>> parseNumber("100.000,000")
    100000
    >>> parseNumber("100 000,000")
    100000
    >>> parseNumber("100,000,000")
    100000000
    >>> parseNumber("100 000 000")
    100000000
    >>> parseNumber("100.001 001")
    100.001
    >>> parseNumber("$.3")
    0.3
    >>> parseNumber(".003")
    0.003
    >>> parseNumber(".003 55")
    0.003
    >>> parseNumber("3 005")
    3005
    >>> parseNumber("1.190,00 €")
    1190
    >>> parseNumber("1190,00 €")
    1190
    >>> parseNumber("1,190.00 €")
    1190
    >>> parseNumber("$1190.00")
    1190
    >>> parseNumber("$1 190.99")
    1190.99
    >>> parseNumber("$-1 190.99")
    -1190.99
    >>> parseNumber("1 000 000.3")
    1000000.3
    >>> parseNumber('-151.744122')
    -151.744122
    >>> parseNumber('-1')
    -1
    >>> parseNumber("1 0002,1.2")
    10002.1
    >>> parseNumber("")
    >>> parseNumber(None)
    >>> parseNumber(1)
    1
    >>> parseNumber(1.1)
    1.1
    >>> parseNumber("rrr1,.2o")
    1
    >>> parseNumber("rrr1rrr")
    1
    >>> parseNumber("rrr ,.o")
    """
    try:
        # First we return None if we don't have something in the text:
        if text is None:
            return None
        if isinstance(text, int) or isinstance(text, float):
            return text
        text = text.strip()
        if text == "":
            return None
        # Next we get the first "[0-9,. ]+":
        n = re.search("-?[0-9]*([,. ]?[0-9]+)+", text).group(0)
        n = n.strip()
        if not re.match(".*[0-9]+.*", text):
            return None
        # Then we cut to keep only 2 symbols:
        while " " in n and "," in n and "." in n:
            index = max(n.rfind(","), n.rfind(" "), n.rfind("."))
            n = n[0:index]
        n = n.strip()
        # We count the number of symbols:
        symbolsCount = 0
        for current in [" ", ",", "."]:
            if current in n:
                symbolsCount += 1
        # If we don't have any symbol, we do nothing:
        if symbolsCount == 0:
            pass
        # With one symbol:
        elif symbolsCount == 1:
            # If this is a space, we just remove all:
            if " " in n:
                n = n.replace(" ", "")
            # Else we set it as a "." if one occurence, or remove it:
            else:
                theSymbol = "," if "," in n else "."
                if n.count(theSymbol) > 1:
                    n = n.replace(theSymbol, "")
                else:
                    n = n.replace(theSymbol, ".")
        else:
            # Now replace symbols so the right symbol is "." and all left are "":
            rightSymbolIndex = max(n.rfind(","), n.rfind(" "), n.rfind("."))
            rightSymbol = n[rightSymbolIndex : rightSymbolIndex + 1]
            if rightSymbol == " ":
                return parseNumber(n.replace(" ", "_"))
            n = n.replace(rightSymbol, "R")
            leftSymbolIndex = max(n.rfind(","), n.rfind(" "), n.rfind("."))
            leftSymbol = n[leftSymbolIndex : leftSymbolIndex + 1]
            n = n.replace(leftSymbol, "L")
            n = n.replace("L", "")
            n = n.replace("R", ".")
        # And we cast the text to float or int:
        n = float(n)
        if n.is_integer():
            return int(n)
        else:
            return n
    except:
        pass
    return None
