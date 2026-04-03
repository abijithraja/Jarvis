from datetime import datetime


def get_time():
    return datetime.now().strftime("%I:%M %p")


def handle_system_command(text):
    return None