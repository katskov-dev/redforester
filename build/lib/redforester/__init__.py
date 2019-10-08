import aiohttp
import asyncio
from .config import PRODUCTION_CONFIG, Config
import logging

import json
import hashlib
from dataclasses import dataclass, field
import typing
import datetime


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
                if response.status in [500, 404]:
                    logging.critical(f'Request.async_send {await response.text()}')
                    return response.status, await response.text()
                elif response.status != 200:
                    data = json.loads(await response.text())
                    logging.error(f"Request.async_send, code: {data['code']}, message: {data['message']}")
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
        async with aiohttp.ClientSession(auth=self.session.auth) as session:
            async with session.request(self.method,
                                       f"{self.session.config.PROTOCOL}://{self.session.config.BASIC_URL}{self.url}",
                                       data=json.dumps(self.data), headers=headers) as response:
                if response.status in [500, 404]:
                    logging.critical(f'Action.async_send {await response.text()}')
                    return response.status, await response.text()
                elif response.status != 200:
                    data = json.loads(await response.text())
                    logging.error(f"Action.async_send, code: {data['code']}, message: {data['message']}")
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

    async def async_update(self, user: User):

        if not user.current:
            logging.error('Вы не можете изменять данные другого пользователя!')
            return
        if len(user.changes.keys()) > 0:
            action = Action(self.session, 'PATCH', '/api/user', user.changes)
            response = await action.async_send()
            if response[0] != 200:
                data = json.loads(response[1])
                logging.error(f"Users.update, code: {data['code']}, message: {data['message']}")

    def update(self, user: User):
        self.session.loop.run_until_complete(self.async_update(user))

    async def async_get(self):
        request = Request(self.session, "GET", "/api/user")
        response = await request.async_send()
        if response[0] != 200:
            data = json.loads(response[1])
            logging.error(f"Users.get, code: {data['code']}, message: {data['message']}")

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

    def get(self):
        return self.session.loop.run_until_complete(self.async_get())

        # print('SET', key, value)

    async def async_get_by_id(self, user_id: str):
        request = Request(self.session, "GET", f"/api/user/{user_id}")
        response = await request.async_send()
        if response[0] != 200:
            data = json.loads(response[1])
            logging.error(f"Users.get_by_id, code: {data['code']}, message: {data['message']}")
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

    def get_by_id(self, user_id: str):
        return self.session.loop.run_until_complete(self.async_get_by_id(user_id))


@dataclass
class Map(DataNode):
    id: str = ""
    root_node_id: str = ""
    owner: str = ""
    owner_name: str = ""
    owner_avatar: str = ""
    layout: str = "LR"
    public: bool = False
    node_count: int = 0
    user_count: int = 0
    name: str = "noname"

    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)
        print(self.__dict__)
        # for kwarg in kwargs:
        #     print(kwargs)
        super().__init__()
        self.changes.clear()


class Maps:
    """
    Users - репозиторий для работы с объектами типа User.
    Основная задача - реализация CRUD методов
    """

    def __init__(self, session: Session):
        self.session = session

    async def async_create(self, *maps: typing.List[Map]):
        actions = []
        for map in maps:
            action = Action(self.session, 'POST', '/api/maps', map.changes)
            actions.append(action)
        sequence = Sequence(self.session, tuple(actions))

        response = await sequence.async_send()
        # print(response)
        if response[0] != 200:
            if response[0] != 404:
                data = json.loads(response[1])
                logging.error(f"Maps.update, code: {data['code']}, message: {data['message']}")
            else:
                logging.error(f"Maps.update, " + str(response))

    def create(self, *maps: typing.List[Map]):
        self.session.loop.run_until_complete(self.async_create(*maps))

    async def async_update(self, *maps: typing.List[Map]):
        actions = []
        for map in maps:
            if len(map.changes.keys()) > 0:
                action = Action(self.session, 'PATCH', f'/api/maps/{map.id}', map.changes)
                actions.append(action)

        if len(actions) > 0:
            sequence = Sequence(self.session, tuple(actions))
            response = await sequence.async_send()
            # print(response)
            if response[0] != 200:
                if response[0] != 404:
                    data = json.loads(response[1])
                    logging.error(f"Maps.update, code: {data['code']}, message: {data['message']}")
                else:
                    logging.error(f"Maps.update, " + str(response))

    def update(self, *maps: typing.List[Map]):
        self.session.loop.run_until_complete(self.async_update(*maps))

    async def async_get_by_id(self, map_id: str):
        request = Request(self.session, "GET", f"/api/maps/{map_id}")
        response = await request.async_send()
        if response[0] != 200:
            logging.error('Maps.get_by_id' + str(response))
            return None
        else:
            # print(response)
            args = {
                "id": "" if not ("id" in response[1]) else response[1]["id"],
                "root_node_id": "" if not ("root_node_id" in response[1]) else response[1]["root_node_id"],
                "owner": "" if not ("owner" in response[1]) else response[1]["owner"],
                "owner_name": "" if not ("owner_name" in response[1]) else response[1]["owner_name"],
                "owner_avatar": "" if not ("owner_avatar" in response[1]) else response[1]["owner_avatar"],
                "layout": "" if not ("layout" in response[1]) else response[1]["layout"],
                "public": False if not ("public" in response[1]) else response[1]["public"],
                "node_count": 0 if not ("node_count" in response[1]) else response[1]["node_count"],
                "user_count": 0 if not ("user_count" in response[1]) else response[1]["user_count"],
                "name": "" if not ("name" in response[1]) else response[1]["name"],

            }
            map = Map(**args)
            map.changes.clear()
            return map

    def get_by_id(self, map_id: str):
        return self.session.loop.run_until_complete(self.async_get_by_id(map_id))


