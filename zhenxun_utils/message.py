from io import BytesIO
from pathlib import Path
from typing import Any

import nonebot
from nonebot import logger
from nonebot_plugin_alconna import (
    At,
    AtAll,
    CustomNode,
    Image,
    Reference,
    Text,
    UniMessage,
    Video,
    Voice,
)

from ._build_image import BuildImage

driver = nonebot.get_driver()

MESSAGE_TYPE = (
    str
    | int
    | float
    | Path
    | bytes
    | BytesIO
    | BuildImage
    | At
    | AtAll
    | Image
    | Text
    | Voice
    | Video
)


class MessageUtils:
    @classmethod
    def __build_message(cls, msg_list: list[MESSAGE_TYPE]) -> list[Text | Image]:
        """构造消息

        参数:
            msg_list: 消息列表

        返回:
            list[Text | Text]: 构造完成的消息列表
        """
        message_list = []
        for msg in msg_list:
            if isinstance(msg, Image | Text | At | AtAll | Video | Voice):
                message_list.append(msg)
            elif isinstance(msg, str | int | float):
                message_list.append(Text(str(msg)))
            elif isinstance(msg, Path):
                if msg.exists():
                    image = BuildImage.open(msg)
                    message_list.append(Image(raw=image.pic2bytes()))
                else:
                    logger.warning(f"图片路径不存在: {msg}")
            elif isinstance(msg, bytes):
                message_list.append(Image(raw=msg))
            elif isinstance(msg, BytesIO):
                message_list.append(Image(raw=msg))
            elif isinstance(msg, BuildImage):
                message_list.append(Image(raw=msg.pic2bytes()))
        return message_list

    @classmethod
    def build_message(
        cls, msg_list: MESSAGE_TYPE | list[MESSAGE_TYPE | list[MESSAGE_TYPE]]
    ) -> UniMessage:
        """构造消息

        参数:
            msg_list: 消息列表

        返回:
            UniMessage: 构造完成的消息列表
        """
        message_list = []
        if not isinstance(msg_list, list):
            msg_list = [msg_list]
        for m in msg_list:
            _data = m if isinstance(m, list) else [m]
            message_list += cls.__build_message(_data)  # type: ignore
        return UniMessage(message_list)

    @classmethod
    def alc_forward_msg(
        cls,
        msg_list: list,
        uin: str,
        name: str,
    ) -> UniMessage:
        """生成自定义合并消息

        参数:
            msg_list: 消息列表
            uin: 发送者 QQ
            name: 自定义名称

        返回:
            list[dict]: 转发消息
        """
        node_list = []
        for _message in msg_list:
            if isinstance(_message, list):
                for i in range(len(_message.copy())):
                    if isinstance(_message[i], Path):
                        _message[i] = Image(
                            raw=BuildImage.open(_message[i]).pic2bytes()
                        )
                    elif isinstance(_message[i], BuildImage):
                        _message[i] = Image(raw=_message[i].pic2bytes())
            node_list.append(
                CustomNode(uid=uin, name=name, content=UniMessage(_message))
            )
        return UniMessage(Reference(nodes=node_list))

    @classmethod
    def custom_forward_msg(
        cls,
        msg_list: list[Any],
        uin: str,
        name: str,
    ) -> list[dict]:
        """生成自定义合并消息

        参数:
            msg_list: 消息列表
            uin: 发送者 QQ
            name: 自定义名称

        返回:
            list[dict]: 转发消息
        """
        mes_list = []
        for _message in msg_list:
            data = {
                "type": "node",
                "data": {
                    "name": name,
                    "uin": f"{uin}",
                    "content": _message,
                },
            }
            mes_list.append(data)
        return mes_list
