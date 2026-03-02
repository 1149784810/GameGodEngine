"""
输出规范器 - 确保所有文件输出到正确的目录结构中

重构后：
1. 不再使用正则表达式解析用户请求
2. 将规范规则告知LLM，由LLM决定目录结构
3. 仅保留目录创建和路径拼接功能

项目目录结构规则：
- 游戏项目 -> projects/{GameName}/
  - docs/          # 策划文档
  - src/           # 源代码
  - assets/        # 资源文件
    - sprites/     # 精灵图
    - audio/       # 音频
    - fonts/       # 字体
  - config/        # 配置文件
  - tests/         # 测试文件
  - build/         # 构建输出

- 普通项目 -> projects/{ProjectName}/
  - docs/          # 文档
  - src/           # 源代码
  - config/        # 配置文件
  - tests/         # 测试文件
"""

import os
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ProjectType(Enum):
    """项目类型枚举"""
    GAME = "game"           # 游戏项目
    PROJECT = "project"     # 普通项目
    TEMP = "temp"           # 临时文件
    TEST = "test"           # 测试文件
    UNKNOWN = "unknown"     # 未知类型


@dataclass
class ProjectInfo:
    """项目信息"""
    project_type: ProjectType
    project_name: str
    base_dir: str
    subdirs: Dict[str, str]  # 子目录映射


