from collections.abc import Awaitable, Callable
from typing import Literal

import httpx
import nonebot
from nonebot import logger
from nonebot.adapters import Bot
from nonebot.utils import is_coroutine_callable
from nonebot_plugin_alconna.uniseg import Target, UniMessage
from nonebot_plugin_uninfo import Uninfo, get_interface
from pydantic import BaseModel

from .http_utils import AsyncHttpx
from .message import MessageUtils

driver = nonebot.get_driver()


class UserData(BaseModel):
    name: str
    """昵称"""
    card: str | None = None
    """名片/备注"""
    user_id: str
    """用户id"""
    group_id: str | None = None
    """群组id"""
    role: str | None = None
    """角色"""
    avatar_url: str | None = None
    """头像url"""
    join_time: int | None = None
    """加入时间"""


class PlatformUtils:

    @classmethod
    async def get_user_avatar(
        cls, user_id: str, platform: str, appid: str | None = None
    ) -> bytes | None:
        """快捷获取用户头像

        参数:
            user_id: 用户id
            platform: 平台
        """
        url = None
        if platform == "qq":
            if user_id.isdigit():
                url = f"http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=160"
            else:
                url = f"https://q.qlogo.cn/qqapp/{appid}/{user_id}/100"
        return await AsyncHttpx.get_content(url) if url else None

    @classmethod
    def get_user_avatar_url(
        cls, user_id: str, platform: str, appid: str | None = None
    ) -> str | None:
        """快捷获取用户头像url

        参数:
            user_id: 用户id
            platform: 平台
        """
        if platform == "qq":
            return (
                f"http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=160"
                if user_id.isdigit()
                else f"https://q.qlogo.cn/qqapp/{appid}/{user_id}/100"
            )
        else:
            return None

    @classmethod
    async def get_group_avatar(cls, gid: str, platform: str) -> bytes | None:
        """快捷获取用群头像

        参数:
            gid: 群组id
            platform: 平台
        """
        if platform == "qq":
            url = f"http://p.qlogo.cn/gh/{gid}/{gid}/640/"
            async with httpx.AsyncClient() as client:
                for _ in range(3):
                    try:
                        return (await client.get(url)).content
                    except Exception:
                        logger.error("获取群头像错误", "Util")
        return None

    @classmethod
    def get_platform(cls, t: Bot | Uninfo) -> str:
        """获取平台

        参数:
            bot: Bot

        返回:
            str | None: 平台
        """
        if isinstance(t, Bot):
            if interface := get_interface(t):
                info = interface.basic_info()
                platform = info["scope"].lower()
                return "qq" if platform.startswith("qq") else platform
        else:
            platform = t.basic["scope"].lower()
            return "qq" if platform.startswith("qq") else platform
        return "unknown"

    @classmethod
    def get_target(
        cls,
        bot: Bot,
        user_id: str | None = None,
        group_id: str | None = None,
        channel_id: str | None = None,
    ):
        """获取发生Target

        参数:
            bot: Bot
            user_id: 用户id
            group_id: 频道id或群组id
            channel_id: 频道id

        返回:
            target: 对应平台Target
        """
        target = None
        platform = cls.get_platform(bot)
        if platform == "qq":
            if group_id:
                target = Target(group_id)
            elif user_id:
                target = Target(user_id, private=True)
        elif platform in ["kaiheila", "kook", "dodo"]:
            if group_id and channel_id:
                target = Target(channel_id, parent_id=group_id, channel=True)
            elif user_id:
                target = Target(user_id, private=True)
        return target


async def broadcast_group(
    message: str | UniMessage,
    bot: Bot | list[Bot] | None = None,
    bot_id: str | set[str] | None = None,
    ignore_group: set[int] | None = None,
    check_func: Callable[[Bot, str], Awaitable] | None = None,
    log_cmd: str | None = None,
    platform: Literal["qq", "dodo", "kaiheila"] | None = None,
):
    """获取所有Bot或指定Bot对象广播群聊

    参数:
        message: 广播消息内容
        bot: 指定bot对象.
        bot_id: 指定bot id.
        ignore_group: 忽略群聊列表.
        check_func: 发送前对群聊检测方法，判断是否发送.
        log_cmd: 日志标记.
        platform: 指定平台
    """
    if platform and platform not in ["qq", "dodo", "kaiheila"]:
        raise ValueError("指定平台不支持")
    if not message:
        raise ValueError("群聊广播消息不能为空")
    bot_dict = nonebot.get_bots()
    bot_list: list[Bot] = []
    if bot:
        if isinstance(bot, list):
            bot_list = bot
        else:
            bot_list.append(bot)
    elif bot_id:
        _bot_id_list = bot_id
        if isinstance(bot_id, str):
            _bot_id_list = [bot_id]
        for id_ in _bot_id_list:
            if bot_id in bot_dict:
                bot_list.append(bot_dict[bot_id])
            else:
                logger.warning(f"Bot:{id_} 对象未连接或不存在")
    else:
        bot_list = list(bot_dict.values())
    _used_group = []
    for _bot in bot_list:
        try:
            if platform and platform != PlatformUtils.get_platform(_bot):
                continue
            if not (interface := get_interface(_bot)):
                continue
            scenes = await interface.get_scenes()
            if group_list := [s for s in scenes if s.is_group or s.is_channel]:
                for group in group_list:
                    group_id = group.id
                    channel_id = None
                    if group.is_channel and group.parent:
                        group_id = group.parent.id
                        channel_id = group.id
                    key = f"{group_id}:{channel_id}"
                    try:
                        if (
                            ignore_group
                            and (group_id in ignore_group or channel_id in ignore_group)
                        ) or key in _used_group:
                            logger.debug(
                                f"群组: {group_id}:{channel_id} | {log_cmd} 广播方法群组重复, 已跳过..."
                            )
                            continue
                        is_run = False
                        if check_func:
                            if is_coroutine_callable(check_func):
                                is_run = await check_func(_bot, group_id)
                            else:
                                is_run = check_func(_bot, group_id)
                        if not is_run:
                            logger.debug(
                                f"群组: {group_id}:{channel_id} | {log_cmd} 广播方法检测运行方法为 False, 已跳过...",
                            )
                            continue
                        if target := PlatformUtils.get_target(
                            _bot, None, group_id, channel_id
                        ):
                            _used_group.append(key)
                            message_list = message
                            await MessageUtils.build_message(message_list).send(
                                target, _bot
                            )
                            logger.debug(
                                f"群组: {group_id}:{channel_id} | {log_cmd} 发送成功"
                            )
                        else:
                            logger.warning(
                                f"群组: {group_id}:{channel_id} | {log_cmd} target为空"
                            )
                    except Exception as e:
                        logger.error(
                            f"群组: {group_id}:{channel_id} | {log_cmd} 发送失败 {type(e)}:{e}"
                        )
        except Exception as e:
            logger.error(
                f"Bot: {_bot.self_id} | {log_cmd} 获取群聊列表失败 {type(e)}:{e}"
            )
