# FontLab 8 设置字体中文名称

## 方法一：手动操作（推荐）

1. 在 FontLab 8 中打开 VFC 文件
2. 菜单：**File > Font Info** (或按 `Ctrl+I`)
3. 在左侧选择 **Names**
4. 设置以下字段：
   - **Family Name**: `高迪书法_行书V5`
   - **Style Name**: `Regular`
5. 点击 **OK** 保存
6. 导出字体时，在 **Export Profiles** 中确保选择包含 name table 的选项

## 方法二：使用 Python 脚本

1. 在 FontLab 8 中打开 VFC 文件
2. 菜单：**Window > Panels > Script**
3. 点击文件夹图标，加载脚本：
   `D:\Claudecode\高迪书法字库制作\fontlab_set_chinese_name.py`
4. 点击运行按钮
5. 保存并导出字体

## 方法三：命令行批量处理

```bash
# 在 FontLab 安装目录下运行
"C:\Program Files\FontLab\FontLab 8\FontLab.exe" -run "D:\Claudecode\高迪书法字库制作\fontlab_set_chinese_name.py"
```

## 验证

导出 TTF 后，在 Windows 中右键字体文件 > 属性 > 详细信息，应显示：
- 字体名称：高迪书法_行书V5
- 字体样式：Regular

在 Word 中选择字体时，应显示为"高迪书法_行书V5"
