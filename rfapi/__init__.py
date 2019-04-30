import aiohttp
import asyncio
from .config import PRODUCTION_CONFIG, Config
import logging

import json
import hashlib
from dataclasses import dataclass, field


class Session:
    """
    Session - класс, необходимый для организации асинхронного общения с RedForester от имени пользователя
    Чтобы использовать на тестовом сервере, следует указать config = DEVELOPMENT_CONFIG
    """

    def __init__(self, username: str, password: str, use_md5: bool = False, config: Config = PRODUCTION_CONFIG,
                 logs=True, sync=False):
        self.config = config
        self.sync = sync
        if not use_md5:
            md5 = hashlib.md5()
            md5.update(password.encode())
            password = md5.hexdigest()
        self.auth = aiohttp.BasicAuth(login=username, password=password, encoding="utf-8")
        self.loop = asyncio.new_event_loop()
        if logs:
            logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)s: %(message)s',
                                datefmt='%m.%d.%Y-%H:%M:%S')
        else:
            logging.basicConfig(level=logging.ERROR, format='[%(asctime)s] %(levelname)s:%(message)s',
                                datefmt='%m.%d.%Y-%H:%M:%S')


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


@dataclass
class DataNode:
    changes: dict = field(default_factory=dict)

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if not ("changes" in self.__dict__):
            return
        if key == "changes":
            return
        if key == "id":
            key = "user_id"
        self.changes[key] = value
        # print('SET', key, value)


@dataclass
class User(DataNode):
    """
    User - класс для хранения данных о пользователе
    """
    current: bool = True
    user_id: str = ""
    username: str = ""
    name: str = ""
    surname: str = ""
    avatar: str = ""
    registration_date: str = ""
    birthday: str = ""
    kv_session: str = ""
    is_extension_user: str = ""


class Users:
    """
    Users - репозиторий для работы с объектами типа User.
    Основная задача - реализация CRUD методов
    """

    def __init__(self, session: Session):
        self.session = session

    async def __async_update(self, user: User):

        if not user.current:
            logging.error('Вы не можете изменять данные другого пользователя!')
            return
        if len(user.changes.keys()) > 0:
            action = Action(self.session, 'PATCH', '/api/user', user.changes)
            response = await action.async_send()
            if response[0] != 200:
                logging.error('Users.update' + str(response))

    def __sync_update(self, user: User):
        self.session.loop.run_until_complete(self.__async_update(user))




    async def __async_get(self):
        request = Request(self.session, "GET", "/api/user")
        response = await request.async_send()
        if response[0] != 200:
            logging.error('Users.get' + str(response))
            return None
        else:
            args = {
                "current": True,
                "user_id": response[1]["user_id"],
                "username": response[1]["username"],
                "name": response[1]["name"],
                "surname": response[1]["surname"],
                "avatar": response[1]["avatar"],
                "registration_date": response[1]["registration_date"],
                "birthday": response[1]["birthday"],
                "kv_session": "" if not ("kv_session" in response[1]) else response[1]["kv_session"],
                "is_extension_user": response[1]["is_extension_user"],
            }
            user = User(**args)
            user.changes.clear()
            return user

    def __sync_get(self):
        return self.session.loop.run_until_complete(self.__async_get())





        # print('SET', key, value)


    async def __async_get_by_id(self, user_id: str):
        request = Request(self.session, "GET", f"/api/user/{user_id}")
        response = await request.async_send()
        if response[0] != 200:
            logging.error('Users.get' + str(response))
            return None
        else:
            args = {
                "current": True,
                "user_id": response[1]["user_id"],
                "username": response[1]["username"],
                "name": response[1]["name"],
                "surname": response[1]["surname"],
                "avatar": response[1]["avatar"],
                "registration_date": response[1]["registration_date"],
                "birthday": response[1]["birthday"],
                "kv_session": "" if not ("kv_session" in response[1]) else response[1]["kv_session"],
                "is_extension_user": response[1]["is_extension_user"],
            }
            user = User(**args)
            user.changes.clear()
            return user

    def __sync_get_by_id(self, user_id: str):
        return self.session.loop.run_until_complete(self.get_by_id(user_id))


    def __getattr__(self, item):
        # super().__getattribute__(item)
        if item == "get":
            if self.session.sync:
                return self.__sync_get
            else:
                return self.__async_get
        elif item == "get_by_id":
            if self.session.sync:
                return self.__sync_get_by_id
            else:
                return self.__async_get_by_id
        elif item == "update":
            if self.session.sync:
                return self.__sync_update
            else:
                return self.__async_update


