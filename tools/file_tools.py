"""
文件操作工具 - 提供文件读写和目录列表功能
"""

import os
from .base import Tool


class ReadFileTool(Tool):
    """读取文件工具"""

    def __init__(self):
        super().__init__(
            name="read_file",
            description="读取指定文件的内容。参数：文件路径"
        )

    def run(self, file_path: str) -> str:
        """
        读取文件内容

        Args:
            file_path: 文件路径（绝对路径或相对路径）

        Returns:
            文件内容或错误信息
        """
        try:
            # 清理输入路径
            file_path = file_path.strip().strip('"').strip("'")

            # 转换为绝对路径
            abs_path = os.path.abspath(file_path)

            if not os.path.exists(abs_path):
                return f"错误：文件不存在 - {abs_path}"

            if not os.path.isfile(abs_path):
                return f"错误：路径不是文件 - {abs_path}"

            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return f"文件内容：\n```\n{content}\n```"
        except UnicodeDecodeError:
            return f"错误：文件编码无法解析，请确保文件是UTF-8编码 - {file_path}"
        except PermissionError:
            return f"错误：没有权限读取文件 - {file_path}"
        except Exception as e:
            return f"读取文件错误：{str(e)}"


class WriteFileTool(Tool):
    """写入文件工具"""

    def __init__(self):
        super().__init__(
            name="write_file",
            description="写入内容到指定文件。参数格式：文件路径|内容"
        )

    def run(self, input_str: str) -> str:
        """
        写入文件内容

        Args:
            input_str: 格式为 "文件路径|内容"

        Returns:
            写入结果或错误信息
        """
        try:
            # 分割路径和内容
            parts = input_str.split('|', 1)
            if len(parts) != 2:
                return "错误：参数格式应为 '文件路径|内容'"

            file_path = parts[0].strip().strip('"').strip("'")
            content = parts[1]

            # 转换为绝对路径
            abs_path = os.path.abspath(file_path)

            # 确保目录存在
            dir_path = os.path.dirname(abs_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"成功写入文件：{abs_path}"
        except PermissionError:
            return f"错误：没有权限写入文件 - {file_path}"
        except Exception as e:
            return f"写入文件错误：{str(e)}"


class ListFilesTool(Tool):
    """列出目录文件工具"""

    def __init__(self):
        super().__init__(
            name="list_files",
            description="列出指定目录下的文件。参数：目录路径（可选，默认为当前目录）"
        )

    def run(self, dir_path: str = ".") -> str:
        """
        列出目录内容

        Args:
            dir_path: 目录路径（默认为当前目录）

        Returns:
            目录内容列表或错误信息
        """
        try:
            # 清理输入路径
            dir_path = dir_path.strip().strip('"').strip("'") if dir_path else "."

            # 转换为绝对路径
            abs_path = os.path.abspath(dir_path)

            if not os.path.exists(abs_path):
                return f"错误：目录不存在 - {abs_path}"

            if not os.path.isdir(abs_path):
                return f"错误：路径不是目录 - {abs_path}"

            files = os.listdir(abs_path)
            if not files:
                return f"目录为空：{abs_path}"

            result = f"目录 {abs_path} 的内容：\n"
            for f in files:
                full_path = os.path.join(abs_path, f)
                ftype = "📁" if os.path.isdir(full_path) else "📄"
                result += f"{ftype} {f}\n"
            return result
        except PermissionError:
            return f"错误：没有权限访问目录 - {dir_path}"
        except Exception as e:
            return f"列出文件错误：{str(e)}"