@dataclass
class Node(DataNode):
    id: str = ""
    map_id: str = ""
    parent: str = ""
    position: list = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    access: str = ""
    originalParent: str = ""
    body: str = ''
    hidden: bool = False
    readers: list = field(default_factory=list)
    nodelevel: int = 1
    meta: dict = field(default_factory=dict)
    _properties_changes_: dict = field(default_factory=dict)

    @staticmethod
    def create(map_id: str, parent: str, properties={"global": {"title": f"{datetime.datetime.now()}"}},
               position=["R", 1]):
        args = {
            "map_id": map_id,
            "parent": parent,
            "properties": properties,
            "position": position,
        }
        return Node(**args)

    def property_get(self, group, key):
        try:

            value = self.body["properties"][group][key]
        except KeyError:
            value = None
        finally:
            return value

    def property_set(self, group, key, value):
        try:
            self.body["properties"][group][key] = value
        except KeyError:
            pass
        else:
            if not "update" in self._properties_changes_:
                self._properties_changes_["update"] = []
            self._properties_changes_["update"].append({
                "group": group,
                "key": key,
                "value": value
            })

    def property_create(self, group, key, value=""):
        pass

    def property_delete(self, group, key):
        pass


class Nodes:
    """
    Nodes - репозиторий для работы с объектами типа Node.
    Основная задача - реализация CRUD методов
    """

    def __init__(self, session: Session):
        self.session = session

    async def async_create(self, map_id: str, parent: str,
                           properties={"global": {"title": f"{datetime.datetime.now()}"}},
                           position=["R", 1]):
        data = {
            "map_id": map_id,
            "parent": parent,
            "properties": json.dumps(properties),
            "position": json.dumps(position),
        }
        action = Action(self.session, 'POST', f'/api/nodes', data)
        response = await action.async_send()

        args = dict(**json.loads(response[1]))
        node = Node(**args)
        node.changes.clear()
        return node

    def create(self, *args, **kwargs):
        return self.session.loop.run_until_complete(self.async_create(*args, **kwargs))

    async def async_update(self, *nodes: typing.List[Node]):
        actions = []
        for node in nodes:
            if len(node.changes.keys()) > 0:
                action = Action(self.session, 'PATCH', f'/api/nodes/{node.id}', node.changes)
                actions.append(action)
                pass
            if len(node._properties_changes_.keys()) > 0:
                # update
                if "update" in node._properties_changes_:
                    data = {
                        "properties": json.dumps(node._properties_changes_)
                    }
                    action = Action(self.session, 'PATCH', f'/api/nodes/{node.id}', data)
                    actions.append(action)

        if len(actions) > 0:
            sequence = Sequence(self.session, tuple(actions))
            response = await sequence.async_send()
            # print(response)
            if response[0] != 200:
                if response[0] != 404:
                    data = json.loads(response[1])
                    logging.error(f"node.update, code: {data['code']}, message: {data['message']}")
                else:
                    logging.error(f"node.update, " + str(response))

    def update(self, *nodes: typing.List[Node]):
        self.session.loop.run_until_complete(self.async_update(*nodes))

    async def async_get_by_id(self, node_id: str):
        request = Request(self.session, "GET", f"/api/nodes/{node_id}")
        response = await request.async_send()
        if response[0] != 200:
            logging.error(f'{self.__class__.__name__}.get_by_id' + str(response))
            return None
        else:

            args = dict(**response[1])
            node = Node(**args)
            node.changes.clear()
            return node

    def get_by_id(self, node_id: str):
        return self.session.loop.run_until_complete(self.async_get_by_id(node_id))