class OutputNormalizer:
    """
    输出规范器 - 简化版
    
    职责：
    1. 提供当前工作区路径
    2. 根据LLM返回的目录结构创建项目
    3. 规范化文件路径
    
    注意：项目类型判断和目录结构规划交由LLM处理
    """
    
    def __init__(self, base_path: str = None):
        """
        初始化输出规范器
        
        Args:
            base_path: 基础路径，默认为当前工作目录
        """
        self.base_path = base_path or os.getcwd()
        self.current_project: Optional[ProjectInfo] = None
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """
        获取当前工作区信息，供LLM参考
        
        Returns:
            包含工作区路径和目录结构规则的字典
        """
        return {
            "current_working_directory": self.base_path,
            "projects_base_dir": os.path.join(self.base_path, "projects"),
            "directory_structure_rules": {
                "game_project": {
                    "base": "projects/{GameName}/",
                    "subdirs": {
                        "docs": "策划文档（GDD、设计文档等）",
                        "src": "源代码文件",
                        "assets": "资源文件",
                        "assets/sprites": "精灵图、图片资源",
                        "assets/audio": "音频资源",
                        "assets/fonts": "字体文件",
                        "config": "配置文件",
                        "tests": "测试文件",
                        "build": "构建输出"
                    }
                },
                "normal_project": {
                    "base": "projects/{ProjectName}/",
                    "subdirs": {
                        "docs": "文档",
                        "src": "源代码",
                        "config": "配置文件",
                        "tests": "测试文件"
                    }
                }
            },
            "file_type_mapping": {
                ".md": "docs",
                ".txt": "docs",
                ".py": "src",
                ".js": "src",
                ".ts": "src",
                ".json": "config",
                ".yaml": "config",
                ".yml": "config",
                ".png": "assets/sprites",
                ".jpg": "assets/sprites",
                ".mp3": "assets/audio",
                ".wav": "assets/audio",
                ".ttf": "assets/fonts"
            }
        }
    
    def create_project_from_llm_response(
        self, 
        project_name: str, 
        project_type: str,
        directory_structure: Optional[Dict[str, str]] = None
    ) -> ProjectInfo:
        """
        根据LLM返回的目录结构创建项目
        
        Args:
            project_name: 项目名称（由用户输入或LLM建议）
            project_type: 项目类型（"game" 或 "project"）
            directory_structure: LLM建议的目录结构（可选）
            
        Returns:
            ProjectInfo: 项目信息
        """
        # 清理项目名称
        project_name = self._sanitize_name(project_name)
        
        if project_type == "game":
            return self._create_game_project_info(project_name, directory_structure)
        else:
            return self._create_project_info(project_name, directory_structure)
    
    def _sanitize_name(self, name: str) -> str:
        """清理名称中的非法字符"""
        # 移除文件系统非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            name = name.replace(char, '')
        name = name.strip()
        # 限制长度
        if len(name) > 50:
            name = name[:50]
        return name or "Untitled"
    
    def _create_game_project_info(
        self, 
        project_name: str, 
        directory_structure: Optional[Dict[str, str]] = None
    ) -> ProjectInfo:
        """创建游戏项目信息"""
        base_dir = os.path.join(self.base_path, "projects", project_name)
        
        # 默认子目录结构
        default_subdirs = {
            "docs": os.path.join(base_dir, "docs"),
            "src": os.path.join(base_dir, "src"),
            "assets": os.path.join(base_dir, "assets"),
            "assets_sprites": os.path.join(base_dir, "assets", "sprites"),
            "assets_audio": os.path.join(base_dir, "assets", "audio"),
            "assets_fonts": os.path.join(base_dir, "assets", "fonts"),
            "config": os.path.join(base_dir, "config"),
            "tests": os.path.join(base_dir, "tests"),
            "build": os.path.join(base_dir, "build"),
        }
        
        # 如果LLM提供了自定义目录结构，可以在这里合并
        if directory_structure:
            for key, path in directory_structure.items():
                if not os.path.isabs(path):
                    path = os.path.join(base_dir, path)
                default_subdirs[key] = path
        
        return ProjectInfo(
            project_type=ProjectType.GAME,
            project_name=project_name,
            base_dir=base_dir,
            subdirs=default_subdirs
        )
    
    def _create_project_info(
        self, 
        project_name: str,
        directory_structure: Optional[Dict[str, str]] = None
    ) -> ProjectInfo:
        """创建普通项目信息"""
        base_dir = os.path.join(self.base_path, "projects", project_name)
        
        default_subdirs = {
            "docs": os.path.join(base_dir, "docs"),
            "src": os.path.join(base_dir, "src"),
            "config": os.path.join(base_dir, "config"),
            "tests": os.path.join(base_dir, "tests"),
        }
        
        if directory_structure:
            for key, path in directory_structure.items():
                if not os.path.isabs(path):
                    path = os.path.join(base_dir, path)
                default_subdirs[key] = path
        
        return ProjectInfo(
            project_type=ProjectType.PROJECT,
            project_name=project_name,
            base_dir=base_dir,
            subdirs=default_subdirs
        )
    
    def normalize_path(
        self, 
        file_path: str, 
        file_type: str = None, 
        project_info: ProjectInfo = None
    ) -> str:
        """
        规范化文件路径
        
        Args:
            file_path: 原始文件路径（可以是相对路径或仅文件名）
            file_type: 文件类型（如 'doc', 'code', 'asset', 'config'）
            project_info: 项目信息（如果为None，使用当前项目）
            
        Returns:
            str: 规范化后的完整路径
        """
        if project_info is None:
            project_info = self.current_project
        
        if project_info is None:
            # 如果没有项目信息，返回原始路径
            return file_path
        
        # 提取文件名
        file_name = os.path.basename(file_path)
        
        # 根据文件类型确定子目录
        target_dir = self._get_target_directory(file_type, file_name, project_info)
        
        # 确保目录存在
        os.makedirs(target_dir, exist_ok=True)
        
        # 返回完整路径
        return os.path.join(target_dir, file_name)
    
    def _get_target_directory(
        self, 
        file_type: str, 
        file_name: str, 
        project_info: ProjectInfo
    ) -> str:
        """根据文件类型确定目标目录"""
        
        # 如果没有指定类型，根据扩展名判断
        if file_type is None:
            file_type = self._detect_file_type(file_name)
        
        # 游戏项目特殊处理
        if project_info.project_type == ProjectType.GAME:
            return self._get_game_project_directory(file_type, project_info)
        
        # 普通项目处理
        subdir_map = {
            "doc": "docs",
            "code": "src",
            "config": "config",
            "test": "tests",
        }
        
        subdir = subdir_map.get(file_type, "")
        if subdir and subdir in project_info.subdirs:
            return project_info.subdirs[subdir]
        
        return project_info.base_dir
    
    def _get_game_project_directory(
        self, 
        file_type: str, 
        project_info: ProjectInfo
    ) -> str:
        """获取游戏项目的目录"""
        
        game_subdir_map = {
            "doc": "docs",
            "design_doc": "docs",
            "code": "src",
            "script": "src",
            "config": "config",
            "test": "tests",
            "sprite": "assets_sprites",
            "image": "assets_sprites",
            "audio": "assets_audio",
            "sound": "assets_audio",
            "music": "assets_audio",
            "font": "assets_fonts",
        }
        
        subdir = game_subdir_map.get(file_type, "")
        if subdir and subdir in project_info.subdirs:
            return project_info.subdirs[subdir]
        
        # 默认到assets
        if file_type in ["asset", "resource"]:
            return project_info.subdirs.get("assets", project_info.base_dir)
        
        return project_info.base_dir
    
    def _detect_file_type(self, file_name: str) -> str:
        """根据文件名检测文件类型"""
        ext = os.path.splitext(file_name)[1].lower()
        
        # 文档类型
        if ext in ['.md', '.txt', '.doc', '.docx', '.pdf', '.rst']:
            return "doc"
        
        # 代码类型
        if ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.swift', '.kt']:
            return "code"
        
        # 配置文件
        if ext in ['.json', '.yaml', '.yml', '.xml', '.ini', '.conf', '.toml']:
            return "config"
        
        # 图片资源
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp']:
            return "sprite"
        
        # 音频资源
        if ext in ['.mp3', '.wav', '.ogg', '.flac', '.aac']:
            return "audio"
        
        # 字体
        if ext in ['.ttf', '.otf', '.woff', '.woff2']:
            return "font"
        
        return ""
    
    def set_current_project(self, project_info: ProjectInfo):
        """设置当前项目并创建目录结构"""
        self.current_project = project_info
        
        # 创建所有必要的子目录
        os.makedirs(project_info.base_dir, exist_ok=True)
        for subdir_path in project_info.subdirs.values():
            os.makedirs(subdir_path, exist_ok=True)
    
    def get_project_summary(self) -> str:
        """获取项目摘要信息"""
        if self.current_project is None:
            return "未设置项目"
        
        info = self.current_project
        lines = [
            f"项目类型: {info.project_type.value}",
            f"项目名称: {info.project_name}",
            f"基础目录: {info.base_dir}",
            "子目录:",
        ]
        
        for name, path in info.subdirs.items():
            exists = "✓" if os.path.exists(path) else "✗"
            lines.append(f"  {exists} {name}: {path}")
        
        return "\n".join(lines)


# 便捷函数
def get_workspace_info() -> Dict[str, Any]:
    """
    获取当前工作区信息
    
    Returns:
        包含工作区路径和目录结构规则的字典
    """
    normalizer = OutputNormalizer()
    return normalizer.get_workspace_info()


def normalize_output_path(
    file_path: str, 
    project_info: ProjectInfo
) -> str:
    """
    便捷函数：规范化输出路径
    
    Args:
        file_path: 原始文件路径
        project_info: 项目信息
        
    Returns:
        str: 规范化后的路径
    """
    normalizer = OutputNormalizer()
    normalizer.set_current_project(project_info)
    return normalizer.normalize_path(file_path)
