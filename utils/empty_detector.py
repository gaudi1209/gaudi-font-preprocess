"""空切片检测模块 - 检测切割后的图片是否有文字

算法说明：
1. 边缘腐蚀：使用形态学腐蚀去除边缘噪点
2. 文本框检测：使用轮廓检测找到文字区域
3. 文本框面积计算：计算文本框总面积占图片面积的比例
4. 阈值判断：文本框面积 < 15% 图片面积 = 空切片
"""

import cv2
import numpy as np
from typing import Tuple


def detect_empty_slice(image: np.ndarray, threshold: float = 0.15) -> Tuple[bool, float, list]:
    """
    检测图片是否为空切片（无文字）

    Args:
        image: 输入图片（二值图，黑底白字）
        threshold: 文本框面积占比阈值，低于此值视为空切片

    Returns:
        (is_empty, text_ratio, boxes)
        - is_empty: 是否为空切片
        - text_ratio: 文本框面积占比
        - boxes: 检测到的文本框列表
    """
    if image is None or image.size == 0:
        return True, 0.0, []

    # 确保是灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    height, width = gray.shape[:2]
    total_area = height * width

    # 边缘腐蚀 - 去除边缘噪点
    kernel = np.ones((3, 3), np.uint8)
    eroded = cv2.erode(gray, kernel, iterations=1)

    # 二值化（确保是黑白图）
    _, binary = cv2.threshold(eroded, 127, 255, cv2.THRESH_BINARY)

    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return True, 0.0, []

    # 过滤太小的轮廓（噪点）
    min_contour_area = total_area * 0.001  # 最小面积阈值
    valid_contours = [c for c in contours if cv2.contourArea(c) > min_contour_area]

    if not valid_contours:
        return True, 0.0, []

    # 计算文本框
    boxes = []
    text_area = 0

    for contour in valid_contours:
        x, y, w, h = cv2.boundingRect(contour)
        box_area = w * h
        boxes.append({
            'x': int(x),
            'y': int(y),
            'width': int(w),
            'height': int(h),
            'area': box_area
        })
        text_area += box_area

    # 计算文本框面积占比
    # 使用所有文本框的合并面积（简化计算，直接相加）
    text_ratio = text_area / total_area

    # 判断是否为空切片
    is_empty = text_ratio < threshold

    return is_empty, text_ratio, boxes


def get_slice_text_coverage(image: np.ndarray) -> float:
    """
    获取图片的文字覆盖率

    Args:
        image: 输入图片（二值图）

    Returns:
        文字覆盖率（0-1）
    """
    if image is None or image.size == 0:
        return 0.0

    # 确保是灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    height, width = gray.shape[:2]
    total_pixels = height * width

    # 计算白色像素（文字）数量
    white_pixels = np.sum(gray > 127)

    return white_pixels / total_pixels


def is_valid_character(image: np.ndarray, min_coverage: float = 0.02, max_coverage: float = 0.95) -> bool:
    """
    判断切片是否包含有效字符

    Args:
        image: 输入图片
        min_coverage: 最小文字覆盖率
        max_coverage: 最大文字覆盖率（排除全是白色的情况）

    Returns:
        是否包含有效字符
    """
    coverage = get_slice_text_coverage(image)
    return min_coverage <= coverage <= max_coverage
