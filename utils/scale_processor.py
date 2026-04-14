"""缩放校正处理模块 - 字符标准化处理

功能：
1. 检测字符边框（边缘腐蚀 + 轮廓检测）
2. 字符居中（上下黑边相等，左右黑边相等）
3. 字符缩放（按比例放大）
4. 输出标准化（512x512）
"""

import cv2
import numpy as np
import os
from typing import Tuple, Optional


def detect_char_bbox(image: np.ndarray) -> Tuple[int, int, int, int]:
    """
    检测字符的边界框

    Args:
        image: 输入图片（二值图，黑底白字）

    Returns:
        (x, y, width, height) 字符边界框
    """
    if image is None or image.size == 0:
        return 0, 0, 0, 0

    # 确保是灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 边缘腐蚀 - 去除边缘噪点
    kernel = np.ones((3, 3), np.uint8)
    eroded = cv2.erode(gray, kernel, iterations=1)

    # 二值化
    _, binary = cv2.threshold(eroded, 127, 255, cv2.THRESH_BINARY)

    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return 0, 0, gray.shape[1], gray.shape[0]

    # 计算所有轮廓的联合边界框
    all_points = np.vstack(contours)
    x, y, w, h = cv2.boundingRect(all_points)

    return x, y, w, h


def center_char_in_canvas(
    image: np.ndarray,
    target_size: int = 512,
    align: str = 'center',
    background: str = 'black'
) -> np.ndarray:
    """
    将字符居中放置在指定尺寸的画布中

    Args:
        image: 输入图片（二值图，黑底白字）
        target_size: 目标尺寸（正方形）
        align: 对齐方式 ('center', 'top', 'baseline')
        background: 背景方式 ('black', 'transparent')

    Returns:
        处理后的图片
    """
    if image is None or image.size == 0:
        # 返回空画布
        if background == 'transparent':
            return np.zeros((target_size, target_size, 4), dtype=np.uint8)
        else:
            return np.zeros((target_size, target_size), dtype=np.uint8)

    # 确保是灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 检测字符边界框
    x, y, w, h = detect_char_bbox(gray)

    if w == 0 or h == 0:
        # 没有检测到字符，返回空画布
        if background == 'transparent':
            return np.zeros((target_size, target_size, 4), dtype=np.uint8)
        else:
            return np.zeros((target_size, target_size), dtype=np.uint8)

    # 裁剪字符区域
    char_region = gray[y:y+h, x:x+w]

    # 创建目标画布
    if background == 'transparent':
        canvas = np.zeros((target_size, target_size, 4), dtype=np.uint8)
        is_rgba = True
    else:
        canvas = np.zeros((target_size, target_size), dtype=np.uint8)
        is_rgba = False

    # 计算放置位置（居中）
    # 上下黑边相等，左右黑边相等
    left_padding = (target_size - w) // 2
    top_padding = (target_size - h) // 2

    # 根据对齐方式调整
    if align == 'top':
        top_padding = 10  # 顶部留少量边距
    elif align == 'baseline':
        # 基线对齐：底部对齐
        top_padding = target_size - h - 10

    # 确保不越界
    right_padding = target_size - left_padding - w
    bottom_padding = target_size - top_padding - h

    if left_padding < 0:
        left_padding = 0
    if top_padding < 0:
        top_padding = 0

    # 放置字符到画布
    end_x = min(left_padding + w, target_size)
    end_y = min(top_padding + h, target_size)

    char_w = end_x - left_padding
    char_h = end_y - top_padding

    if is_rgba:
        # 透明背景：将白色字符复制到 RGBA
        canvas[top_padding:end_y, left_padding:end_x, 0] = char_region[:char_h, :char_w]
        canvas[top_padding:end_y, left_padding:end_x, 1] = char_region[:char_h, :char_w]
        canvas[top_padding:end_y, left_padding:end_x, 2] = char_region[:char_h, :char_w]
        # Alpha 通道：白色部分不透明，黑色部分透明
        _, alpha = cv2.threshold(char_region[:char_h, :char_w], 127, 255, cv2.THRESH_BINARY)
        canvas[top_padding:end_y, left_padding:end_x, 3] = alpha
    else:
        canvas[top_padding:end_y, left_padding:end_x] = char_region[:char_h, :char_w]

    return canvas


