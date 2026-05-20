"""配置文件"""
import os
import sys

# PyInstaller 打包后资源文件在 sys._MEIPASS 目录
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = sys._MEIPASS
    BASE_DIR = os.path.dirname(sys.executable)
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = RESOURCE_DIR

# 路径配置（运行时数据在 BASE_DIR，资源文件在 RESOURCE_DIR）
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')
INPUT_FOLDER = os.path.join(BASE_DIR, 'input')
DATA_FOLDER = os.path.join(BASE_DIR, 'data', 'sessions')

# 图像处理配置
TARGET_HEIGHT = 4096  # 目标高度

# 切割线配置
MERGE_DISTANCE_RATIO = 0.8  # 文本框距离小于自身尺寸的此比例时合并

# 允许的图片扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
