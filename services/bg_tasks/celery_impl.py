from typing import Callable

from celery import Celery, Task
from config import settings

app = Celery(__name__, broker=settings.redis.create_url(db=1), backend=settings.redis.create_url(1))
app.conf.timezone = 'Europe/Moscow'


class CustomTask(Task):
    def __init__(self, func: Callable, name: str):
        self.func = func
        self.name = name

    def run(self, *args, **kwargs):
        self.func(*args, **kwargs)


class CeleryBGTasks:
    async def create_bg_task(self, func: Callable, *args, **kwargs):
        task = app.task()(func)
        task.delay(*args, **kwargs)

        # func_name: str = func.__name__ + "_" + str(datetime.datetime.now())
        # task = CustomTask(func=func, name=func_name)
        # task.delay(*args, **kwargs)