def scale_char(
    image: np.ndarray,
    scale: float = 1.15,
    target_size: int = 512,
    align: str = 'center',
    background: str = 'black'
) -> np.ndarray:
    """
    缩放字符并输出标准化尺寸

    Args:
        image: 输入图片
        scale: 缩放比例 (1.0 - 2.0)
        target_size: 目标尺寸
        align: 对齐方式
        background: 背景方式

    Returns:
        处理后的图片
    """
    if image is None or image.size == 0:
        return center_char_in_canvas(image, target_size, align, background)

    # 确保是灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 检测字符边界框
    x, y, w, h = detect_char_bbox(gray)

    if w == 0 or h == 0:
        return center_char_in_canvas(None, target_size, align, background)

    # 裁剪字符区域
    char_region = gray[y:y+h, x:x+w]

    # 计算缩放后的尺寸
    # 目标：放大后仍能放入 target_size
    max_char_size = int(target_size * 0.9)  # 留10%边距

    # 先按比例缩放
    new_w = int(w * scale)
    new_h = int(h * scale)

    # 如果缩放后超过最大尺寸，按最大尺寸等比缩放
    if new_w > max_char_size or new_h > max_char_size:
        ratio = min(max_char_size / new_w, max_char_size / new_h)
        new_w = int(new_w * ratio)
        new_h = int(new_h * ratio)

    # 缩放字符
    if new_w > 0 and new_h > 0:
        scaled_char = cv2.resize(char_region, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    else:
        scaled_char = char_region

    # 创建目标画布
    if background == 'transparent':
        canvas = np.zeros((target_size, target_size, 4), dtype=np.uint8)
        is_rgba = True
    else:
        canvas = np.zeros((target_size, target_size), dtype=np.uint8)
        is_rgba = False

    # 计算放置位置（居中）
    left_padding = (target_size - new_w) // 2
    top_padding = (target_size - new_h) // 2

    # 根据对齐方式调整
    if align == 'top':
        top_padding = max(5, int(target_size * 0.02))
    elif align == 'baseline':
        top_padding = target_size - new_h - max(5, int(target_size * 0.02))

    # 确保不越界
    left_padding = max(0, left_padding)
    top_padding = max(0, top_padding)

    end_x = min(left_padding + new_w, target_size)
    end_y = min(top_padding + new_h, target_size)

    char_w = end_x - left_padding
    char_h = end_y - top_padding

    if is_rgba:
        # 透明背景
        canvas[top_padding:end_y, left_padding:end_x, 0] = scaled_char[:char_h, :char_w]
        canvas[top_padding:end_y, left_padding:end_x, 1] = scaled_char[:char_h, :char_w]
        canvas[top_padding:end_y, left_padding:end_x, 2] = scaled_char[:char_h, :char_w]
        _, alpha = cv2.threshold(scaled_char[:char_h, :char_w], 127, 255, cv2.THRESH_BINARY)
        canvas[top_padding:end_y, left_padding:end_x, 3] = alpha
    else:
        canvas[top_padding:end_y, left_padding:end_x] = scaled_char[:char_h, :char_w]

    return canvas


def process_character(
    image_path: str,
    output_path: str,
    scale: float = 1.15,
    target_size: int = 512,
    align: str = 'center',
    background: str = 'black'
) -> bool:
    """
    处理单个字符图片

    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        scale: 缩放比例
        target_size: 目标尺寸
        align: 对齐方式
        background: 背景方式

    Returns:
        是否成功
    """
    try:
        # 读取图片
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return False

        # 处理
        result = scale_char(image, scale, target_size, align, background)

        # 保存
        if background == 'transparent':
            cv2.imwrite(output_path, result)
        else:
            cv2.imwrite(output_path, result)

        return True
    except Exception as e:
        print(f"处理字符失败: {e}")
        return False


def apply_adjustments(
    image: np.ndarray,
    adjust_top: int = 0,
    adjust_bottom: int = 0,
    adjust_left: int = 0,
    adjust_right: int = 0
) -> np.ndarray:
    """
    应用调整值裁剪图片

    Args:
        image: 输入图片
        adjust_top: 上边距调整
        adjust_bottom: 下边距调整
        adjust_left: 左边距调整
        adjust_right: 右边距调整

    Returns:
        裁剪后的图片
    """
    if image is None or image.size == 0:
        return image

    # 确保所有参数都是整数
    adjust_top = int(adjust_top or 0)
    adjust_bottom = int(adjust_bottom or 0)
    adjust_left = int(adjust_left or 0)
    adjust_right = int(adjust_right or 0)

    h, w = image.shape[:2]

    # 计算裁剪区域
    y1 = adjust_top
    y2 = h - adjust_bottom
    x1 = adjust_left
    x2 = w - adjust_right

    # 确保不越界
    y1 = max(0, y1)
    y2 = min(h, y2)
    x1 = max(0, x1)
    x2 = min(w, x2)

    if y2 <= y1 or x2 <= x1:
        return image

    return image[y1:y2, x1:x2]


def process_character_with_adjust(
    image_path: str,
    output_path: str,
    adjust_top: int = 0,
    adjust_bottom: int = 0,
    adjust_left: int = 0,
    adjust_right: int = 0,
    scale: float = 1.15,
    target_size: int = 512,
    align: str = 'center',
    background: str = 'black'
) -> bool:
    """
    处理单个字符图片（带调整值）

    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        adjust_top/bottom/left/right: 调整值
        scale: 缩放比例
        target_size: 目标尺寸
        align: 对齐方式
        background: 背景方式

    Returns:
        是否成功
    """
    try:
        # 读取图片
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return False

        # 应用调整值
        adjusted = apply_adjustments(
            image, adjust_top, adjust_bottom, adjust_left, adjust_right
        )

        # 处理
        result = scale_char(adjusted, scale, target_size, align, background)

        # 保存
        cv2.imwrite(output_path, result)

        return True
    except Exception as e:
        print(f"处理字符失败: {e}")
        return False
