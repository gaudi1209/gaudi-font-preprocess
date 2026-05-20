# -*- coding: utf-8 -*-
"""
FontLab 8 简单版 - 检测超出边框的字符

使用方法:
1. FontLab 8 中打开字体
2. Scripts 菜单 > Run Script
3. 选择此文件运行
"""

# 获取当前字体
f = fl.font

if f is None:
    print("请先打开字体文件")
else:
    # 获取边界参数
    upm = f.upm
    asc = f.ascender
    dsc = f.descender
    
    print("=" * 60)
    print(f"字体: {f.font_name}")
    print(f"UPM: {upm}, Ascender: {asc}, Descender: {dsc}")
    print("=" * 60)
    
    # 清空选择
    fl.Unselect(0xffffffff)
    
    overflow_count = 0
    top_overflow = []
    bottom_overflow = []
    
    # 遍历所有字形
    for g in f.glyphs:
        if g.isEmpty():
            continue
        
        # 获取边界框
        box = g.GetBBox()
        xMin, yMin, xMax, yMax = box[0], box[1], box[2], box[3]
        
        # 检查超出
        has_issue = False
        
        if yMax > asc:
            top_overflow.append((g.name, yMax - asc))
            has_issue = True
        
        if yMin < dsc:
            bottom_overflow.append((g.name, dsc - yMin))
            has_issue = True
        
        # 选中超出边框的字形
        if has_issue:
            fl.Select(g.id)
            overflow_count += 1
    
    # 输出报告
    print(f"\n超出顶部边界的字形 ({len(top_overflow)} 个):")
    print("-" * 60)
    for name, excess in top_overflow[:20]:  # 只显示前20个
        print(f"  {name}: 超出 {excess:.0f} 单位")
    if len(top_overflow) > 20:
        print(f"  ... 还有 {len(top_overflow) - 20} 个")
    
    print(f"\n超出底部边界的字形 ({len(bottom_overflow)} 个):")
    print("-" * 60)
    for name, excess in bottom_overflow[:20]:
        print(f"  {name}: 超出 {excess:.0f} 单位")
    if len(bottom_overflow) > 20:
        print(f"  ... 还有 {len(bottom_overflow) - 20} 个")
    
    print("\n" + "=" * 60)
    print(f"总计: {overflow_count} 个字形超出边界 (已选中)")
    print("=" * 60)
