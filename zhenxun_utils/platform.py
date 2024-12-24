import httpx
import nonebot
from nonebot import require
from nonebot.adapters import Bot

require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")

from nonebot_plugin_alconna.uniseg import Receipt, Target, UniMessage
from nonebot_plugin_uninfo import SceneType, Uninfo, get_interface
from nonebot_plugin_uninfo.model import Member
from pydantic import BaseModel

from .http_utils import AsyncHttpx
from .log import logger
from .message import MessageUtils

driver = nonebot.get_driver()


class UserData(BaseModel):
    name: str | None
    """昵称"""
    card: str | None = None
    """名片/备注"""
    user_id: str
    """用户id"""
    group_id: str | None = None
    """群组id"""
    channel_id: str | None = None
    """频道id"""
    role: str | None = None
    """角色"""
    avatar_url: str | None = None
    """头像url"""
    join_time: int | None = None
    """加入时间"""


class GroupData(BaseModel):
    group_id: str
    """群组id"""
    group_name: str | None
    """群组名称"""
    channel_id: str | None = None
    """频道id"""


class PlatformUtils:
    @classmethod
    async def ban_user(cls, bot: Bot, user_id: str, group_id: str, duration: int):
        """禁言

        参数:
            bot: Bot
            user_id: 用户id
            group_id: 群组id
            duration: 禁言时长(分钟)
        """
        if cls.get_platform(bot) == "qq":
            await bot.set_group_ban(
                group_id=int(group_id),
                user_id=int(user_id),
                duration=duration * 60,
            )

    @classmethod
    async def get_group_member_list(cls, bot: Bot, group_id: str) -> list[UserData]:
        """获取群组/频道成员列表

        参数:
            bot: Bot
            group_id: 群组/频道id

        返回:
            list[UserData]: 用户数据列表
        """
        if interface := get_interface(bot):
            members: list[Member] = await interface.get_members(
                SceneType.GROUP, group_id
            )
            return [
                UserData(
                    name=member.user.name or "",
                    card=member.nick,
                    user_id=member.user.id,
                    group_id=group_id,
                    role=member.role.id if member.role else "",
                    avatar_url=member.user.avatar,
                    join_time=int(member.joined_at.timestamp())
                    if member.joined_at
                    else None,
                )
                for member in members
            ]
        return []

    @classmethod
    async def get_friend_list(cls, bot: Bot) -> tuple[list[UserData], str]:
        """获取好友列表

        参数:
            bot: Bot

        返回:
            list[FriendUser]: 好友列表
        """
        if interface := get_interface(bot):
            user_list = await interface.get_users()
            return [
                UserData(user_id=u.id, name=u.name) for u in user_list
            ], cls.get_platform(bot)
        return [], ""

    @classmethod
    async def get_group_list(
        cls, bot: Bot, only_group: bool = False
    ) -> tuple[list[GroupData], str]:
        """获取群组列表

        参数:
            bot: Bot
            only_group: 是否只获取群组（不获取channel）

        返回:
            tuple[list[GroupConsole], str]: 群组列表, 平台
        """
        if not (interface := get_interface(bot)):
            return [], ""
        platform = cls.get_platform(bot)
        result_list = []
        scenes = await interface.get_scenes(SceneType.GROUP)
        for scene in scenes:
            group_id = scene.id
            result_list.append(
                GroupData(
                    group_id=scene.id,
                    group_name=scene.name,
                )
            )
            if not only_group and platform != "qq":
                if channel_list := await interface.get_scenes(parent_scene_id=group_id):
                    result_list.extend(
                        GroupData(
                            group_id=scene.id,
                            group_name=channel.name,
                            channel_id=channel.id,
                        )
                        for channel in channel_list
                    )
        return result_list, platform

    @classmethod
    async def get_user(
        cls,
        bot: Bot,
        user_id: str,
        group_id: str | None = None,
        channel_id: str | None = None,
    ) -> UserData | None:
        """获取用户信息

        参数:
            bot: Bot
            user_id: 用户id
            group_id: 群组id.
            channel_id: 频道id.

        返回:
            UserData | None: 用户数据
        """
        if not (interface := get_interface(bot)):
            return None
        member = None
        user = None
        if channel_id:
            member = await interface.get_member(
                SceneType.CHANNEL_TEXT, channel_id, user_id
            )
            if member:
                user = member.user
        elif group_id:
            member = await interface.get_member(SceneType.GROUP, group_id, user_id)
            if member:
                user = member.user
        else:
            user = await interface.get_user(user_id)
        if not user:
            return None
        return (
            UserData(
                name=user.name or "",
                card=member.nick,
                user_id=user.id,
                group_id=group_id,
                channel_id=channel_id,
                role=member.role.id if member.role else None,
                join_time=(
                    int(member.joined_at.timestamp()) if member.joined_at else None
                ),
            )
            if member
            else UserData(
                name=user.name or "",
                user_id=user.id,
                group_id=group_id,
                channel_id=channel_id,
            )
        )

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
                        logger.error(
                            "获取群头像错误", "Util", target=gid, platform=platform
                        )
        return None

    @classmethod
    async def send_message(
        cls,
        bot: Bot,
        user_id: str | None,
        group_id: str | None,
        message: str | UniMessage,
    ) -> Receipt | None:
        """发送消息

        参数:
            bot: Bot
            user_id: 用户id
            group_id: 群组id或频道id
            message: 消息文本

        返回:
            Receipt | None: 是否发送成功
        """
        if target := cls.get_target(user_id=user_id, group_id=group_id):
            send_message = (
                MessageUtils.build_message(message)
                if isinstance(message, str)
                else message
            )
            return await send_message.send(target=target, bot=bot)
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
        *,
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
        if group_id and channel_id:
            target = Target(channel_id, parent_id=group_id, channel=True)
        elif group_id:
            target = Target(group_id)
        elif user_id:
            target = Target(user_id, private=True)
        return target
