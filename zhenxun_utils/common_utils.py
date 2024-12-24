from typing import overload


class CommonUtils:
    @staticmethod
    def format(name: str) -> str:
        return f"<{name},"

    @overload
    @classmethod
    def convert_module_format(cls, data: str) -> list[str]: ...

    @overload
    @classmethod
    def convert_module_format(cls, data: list[str]) -> str: ...

    @classmethod
    def convert_module_format(cls, data: str | list[str]) -> str | list[str]:
        """
        在 `<aaa,<bbb,<ccc,` 和 `["aaa", "bbb", "ccc"]` 之间进行相互转换。

        参数:
            data (str | list[str]): 输入数据，可能是格式化字符串或字符串列表。

        返回:
            str | list[str]: 根据输入类型返回转换后的数据。
        """
        if isinstance(data, str):
            return [item.strip(",") for item in data.split("<") if item]
        elif isinstance(data, list):
            return "".join(cls.format(item) for item in data)
