"""切割线分析模块 - 根据文本框计算切割线

算法说明：
1. 竖向切割：计算文本框横向距离，距离>30px为有效间隔，取中间值布置切割线
2. 横向切割：按竖条独立处理
   - 纵向距离 < 1/2文本框尺寸 = 同一个字（合并）
   - 计算不同字的y间距，取中间值布置切割线
   - 横向切割线只属于本列，不跨列
"""

import numpy as np
from typing import List, Dict, Tuple


def merge_boxes_to_chars(boxes: List[Dict], merge_ratio: float = 0.5) -> List[Dict]:
    """
    合并x方向距离很近的文本框为同一个字
    merge_ratio: x方向距离小于 文本框尺寸*merge_ratio 时合并
    合并后，字的边界是y_min和y_max（用于计算横向切割线）
    """
    if not boxes:
        return []

    # 按y坐标排序
    sorted_boxes = sorted(boxes, key=lambda b: (b['y_min'], b['x_min']))

    merged = []
    used = set()

    for i, box in enumerate(sorted_boxes):
        if i in used:
            continue

        current_group = [box]
        used.add(i)

        # 查找可以合并的邻近框（x方向距离近）
        for j, other in enumerate(sorted_boxes):
            if j in used:
                continue

            # 计算x方向距离
            dx = 0
            if box['x_max'] < other['x_min']:
                dx = other['x_min'] - box['x_max']
            elif other['x_max'] < box['x_min']:
                dx = box['x_min'] - other['x_max']
            # 如果x方向有重叠，dx为0

            # 参考尺寸：使用较小的文本框宽度
            ref_size = min(box['width'], other['width'])
            threshold = ref_size * merge_ratio

            # 同时检查y方向是否有重叠或接近（同一个字的各部分应该在相近的y位置）
            y_overlap = max(0, min(box['y_max'], other['y_max']) - max(box['y_min'], other['y_min']))
            y_close = y_overlap > 0 or (
                abs(box['center_y'] - other['center_y']) < min(box['height'], other['height']) * 0.5
            )

            # x方向距离近且y位置接近 = 同一个字
            if dx < threshold and y_close:
                current_group.append(other)
                used.add(j)

        # 合并组内的框
        if len(current_group) == 1:
            merged.append(box)
        else:
            merged_box = {
                'x_min': int(min(b['x_min'] for b in current_group)),
                'x_max': int(max(b['x_max'] for b in current_group)),
                'y_min': int(min(b['y_min'] for b in current_group)),
                'y_max': int(max(b['y_max'] for b in current_group)),
            }
            merged_box['width'] = merged_box['x_max'] - merged_box['x_min']
            merged_box['height'] = merged_box['y_max'] - merged_box['y_min']
            merged_box['center_x'] = (merged_box['x_min'] + merged_box['x_max']) // 2
            merged_box['center_y'] = (merged_box['y_min'] + merged_box['y_max']) // 2
            merged.append(merged_box)

    return merged


def find_vertical_cut_lines(boxes: List[Dict], image_width: int, min_gap: int = 30) -> List[int]:
    """
    竖向切割线算法：
    1. 将文本框投影到x轴，找出"占用区间"
    2. 合并重叠或相邻的区间
    3. 找出区间之间的大间隙（>min_gap）
    4. 在间隙中间布置切割线
    """
    if not boxes:
        return [0, image_width]

    # 收集所有文本框的x区间
    intervals = []
    for box in boxes:
        intervals.append([box['x_min'], box['x_max']])

    # 按左边界排序
    intervals.sort(key=lambda x: x[0])

    # 合并重叠或相邻的区间
    merged_intervals = []
    for interval in intervals:
        if not merged_intervals:
            merged_intervals.append(interval)
        else:
            # 检查是否与上一个区间重叠或很近
            last = merged_intervals[-1]
            # 如果当前区间与上一个有重叠或间隙很小（<min_gap），则合并
            if interval[0] <= last[1] + min_gap:
                last[1] = max(last[1], interval[1])
            else:
                merged_intervals.append(interval)

    if len(merged_intervals) <= 1:
        return [0, image_width]

    # 在合并后的区间之间找间隙，布置切割线
    cut_lines = [0]
    for i in range(len(merged_intervals) - 1):
        gap_left = merged_intervals[i][1]
        gap_right = merged_intervals[i + 1][0]
        gap = gap_right - gap_left
        if gap >= min_gap:
            mid = (gap_left + gap_right) // 2
            cut_lines.append(mid)

    cut_lines.append(image_width)

    return sorted(set(cut_lines))


def find_horizontal_cut_lines_for_strip(
    boxes: List[Dict],
    strip_x_start: int,
    strip_x_end: int,
    image_height: int
) -> List[int]:
    """
    横向切割线算法（按竖条独立处理）：
    1. 筛选当前竖条内的文本框
    2. 合并纵向距离 < 1/2文本框尺寸的框为同一个字
    3. 计算不同字的y间距
    4. 在间距中间值位置布置切割线
    """
    # 筛选在当前竖条内的文本框（中心点在竖条内）
    strip_boxes = []
    for box in boxes:
        if strip_x_start <= box['center_x'] <= strip_x_end:
            strip_boxes.append(box)

    if not strip_boxes:
        return [0, image_height]

    # 合并为字
    merged_chars = merge_boxes_to_chars(strip_boxes, merge_ratio=0.5)

    if not merged_chars:
        return [0, image_height]

    # 按y坐标排序
    merged_chars.sort(key=lambda b: b['y_min'])

    # 计算相邻字之间的y间距
    gaps = []
    for i in range(len(merged_chars) - 1):
        current_bottom = merged_chars[i]['y_max']
        next_top = merged_chars[i + 1]['y_min']
        gap = next_top - current_bottom
        if gap > 0:
            gaps.append({
                'gap': gap,
                'position': (current_bottom + next_top) // 2
            })

    # 生成切割线：0 + 字之间的间隙位置 + image_height
    cut_lines = [0]
    for gap_info in gaps:
        cut_lines.append(gap_info['position'])
    cut_lines.append(image_height)

    return sorted(set(cut_lines))


def analyze_cut_lines(boxes: List[Dict], image_width: int, image_height: int) -> Dict:
    """
    综合分析切割线
    步骤：
    1. 计算竖向切割线
    2. 对每条竖条独立计算横向切割线
    """
    # 第一步：计算竖向切割线
    vertical_lines = find_vertical_cut_lines(boxes, image_width, min_gap=30)

    # 第二步：对每条竖条独立计算横向切割线
    # 每个竖条有自己的横向切割线集合
    strip_horizontal_lines = []

    for i in range(len(vertical_lines) - 1):
        strip_x_start = vertical_lines[i]
        strip_x_end = vertical_lines[i + 1]

        strip_h_lines = find_horizontal_cut_lines_for_strip(
            boxes, strip_x_start, strip_x_end, image_height
        )
        strip_horizontal_lines.append({
            'strip_index': i,
            'x_start': strip_x_start,
            'x_end': strip_x_end,
            'horizontal_lines': strip_h_lines
        })

    # 为了前端显示，合并所有横向切割线（但实际切割时按列处理）
    all_horizontal_lines = set([0, image_height])
    for strip_info in strip_horizontal_lines:
        all_horizontal_lines.update(strip_info['horizontal_lines'])
    horizontal_lines = sorted(all_horizontal_lines)

    return {
        'vertical_lines': vertical_lines,
        'horizontal_lines': horizontal_lines,
        'strip_horizontal_lines': strip_horizontal_lines,  # 按列分组的横向切割线
        'original_boxes': boxes
    }
