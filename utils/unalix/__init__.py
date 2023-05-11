from utils.unalix.__version__ import __description__, __title__, __version__
from utils.unalix._core import clear_url, unshort_url
from utils.unalix._exceptions import (ConnectError, InvalidScheme, InvalidURL,
                                      TooManyRedirects)

__all__ = [
    "__description__",
    "__title__",
    "__version__",
    "clear_url",
    "unshort_url",
    "InvalidURL",
    "InvalidScheme",
    "TooManyRedirects",
    "ConnectError",
]

__locals = locals()

for __name in __all__:
    if not __name.startswith("__"):
        setattr(__locals[__name], "__module__", "")
