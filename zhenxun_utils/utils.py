from datetime import datetime

import pypinyin


def cn2py(word: str) -> str:
    """将字符串转化为拼音

    参数:
        word: 文本
    """
    return "".join("".join(i) for i in pypinyin.pinyin(word, style=pypinyin.NORMAL))


def is_valid_date(date_text: str, separator: str = "-") -> bool:
    """日期是否合法

    参数:
        date_text: 日期
        separator: 分隔符

    返回:
        bool: 日期是否合法
    """
    try:
        datetime.strptime(date_text, f"%Y{separator}%m{separator}%d")
        return True
    except ValueError:
        return False
