from datetime import datetime


def get_time() -> str:
    return datetime.now().strftime("%I:%M:%S %p")


def get_date() -> str:
    return datetime.now().strftime("%A, %B %d, %Y")


def get_datetime() -> str:
    return f"{get_date()} at {get_time()}"
