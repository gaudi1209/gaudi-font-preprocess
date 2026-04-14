"""数据存储模块 - JSON文件存储会话数据"""
import json
import os
from typing import Dict, Any, Optional


def get_session_filepath(image_hash: str, data_dir: str) -> str:
    """获取会话文件路径"""
    return os.path.join(data_dir, f"{image_hash}.json")


def save_session(image_hash: str, data: Dict[str, Any], data_dir: str) -> bool:
    """保存会话数据"""
    filepath = get_session_filepath(image_hash, data_dir)
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存会话失败: {e}")
        return False


def load_session(image_hash: str, data_dir: str) -> Optional[Dict[str, Any]]:
    """加载会话数据"""
    filepath = get_session_filepath(image_hash, data_dir)
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载会话失败: {e}")
        return None


def delete_session(image_hash: str, data_dir: str) -> bool:
    """删除会话数据"""
    filepath = get_session_filepath(image_hash, data_dir)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        return True
    except Exception as e:
        print(f"删除会话失败: {e}")
        return False


def list_sessions(data_dir: str) -> list:
    """列出所有会话"""
    if not os.path.exists(data_dir):
        return []
    return [f[:-5] for f in os.listdir(data_dir) if f.endswith('.json')]
