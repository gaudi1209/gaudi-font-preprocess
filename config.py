"""配置文件"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 路径配置
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
