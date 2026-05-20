# -*- coding: utf-8 -*-
"""
FontLab 8 脚本 - 检测超出边框的字符
使用方法: 在 FontLab 8 中打开字体，然后运行此脚本
"""

from fontlab import flFont, flGlyph
import FL

def check_glyph_bounds(font, margin_top=0, margin_bottom=0, margin_left=0, margin_right=0):
    """
    检测超出边框的字符
    
    参数:
        font: 当前字体
        margin_top: 顶部安全边距（相对于 ascender）
        margin_bottom: 底部安全边距（相对于 descender）
        margin_left: 左侧安全边距
        margin_right: 右侧安全边距
    """
    
    # 获取字体的度量参数
    upm = font.upm
    ascender = font.ascender
    descender = font.descender
    
    # 定义安全边界
    safe_top = ascender - margin_top
    safe_bottom = descender + margin_bottom
    safe_left = margin_left
    safe_right = upm - margin_right
    
    # 存储超出边框的字形
    overflow_glyphs = []
    
    # 遍历所有字形
    for glyph in font.glyphs:
        if glyph.isEmpty():
            continue
            
        # 获取字形边界框
        bbox = glyph.bBox
        x_min, y_min = bbox[0]
        x_max, y_max = bbox[1]
        
        # 检查是否超出边界
        issues = []
        
        if y_max > safe_top:
            overflow = y_max - safe_top
            issues.append(f"顶部超出 {overflow:.0f} 单位")
            
        if y_min < safe_bottom:
            overflow = safe_bottom - y_min
            issues.append(f"底部超出 {overflow:.0f} 单位")
            
        if x_min < safe_left:
            overflow = safe_left - x_min
            issues.append(f"左侧超出 {overflow:.0f} 单位")
            
        if x_max > safe_right:
            overflow = x_max - safe_right
            issues.append(f"右侧超出 {overflow:.0f} 单位")
        
        if issues:
            overflow_glyphs.append({
                'name': glyph.name,
                'unicode': glyph.unicode,
                'bbox': bbox,
                'issues': issues
            })
    
    return overflow_glyphs, safe_top, safe_bottom, safe_left, safe_right


def main():
    # 获取当前字体
    font = flFont(fl.font_if)
    
    if not font:
        print("错误: 没有打开的字体文件")
        return
    
    print("=" * 60)
    print(f"字体: {font.font_name}")
    print("=" * 60)
    print()
    
    # 设置安全边距（可根据需要调整）
    margin_top = 50      # 顶部边距
    margin_bottom = 50   # 底部边距  
    margin_left = 50     # 左侧边距
    margin_right = 50    # 右侧边距
    
    # 检测超出边框的字符
    overflow_glyphs, safe_top, safe_bottom, safe_left, safe_right = check_glyph_bounds(
        font, margin_top, margin_bottom, margin_left, margin_right
    )
    
    # 输出安全边界信息
    print(f"安全边界设置:")
    print(f"  顶部边界: {safe_top:.0f} (Ascender: {font.ascender} - 边距: {margin_top})")
    print(f"  底部边界: {safe_bottom:.0f} (Descender: {font.descender} + 边距: {margin_bottom})")
    print(f"  左侧边界: {safe_left:.0f}")
    print(f"  右侧边界: {safe_right:.0f} (UPM: {font.upm} - 边距: {margin_right})")
    print()
    
    # 输出结果
    if overflow_glyphs:
        print(f"发现 {len(overflow_glyphs)} 个超出边框的字符:")
        print("-" * 60)
        
        for item in overflow_glyphs:
            char = chr(item['unicode']) if item['unicode'] else '?'
            print(f"\n字形: {item['name']} ({char})")
            print(f"  Unicode: U+{item['unicode']:04X}" if item['unicode'] else "  无 Unicode")
            print(f"  边界框: ({item['bbox'][0][0]:.0f}, {item['bbox'][0][1]:.0f}) - ({item['bbox'][1][0]:.0f}, {item['bbox'][1][1]:.0f})")
            print(f"  问题: {', '.join(item['issues'])}")
    else:
        print("所有字符都在安全边界内")
    
    print()
    print("=" * 60)
    print("检测完成")


if __name__ == "__main__":
    main()
