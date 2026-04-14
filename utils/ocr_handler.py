"""文本框检测模块 - 使用 OpenCV 轮廓检测"""
import cv2
import numpy as np


def detect_text_boxes(img, min_area=100, max_area_ratio=0.3):
    """
    使用 OpenCV 轮廓检测识别文本框
    对于书法图片，这种方法比 OCR 更准确

    参数：
        img: 二值图（黑底白字）
        min_area: 最小文本框面积
        max_area_ratio: 最大文本框占图片面积的比例

    返回: list of dict, 每个包含 {x_min, x_max, y_min, y_max, width, height, center_x, center_y}
    """
    # 确保是二值图
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # 膨胀操作，连接相邻的文字部分
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(gray, kernel, iterations=1)

    # 查找轮廓
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    img_area = gray.shape[0] * gray.shape[1]
    max_area = img_area * max_area_ratio

    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h

        # 过滤过大或过小的框
        if area < min_area or area > max_area:
            continue

        # 过滤太扁或太窄的框（不是正常的字）
        aspect_ratio = w / h if h > 0 else 0
        if aspect_ratio > 5 or aspect_ratio < 0.1:
            continue

        box_info = {
            'x_min': int(x),
            'x_max': int(x + w),
            'y_min': int(y),
            'y_max': int(y + h),
            'width': int(w),
            'height': int(h),
            'center_x': int(x + w / 2),
            'center_y': int(y + h / 2),
            'area': int(area)
        }
        boxes.append(box_info)

    return boxes


def filter_boxes_by_size(boxes, min_width=10, min_height=10, max_width_ratio=0.5, max_height_ratio=0.5, img_width=1, img_height=1):
    """按尺寸过滤文本框"""
    filtered = []
    for box in boxes:
        if box['width'] < min_width or box['height'] < min_height:
            continue
        if box['width'] > img_width * max_width_ratio:
            continue
        if box['height'] > img_height * max_height_ratio:
            continue
        filtered.append(box)
    return filtered


def merge_overlapping_boxes(boxes, overlap_threshold=0.5):
    """合并重叠的文本框"""
    if not boxes:
        return []

    # 按 x_min 排序
    sorted_boxes = sorted(boxes, key=lambda b: (b['x_min'], b['y_min']))

    merged = []
    used = set()

    for i, box in enumerate(sorted_boxes):
        if i in used:
            continue

        current = box.copy()
        used.add(i)

        # 查找重叠的框
        for j, other in enumerate(sorted_boxes):
            if j in used:
                continue

            # 计算重叠
            x_overlap = max(0, min(current['x_max'], other['x_max']) - max(current['x_min'], other['x_min']))
            y_overlap = max(0, min(current['y_max'], other['y_max']) - max(current['y_min'], other['y_min']))

            overlap_area = x_overlap * y_overlap
            smaller_area = min(current['width'] * current['height'], other['width'] * other['height'])

            if smaller_area > 0 and overlap_area / smaller_area > overlap_threshold:
                # 合并
                current['x_min'] = min(current['x_min'], other['x_min'])
                current['x_max'] = max(current['x_max'], other['x_max'])
                current['y_min'] = min(current['y_min'], other['y_min'])
                current['y_max'] = max(current['y_max'], other['y_max'])
                current['width'] = current['x_max'] - current['x_min']
                current['height'] = current['y_max'] - current['y_min']
                current['center_x'] = (current['x_min'] + current['x_max']) // 2
                current['center_y'] = (current['y_min'] + current['y_max']) // 2
                used.add(j)

        merged.append(current)

    return merged
