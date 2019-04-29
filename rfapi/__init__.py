import aiohttp
import asyncio
from .config import PRODUCTION_CONFIG, Config
import logging

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

    async def __call__(self, *args, **kwargs):
        return await self.async_send()


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

    async def __call__(self, *args, **kwargs):
        return await self.async_send()


class Sequence(Action):
    """
    Sequence - позволяет совершить последовательно множество дейтсвий.
    Организует отдельные Action в batch-запрос, что ускоряет выполнение действий на стороне сервера.
    """

    def __init__(self, session: Session, actions: tuple = ()):
        super().__init__(session=session, method="POST", url="/api/batch")
        self.actions = actions
        self.data = [action.prepare_for_batch() for action in self.actions]


class User:
    """
    User - класс для работы с моделью пользователя
    """

    def __init__(self, session: Session, user_id: str = ""):
        self.changes = {}
        self.session = session
        self.current = True if user_id == "" else False
        self.id = "" if self.current else user_id
        self.username = ""
        self.name = ""
        self.surname = ""
        self.avatar = ""
        self.registration_date = ""
        self.birthday = ""
        self.kv_session = ""
        self.is_extension_user = ""
        self.changes.clear()

        response = self.session.loop.run_until_complete(self.async_update())

    def __str__(self):
        return str(self.name) + " " + str(self.surname) + f"({self.username})"

    def __update_from_response(self, response: dict):
        self.id = response[1]["user_id"]
        self.username = response[1]["username"]
        self.name = "" if not ("name" in response[1]) else response[1]["name"]
        self.surname = "" if not ("surname" in response[1]) else response[1]["surname"]
        self.avatar = "" if not ("avatar" in response[1]) else response[1]["avatar"]
        self.registration_date = "" if not ("registration_date" in response[1]) else response[1]["registration_date"]
        self.birthday = "" if not ("birthday" in response[1]) else response[1]["birthday"]
        self.kv_session = "" if not ("kv_session" in response[1]) else response[1]["kv_session"]
        self.is_extension_user = "" if not ("is_extension_user" in response[1]) else response[1]["is_extension_user"]
        self.changes.clear()

    def __request_current_user_information(self):
        return Request(self.session, "GET", "/api/user")

    def __request_other_user_information(self, user_id: str):
        return Request(self.session, "GET", f"/api/user/{user_id}")

    async def async_update(self):
        request = self.__request_current_user_information() if self.current else self.__request_other_user_information(
            self.id)
        response = await request()
        # print(response)
        if response[0] == 200:
            self.__update_from_response(response)
            # print(self.__dict__)
        else:
            print('ERROR User.async_update', response)

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key == "changes":
            return
        if key == "id":
            key = "user_id"
        self.changes[key] = value
        # print('SET', key, value)

    async def async_save(self):
        if not self.current:
            print('Error, вы не можете изменять данные другого пользователя')
            return
        if len(self.changes.keys()) > 0:
            action = Action(self.session, 'PATCH', '/api/user', self.changes)
            response = await action.async_send()
            if response[0] != 200:
                print('Error User.async_save')

    def save(self):
        self.session.loop.run_until_complete(self.async_save())
