"""
工具基类
"""


class Tool:
    """工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def run(self, input_str: str) -> str:
        """
        执行工具

        Args:
            input_str: 工具输入参数

        Returns:
            工具执行结果的字符串表示
        """
        raise NotImplementedError
