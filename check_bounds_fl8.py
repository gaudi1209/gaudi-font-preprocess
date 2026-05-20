# -*- coding: utf-8 -*-
"""
FontLab 8 - Check glyphs out of bounds (Top/Bottom/Left/Right)
"""

f = fl.font

if f is None:
    print("Please open a font first")
else:
    # Get font metrics
    upm = f.upm
    asc = float(f.ascender[0])  # VArray, get first element
    dsc = float(f.descender[0])  # VArray, get first element
    
    # Left/Right boundaries
    left_bound = 0
    right_bound = upm
    
    print("=" * 60)
    print("Font: " + str(f.family_name))
    print("UPM: " + str(upm))
    print("Ascender: " + str(asc))
    print("Descender: " + str(dsc))
    print("Left bound: " + str(left_bound))
    print("Right bound: " + str(right_bound))
    print("=" * 60)
    
    # Clear selection
    fl.Unselect(0xffffffff)
    
    overflow_count = 0
    top_list = []
    bottom_list = []
    left_list = []
    right_list = []
    
    # Check all glyphs
    for g in f.glyphs:
        # Skip empty glyphs
        try:
            if g.nodes_count == 0:
                continue
        except:
            continue
        
        # Get bounding box
        try:
            bbox = g.GetBBox()
            xMin = float(bbox[0])
            yMin = float(bbox[1])
            xMax = float(bbox[2])
            yMax = float(bbox[3])
        except:
            continue
        
        has_issue = False
        
        # Check top overflow
        if yMax > asc:
            top_list.append((g.name, yMax - asc))
            has_issue = True
        
        # Check bottom overflow
        if yMin < dsc:
            bottom_list.append((g.name, dsc - yMin))
            has_issue = True
        
        # Check left overflow
        if xMin < left_bound:
            left_list.append((g.name, xMin - left_bound))
            has_issue = True
        
        # Check right overflow
        if xMax > right_bound:
            right_list.append((g.name, xMax - right_bound))
            has_issue = True
        
        # Select if has issue
        if has_issue:
            fl.Select(g.id)
            overflow_count += 1
    
    # Print results
    print("")
    print("Top overflow (" + str(len(top_list)) + " glyphs):")
    print("-" * 60)
    for item in top_list[:15]:
        print("  " + item[0] + ": +" + str(int(item[1])))
    if len(top_list) > 15:
        print("  ... " + str(len(top_list) - 15) + " more")
    
    print("")
    print("Bottom overflow (" + str(len(bottom_list)) + " glyphs):")
    print("-" * 60)
    for item in bottom_list[:15]:
        print("  " + item[0] + ": " + str(int(item[1])))
    if len(bottom_list) > 15:
        print("  ... " + str(len(bottom_list) - 15) + " more")
    
    print("")
    print("Left overflow (" + str(len(left_list)) + " glyphs):")
    print("-" * 60)
    for item in left_list[:15]:
        print("  " + item[0] + ": " + str(int(item[1])))
    if len(left_list) > 15:
        print("  ... " + str(len(left_list) - 15) + " more")
    
    print("")
    print("Right overflow (" + str(len(right_list)) + " glyphs):")
    print("-" * 60)
    for item in right_list[:15]:
        print("  " + item[0] + ": +" + str(int(item[1])))
    if len(right_list) > 15:
        print("  ... " + str(len(right_list) - 15) + " more")
    
    print("")
    print("=" * 60)
    print("Summary:")
    print("  Top:    " + str(len(top_list)) + " glyphs")
    print("  Bottom: " + str(len(bottom_list)) + " glyphs")
    print("  Left:   " + str(len(left_list)) + " glyphs")
    print("  Right:  " + str(len(right_list)) + " glyphs")
    print("  Total:  " + str(overflow_count) + " glyphs selected")
    print("=" * 60)
