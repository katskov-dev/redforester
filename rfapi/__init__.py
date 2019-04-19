import aiohttp
import asyncio
from .config import PRODUCTION_CONFIG
import json


class Session:
    """
    Session - класс, необходимый для организации асинхронного общения с RedForester от имени пользователя
    Чтобы использовать на тестовом сервере, следует указать config = DEVELOPMENT_CONFIG
    """
    def __init__(self, username, password, config=PRODUCTION_CONFIG):
        self.config = config
        self.auth = aiohttp.BasicAuth(login=username, password=password, encoding="utf-8")
        self.loop = asyncio.new_event_loop()


class Request:
    """
    Request - класс для совершения запросов получения данных от сервера RedForester. Использует информацию о сессии
    """
    def __init__(self, session, method, url, data={}):
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


class Sequence(Action):
    """
    Sequence - позволяет совершить последовательно множество дейтсвий.
    Организует отдельные Action в batch-запрос, что ускоряет выполнение действий на стороне сервера.
    """
    def __init__(self, session, actions=()):
        super().__init__(session=session, method="POST", url="/api/batch")
        self.actions = actions
        self.data = [action.prepare_for_batch() for action in self.actions]


# class User:
#     id = ""
#     username = ""
#     name = ""
#     surname = ""
#     avatar = ""
#     kv_session = ""


