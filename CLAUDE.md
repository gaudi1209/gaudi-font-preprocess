# CLAUDE.md - 高迪书法字库制作项目

## 项目概览

高迪书法字库制作，涉及字体训练、字库生成、字符检测、文档排版等工作。

## 常用路径

| 用途 | 路径 |
|------|------|
| 字库制作根目录 | `D:\Claudecode\高迪书法字库制作` |
| 字库输出 | `D:\Claudecode\高迪书法字库制作\output` |
| 字体训练 | `D:\Claudecode\字体训练\zi2zi-JiT-main` |
| 字库文件（行书V5） | `C:\Users\chenlin\Desktop\2026工作文件\高迪书法_行书V5\OpenType-TT\高迪书法_行书V5-Regular.ttf` |
| 字库文件（王羲之） | `C:\Users\chenlin\Desktop\2026工作文件\gaudi\OpenType-TT\高迪书法_王羲之V1-Regular.ttf` |

## 字库缺失字符检测规范

- 输出文件命名：`字库缺失字符_<标识>_<日期>.txt`
- 每200字一组，带编号（如 `1. xxxx`）
- 所有字符写入一个文件，用换行分隔每组
- 支持 CJK 全区段：基本区、扩展A-F、兼容区
- 输出时附带分区段统计信息
