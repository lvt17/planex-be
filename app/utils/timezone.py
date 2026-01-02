from datetime import datetime, timedelta, timezone

def get_now_vn():
    """Returns the current time in GMT+7 (Vietnam Time)"""
    return datetime.now(timezone(timedelta(hours=7)))
