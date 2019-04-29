import aiohttp
import asyncio
from .config import PRODUCTION_CONFIG, Config

import json
import hashlib


class Session:
    """
    Session - класс, необходимый для организации асинхронного общения с RedForester от имени пользователя
    Чтобы использовать на тестовом сервере, следует указать config = DEVELOPMENT_CONFIG
    """

    def __init__(self, username: str, password: str, use_md5: bool = False, config: Config = PRODUCTION_CONFIG, ):
        self.config = config
        if not use_md5:
            md5 = hashlib.md5()
            md5.update(password.encode())
            password = md5.hexdigest()
        self.auth = aiohttp.BasicAuth(login=username, password=password, encoding="utf-8")
        self.loop = asyncio.new_event_loop()


class Request:
    """
    Request - класс для совершения запросов получения данных от сервера RedForester. Использует информацию о сессии
    """

    def __init__(self, session: Session, method: str, url: str, data: dict = {}):
        self.session = session
        self.method = method
        self.url = url
        self.data = data

    async def async_send(self):
        async with aiohttp.ClientSession(auth=self.session.auth) as session:
            async with session.request(self.method,
                                       f"{self.session.config.PROTOCOL}://{self.session.config.BASIC_URL}{self.url}",
                                       ) as response:
                return response.status, json.loads(await response.text())

    def send(self):
        return self.session.loop.run_until_complete(self.async_send())

    def __call__(self, sync=False, *args, **kwargs):
        if not sync:
            return self.session.loop.run_until_complete(self.async_send())
        else:
            return self.send()


class Action(Request):
    """
    Action - класс для совершения действий в RedForester.
    """

    def prepare_for_batch(self):
        result = {
            "url": self.url,
            "method": self.method,

        }
        if len(self.data) > 0:
            result["body"] = json.dumps(self.data)
        return result

    async def async_send(self):
        headers = {
            "Content-Type": "application/json"
        }
        # print(json.dumps(self.data))
        async with aiohttp.ClientSession(auth=self.session.auth) as session:
            async with session.request(self.method,
                                       f"{self.session.config.PROTOCOL}://{self.session.config.BASIC_URL}{self.url}",
                                       data=json.dumps(self.data), headers=headers) as response:
                return response.status, await response.text()

    def send(self):
        return self.session.loop.run_until_complete(self.async_send())

    def __call__(self, sync=False, *args, **kwargs):
        if not sync:
            return self.session.loop.run_until_complete(self.async_send())
        else:
            return self.send()


class Sequence(Action):
    """
    Sequence - позволяет совершить последовательно множество дейтсвий.
    Организует отдельные Action в batch-запрос, что ускоряет выполнение действий на стороне сервера.
    """

    def __init__(self, session: Session, actions: tuple = ()):
        super().__init__(session=session, method="POST", url="/api/batch")
        self.actions = actions
        self.data = [action.prepare_for_batch() for action in self.actions]


# class User:
#     def __init__(self, session: Session):
#         self.session = session
#         self.id = ""
#         self.username = ""
#         self.name = ""
#         self.surname = ""
#         self.avatar = ""
#         # self.registration_date = ""
