"""
命令行执行工具 - 使用@tool装饰器实现，支持执行系统命令和PowerShell
"""

import subprocess
import os
from typing import Optional
from langchain_core.tools import tool


@tool
def execute_command(command: str, cwd: Optional[str] = None, timeout: int = 30) -> str:
    """执行系统命令行命令（CMD）。
    
    用于执行各种系统命令，如编译、运行程序、文件操作等。
    
    Args:
        command: 要执行的命令
        cwd: 工作目录（可选，默认为当前目录）
        timeout: 超时时间（秒，默认30秒）
    
    Returns:
        命令执行结果（stdout + stderr）
    
    Examples:
        execute_command("dir")  # 列出当前目录
        execute_command("python main.py", cwd="./src")  # 在src目录运行Python
        execute_command("gcc main.c -o main")  # 编译C程序
    """
    try:
        # 清理命令字符串
        command = command.strip()
        
        # 设置工作目录
        if cwd:
            cwd = os.path.abspath(cwd.strip().strip('"').strip("'"))
            if not os.path.exists(cwd):
                return f"错误：工作目录不存在 - {cwd}"
        else:
            cwd = os.getcwd()
        
        # 执行命令
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            encoding='utf-8',
            errors='replace'
        )
        
        # 构建输出
        output_parts = []
        output_parts.append(f"命令: {command}")
        output_parts.append(f"工作目录: {cwd}")
        output_parts.append(f"返回码: {result.returncode}")
        
        if result.stdout:
            output_parts.append(f"\n标准输出:\n{result.stdout}")
        
        if result.stderr:
            output_parts.append(f"\n标准错误:\n{result.stderr}")
        
        return "\n".join(output_parts)
        
    except subprocess.TimeoutExpired:
        return f"错误：命令执行超时（超过{timeout}秒）\n命令: {command}"
    except Exception as e:
        return f"执行命令错误: {str(e)}\n命令: {command}"


@tool
def execute_powershell(script: str, cwd: Optional[str] = None, timeout: int = 30) -> str:
    """执行PowerShell脚本或命令。
    
    用于执行PowerShell命令，支持更强大的Windows系统管理能力。
    
    Args:
        script: PowerShell脚本或命令
        cwd: 工作目录（可选，默认为当前目录）
        timeout: 超时时间（秒，默认30秒）
    
    Returns:
        脚本执行结果
    
    Examples:
        execute_powershell("Get-Process")  # 获取进程列表
        execute_powershell("Get-ChildItem -Recurse")  # 递归列出文件
        execute_powershell("python main.py", cwd="./src")  # 在src目录运行
    """
    try:
        # 清理脚本字符串
        script = script.strip()
        
        # 设置工作目录
        if cwd:
            cwd = os.path.abspath(cwd.strip().strip('"').strip("'"))
            if not os.path.exists(cwd):
                return f"错误：工作目录不存在 - {cwd}"
        else:
            cwd = os.getcwd()
        
        # 构建PowerShell命令
        # 使用 -Command 参数执行命令
        ps_command = [
            "powershell.exe",
            "-NoProfile",  # 不加载配置文件，加快启动
            "-ExecutionPolicy", "Bypass",  # 绕过执行策略限制
            "-Command", script
        ]
        
        # 执行PowerShell
        result = subprocess.run(
            ps_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            encoding='utf-8',
            errors='replace'
        )
        
        # 构建输出
        output_parts = []
        output_parts.append(f"PowerShell命令: {script}")
        output_parts.append(f"工作目录: {cwd}")
        output_parts.append(f"返回码: {result.returncode}")
        
        if result.stdout:
            output_parts.append(f"\n标准输出:\n{result.stdout}")
        
        if result.stderr:
            output_parts.append(f"\n标准错误:\n{result.stderr}")
        
        return "\n".join(output_parts)
        
    except subprocess.TimeoutExpired:
        return f"错误：PowerShell执行超时（超过{timeout}秒）\n脚本: {script}"
    except FileNotFoundError:
        return f"错误：PowerShell未找到。请确保系统中已安装PowerShell。"
    except Exception as e:
        return f"执行PowerShell错误: {str(e)}\n脚本: {script}"


@tool
def run_python_script(script_path: str, args: Optional[str] = None, cwd: Optional[str] = None, timeout: int = 30) -> str:
    """运行Python脚本。
    
    专门用于执行Python脚本，会自动检测Python解释器。
    
    Args:
        script_path: Python脚本路径
        args: 传递给脚本的参数（可选）
        cwd: 工作目录（可选）
        timeout: 超时时间（秒，默认30秒）
    
    Returns:
        脚本执行结果
    
    Examples:
        run_python_script("main.py")  # 运行main.py
        run_python_script("test.py", "--verbose")  # 带参数运行
        run_python_script("src/main.py", cwd="./project")  # 指定工作目录
    """
    try:
        # 清理路径
        script_path = script_path.strip().strip('"').strip("'")
        abs_script_path = os.path.abspath(script_path)
        
        if not os.path.exists(abs_script_path):
            return f"错误：脚本文件不存在 - {abs_script_path}"
        
        # 设置工作目录
        if cwd:
            cwd = os.path.abspath(cwd.strip().strip('"').strip("'"))
            if not os.path.exists(cwd):
                return f"错误：工作目录不存在 - {cwd}"
        else:
            cwd = os.path.dirname(abs_script_path) or os.getcwd()
        
        # 构建命令
        python_cmd = "python"
        command = f"{python_cmd} \"{abs_script_path}\""
        if args:
            command += f" {args}"
        
        # 执行
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            encoding='utf-8',
            errors='replace'
        )
        
        # 构建输出
        output_parts = []
        output_parts.append(f"Python脚本: {abs_script_path}")
        output_parts.append(f"工作目录: {cwd}")
        output_parts.append(f"返回码: {result.returncode}")
        
        if result.stdout:
            output_parts.append(f"\n输出:\n{result.stdout}")
        
        if result.stderr:
            output_parts.append(f"\n错误:\n{result.stderr}")
        
        return "\n".join(output_parts)
        
    except subprocess.TimeoutExpired:
        return f"错误：Python脚本执行超时（超过{timeout}秒）\n脚本: {script_path}"
    except Exception as e:
        return f"运行Python脚本错误: {str(e)}\n脚本: {script_path}"


# 工具列表，方便导入
shell_tools = [execute_command, execute_powershell, run_python_script]
