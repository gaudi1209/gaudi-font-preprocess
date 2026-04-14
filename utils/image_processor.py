"""图像处理模块 - 二值化、缩放、哈希计算"""
import cv2
import numpy as np
import hashlib
from PIL import Image


def load_image(filepath):
    """加载图片（支持中文路径）"""
    # 使用 numpy 读取文件，避免中文路径问题
    with open(filepath, 'rb') as f:
        img_array = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法加载图片: {filepath}")
    return img


def to_binary(img):
    """转换为二值图（黑底白字）"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 使用大津法自动阈值，THRESH_BINARY_INV 反转为黑底白字
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def resize_to_height(img, target_height=4096):
    """等比缩放到目标高度"""
    h, w = img.shape[:2]
    if h == target_height:
        return img, 1.0

    scale = target_height / h
    new_w = int(w * scale)
    resized = cv2.resize(img, (new_w, target_height), interpolation=cv2.INTER_AREA)
    return resized, scale


def compute_hash(filepath):
    """计算文件MD5哈希"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def save_image(img, filepath):
    """保存图片（支持中文路径）"""
    # 使用 imencode 避免中文路径问题
    ext = filepath.rsplit('.', 1)[-1]
    success, img_encoded = cv2.imencode(f'.{ext}', img)
    if success:
        with open(filepath, 'wb') as f:
            f.write(img_encoded.tobytes())
    else:
        raise ValueError(f"无法保存图片: {filepath}")


def get_image_info(filepath):
    """获取图片信息"""
    img = load_image(filepath)
    h, w = img.shape[:2]
    file_hash = compute_hash(filepath)
    return {
        'width': w,
        'height': h,
        'hash': file_hash,
        'filepath': filepath
    }
