# -*- coding: utf-8 -*-
"""
FontLab 8 脚本 - 检测超出边框的字符
===========================================

使用方法:
1. 在 FontLab 8 中打开字体文件
2. 菜单: Macro > Execute Script (或按 Ctrl+Shift+M)
3. 选择并运行此脚本

功能:
- 检测超出 ascender/descender 的字形
- 检测超出 UPM 左右边界的字形
- 生成详细报告
- 可选: 自动选中超出边框的字形
"""

from fontlab import *
from PythonQt import QtCore

def check_out_of_bounds(font, top_margin=0, bottom_margin=0, select_glyphs=True):
    """
    检测超出边框的字符
    
    参数:
        font: FontLab 字体对象
        top_margin: 顶部允许超出的边距 (正值表示允许超出)
        bottom_margin: 底部允许超出的边距 (正值表示允许超出)
        select_glyphs: 是否自动选中超出边框的字形
    """
    
    if font is None:
        print("错误: 没有打开字体文件")
        return []
    
    # 获取字体参数
    upm = font.upm
    ascender = font.info.ascender if hasattr(font.info, 'ascender') else font.metrics.ascender
    descender = font.info.descender if hasattr(font.info, 'descender') else font.metrics.descender
    
    # 计算边界
    max_top = ascender + top_margin
    max_bottom = descender - bottom_margin
    
    # 结果存储
    overflow_list = []
    
    print("=" * 70)
    print(f"字体: {font.font_name}")
    print(f"UPM: {upm}")
    print(f"Ascender: {ascender}  (最大允许: {max_top})")
    print(f"Descender: {descender}  (最小允许: {max_bottom})")
    print("=" * 70)
    
    # 遍历所有字形
    for glyph in font.glyphs:
        if glyph.isEmpty():
            continue
        
        # 获取边界框
        bbox = glyph.boundingBox if hasattr(glyph, 'boundingBox') else glyph.box
        
        left = bbox[0]
        bottom = bbox[1]
        right = bbox[2]
        top = bbox[3]
        
        issues = []
        
        # 检查超出情况
        if top > max_top:
            issues.append(f"超出顶部 {top - max_top:.0f} 单位")
        
        if bottom < max_bottom:
            issues.append(f"超出底部 {max_bottom - bottom:.0f} 单位")
        
        if left < 0:
            issues.append(f"超出左侧 {-left:.0f} 单位")
        
        if right > upm:
            issues.append(f"超出右侧 {right - upm:.0f} 单位")
        
        if issues:
            char = chr(glyph.unicode) if glyph.unicode and glyph.unicode > 0 else ''
            overflow_list.append({
                'name': glyph.name,
                'unicode': glyph.unicode,
                'char': char,
                'bbox': bbox,
                'issues': issues,
                'glyph': glyph
            })
    
    # 输出结果
    print(f"\n检测到 {len(overflow_list)} 个超出边框的字形:")
    print("-" * 70)
    
    for item in overflow_list:
        char_display = f"({item['char']})" if item['char'] else ""
        unicode_str = f"U+{item['unicode']:04X}" if item['unicode'] else "无Unicode"
        print(f"{item['name']:<20} {char_display:<5} {unicode_str:<12} {'; '.join(item['issues'])}")
    
    # 可选: 选中超出边框的字形
    if select_glyphs and overflow_list:
        print("\n正在选中超出边框的字形...")
        font.selection.clear()
        for item in overflow_list:
            font.selection.select(item['glyph'])
        print(f"已选中 {len(overflow_list)} 个字形")
    
    print("-" * 70)
    print("检测完成")
    
    return overflow_list


# ============ 主程序 ============

# 获取当前字体
current_font = fl.font_if

# 运行检测
# 参数说明:
#   top_margin: 允许超出 ascender 的量 (0 = 不允许超出)
#   bottom_margin: 允许超出 descender 的量 (0 = 不允许超出)
#   select_glyphs: True = 自动选中超出边框的字形

result = check_out_of_bounds(
    current_font,
    top_margin=0,      # 不允许超出顶部
    bottom_margin=0,   # 不允许超出底部
    select_glyphs=True # 自动选中问题字形
)
