import datetime


def get_current_time_str():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
