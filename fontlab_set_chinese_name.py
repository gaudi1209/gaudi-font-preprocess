"""
FontLab 8 脚本：设置字体中文名称
在 FontLab 中运行此脚本，或在命令行中使用 fontlab 命令执行

使用方法：
1. 在 FontLab 中打开 VFC 文件
2. 打开脚本面板 (Window > Panels > Script)
3. 运行此脚本
"""

from fontlab import flFont, flApplication
import fontlab as fl

def set_chinese_font_name(font, chinese_name, subfamily="Regular"):
    """
    设置字体的中文名称

    参数:
        font: FontLab 字体对象
        chinese_name: 中文家庭名称 (如 "高迪书法_行书V5")
        subfamily: 子族名称 (Regular, Bold, etc.)
    """

    # 获取当前字体的 family name
    current_family = font.family_name
    print(f"当前 Family Name: {current_family}")
    print(f"设置中文名称: {chinese_name}")

    # Windows 简体中文的 name table 参数
    # Platform ID: 3 (Windows)
    # Encoding ID: 1 (Unicode BMP)
    # Language ID: 2052 (0x0804 简体中文)

    # 设置 name table 条目
    names = font.names

    # Name ID 1: Font Family (家庭名称)
    names.setName(chinese_name, 1, 3, 1, 2052)  # Windows 简体中文
    names.setName(chinese_name, 1, 1, 0, 0)     # Macintosh (可选)

    # Name ID 2: Font Subfamily (子族名称)
    names.setName(subfamily, 2, 3, 1, 2052)
    names.setName(subfamily, 2, 1, 0, 0)

    # Name ID 4: Full Font Name (完整名称)
    full_name = f"{chinese_name} {subfamily}"
    names.setName(full_name, 4, 3, 1, 2052)
    names.setName(full_name, 4, 1, 0, 0)

    # Name ID 6: PostScript Name (保持英文/拼音)
    ps_name = chinese_name.replace(" ", "_") + "-" + subfamily
    names.setName(ps_name, 6, 3, 1, 1033)  # 英文

    # Name ID 16: Typographic Family (可选，用于多字重家族)
    names.setName(chinese_name, 16, 3, 1, 2052)

    # Name ID 17: Typographic Subfamily
    names.setName(subfamily, 17, 3, 1, 2052)

    # 更新字体的 family_name 属性
    font.family_name = chinese_name

    print(f"已设置中文名称:")
    print(f"  Family: {chinese_name}")
    print(f"  Subfamily: {subfamily}")
    print(f"  Full Name: {full_name}")

    return True


# ========== 主程序 ==========

# 获取当前打开的字体
app = flApplication()
font = app.currentFont

if font is None:
    print("错误：没有打开的字体文件")
    print("请先打开 VFC 文件再运行此脚本")
else:
    # 设置中文名称
    chinese_name = "高迪书法_行书V5"
    subfamily = "Regular"

    set_chinese_font_name(font, chinese_name, subfamily)

    # 保存文件
    font.save()
    print(f"\n已保存到: {font.path}")
    print("请导出字体文件以验证中文名称")
