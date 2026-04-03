from collections import deque

# Keep last 50 tasks in memory during session
_tasks: deque = deque(maxlen=50)


def add_task(task: str):
    if task and task.strip():
        _tasks.append(task.strip())


def get_tasks() -> list:
    return list(_tasks)


def get_recent_tasks(n: int = 5) -> list:
    return list(_tasks)[-n:]


def clear_tasks():
    _tasks.clear()
