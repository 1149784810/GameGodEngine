"""
文件操作工具 - 使用@tool装饰器实现，支持Function Calling
"""

import os
from langchain_core.tools import tool


@tool
def read_file(file_path: str) -> str:
    """读取指定文件的内容。

    Args:
        file_path: 文件路径（绝对路径或相对路径）

    Returns:
        文件内容或错误信息
    """
    try:
        file_path = file_path.strip().strip('"').strip("'")
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


@tool
def write_file(file_path: str, content: str) -> str:
    """写入内容到指定文件。

    Args:
        file_path: 目标文件路径
        content: 要写入的文件内容

    Returns:
        写入结果
    """
    try:
        file_path = file_path.strip().strip('"').strip("'")
        abs_path = os.path.abspath(file_path)

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


@tool
def list_files(dir_path: str = ".") -> str:
    """列出指定目录下的文件和文件夹。

    Args:
        dir_path: 目录路径（默认为当前目录）

    Returns:
        目录内容列表
    """
    try:
        dir_path = dir_path.strip().strip('"').strip("'") if dir_path else "."
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


# 工具列表，方便导入
file_tools = [read_file, write_file, list_files]
