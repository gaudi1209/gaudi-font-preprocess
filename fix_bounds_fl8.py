# -*- coding: utf-8 -*-
"""
FontLab 8 - Auto fix glyphs out of bounds
Usage: Scripts > Run Script > select this file

功能:
1. 检测超出 ascender/descender 的字形
2. 自动缩放到安全边界内
3. 生成修正报告
"""

f = fl.font

if f is None:
    print("Please open a font first")
else:
    # Get font metrics
    upm = f.upm
    asc = f.info.ascender[0] if hasattr(f.info.ascender, '__getitem__') else float(f.info.ascender)
    dsc = f.info.descender[0] if hasattr(f.info.descender, '__getitem__') else float(f.info.descender)
    
    # Safety margin
    margin = 10
    safe_top = asc - margin
    safe_bottom = dsc + margin
    
    print("=" * 60)
    print("Font: " + f.family_name)
    print("UPM: " + str(upm))
    print("Ascender: " + str(asc) + " (safe: " + str(safe_top) + ")")
    print("Descender: " + str(dsc) + " (safe: " + str(safe_bottom) + ")")
    print("=" * 60)
    
    fixed_count = 0
    fixed_list = []
    
    for g in f.glyphs:
        if g.nodes_count == 0:
            continue
        
        try:
            bbox = g.GetBBox()
            yMin = bbox[1]
            yMax = bbox[3]
        except:
            continue
        
        # Calculate scale needed
        top_excess = yMax - safe_top
        bottom_excess = safe_bottom - yMin
        
        max_excess = max(top_excess, bottom_excess)
        
        if max_excess > 0:
            # Need to scale down
            # Calculate scale factor
            height = yMax - yMin
            safe_height = height - max_excess - margin
            scale = safe_height / height if height > 0 else 1.0
            
            if scale < 0.5:
                scale = 0.5  # Minimum scale
            
            # Apply scale
            fl.CallCommand(g.id, 34000)  # Select glyph
            g.Scale(scale, scale, g.width/2, (yMax + yMin)/2)
            
            fixed_list.append((g.name, scale * 100))
            fixed_count += 1
    
    # Report
    print("")
    print("Fixed " + str(fixed_count) + " glyphs:")
    print("-" * 60)
    for item in fixed_list[:20]:
        print("  " + item[0] + ": scaled to " + str(int(item[1])) + "%")
    if len(fixed_list) > 20:
        print("  ... and " + str(len(fixed_list) - 20) + " more")
    
    print("")
    print("=" * 60)
    print("Done! Please review the changes.")
    print("=" * 60)
