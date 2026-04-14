"""高迪书法字库预处理工具 - Flask主应用"""
import os
import json
import cv2
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

from config import *
from utils.image_processor import load_image, to_binary, resize_to_height, compute_hash, save_image, get_image_info
from utils.ocr_handler import detect_text_boxes
from utils.cut_analyzer import analyze_cut_lines
from utils.storage import save_session, load_session
from utils.empty_detector import detect_empty_slice

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 最大50MB

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)


@app.route('/')
def index():
    """首页 - 重定向到切割布局页面"""
    return redirect(url_for('layout'))


@app.route('/layout')
def layout():
    """切割布局页面"""
    return render_template('layout.html')


@app.route('/adjust')
def adjust():
    """切割调整页面"""
    return render_template('adjust.html')


@app.route('/scale')
def scale():
    """缩放校正页面"""
    return render_template('scale.html')


@app.route('/annotate')
def annotate():
    """标注出图页面"""
    return render_template('annotate.html')


@app.route('/api/upload', methods=['POST'])
def upload_image():
    """上传图片并处理"""
    if 'image' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式'}), 400

    # 保存原始文件
    filename = secure_filename(file.filename)
    original_path = os.path.join(app.config['UPLOAD_FOLDER'], f"original_{filename}")
    file.save(original_path)

    # 计算哈希
    file_hash = compute_hash(original_path)

    # 加载并处理图片
    img = load_image(original_path)
    original_height, original_width = img.shape[:2]

    # 转换为二值图
    binary = to_binary(img)

    # 缩放到目标高度
    resized, scale = resize_to_height(binary, TARGET_HEIGHT)
    resized_height, resized_width = resized.shape[:2]

    # 保存处理后的图片
    processed_filename = f"{file_hash}.png"
    processed_path = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)
    save_image(resized, processed_path)

    # 检查是否有保存的会话
    session_data = load_session(file_hash, DATA_FOLDER)

    if session_data:
        # 使用保存的切割线
        # 如果会话中没有boxes，重新检测
        boxes = session_data.get('boxes', [])
        print(f"加载会话: hash={file_hash}, 会话中boxes数量={len(boxes)}")

        if not boxes:
            print("会话中无boxes，重新检测...")
            try:
                boxes = detect_text_boxes(resized)
                print(f"重新检测到boxes数量={len(boxes)}")
            except Exception as e:
                print(f"文本框检测失败: {e}")
                boxes = []

        return jsonify({
            'success': True,
            'hash': file_hash,
            'image_url': f'/static/uploads/{processed_filename}',
            'original_width': original_width,
            'original_height': original_height,
            'width': resized_width,
            'height': resized_height,
            'scale': scale,
            'vertical_lines': session_data.get('vertical_lines', []),
            'horizontal_lines': session_data.get('horizontal_lines', []),
            'strip_horizontal_lines': session_data.get('strip_horizontal_lines', []),
            'boxes': boxes,
            'has_saved_session': True
        })

    # 文本框检测（使用 OpenCV 轮廓检测）
    try:
        boxes = detect_text_boxes(resized)
    except Exception as e:
        print(f"文本框检测失败: {e}")
        boxes = []

    # 分析切割线
    cut_result = analyze_cut_lines(boxes, resized_width, resized_height)

    return jsonify({
        'success': True,
        'hash': file_hash,
        'image_url': f'/static/uploads/{processed_filename}',
        'original_width': original_width,
        'original_height': original_height,
        'width': resized_width,
        'height': resized_height,
        'scale': scale,
        'vertical_lines': cut_result['vertical_lines'],
        'horizontal_lines': cut_result['horizontal_lines'],
        'strip_horizontal_lines': cut_result['strip_horizontal_lines'],
        'boxes': boxes,
        'has_saved_session': False
    })


@app.route('/api/save_cuts', methods=['POST'])
def save_cuts():
    """保存切割线配置"""
    data = request.get_json()
    image_hash = data.get('hash')
    vertical_lines = data.get('vertical_lines', [])
    horizontal_lines = data.get('horizontal_lines', [])
    strip_horizontal_lines = data.get('strip_horizontal_lines', [])
    boxes = data.get('boxes', [])

    print(f"保存切割线: hash={image_hash}, boxes数量={len(boxes)}")

    if not image_hash:
        return jsonify({'error': '缺少图片哈希'}), 400

    session_data = {
        'hash': image_hash,
        'vertical_lines': vertical_lines,
        'horizontal_lines': horizontal_lines,
        'strip_horizontal_lines': strip_horizontal_lines,
        'boxes': boxes
    }

    if save_session(image_hash, session_data, DATA_FOLDER):
        return jsonify({'success': True})
    else:
        return jsonify({'error': '保存失败'}), 500


@app.route('/api/load_session/<image_hash>')
def api_load_session(image_hash):
    """加载会话数据"""
    session_data = load_session(image_hash, DATA_FOLDER)
    if session_data:
        return jsonify({'success': True, 'data': session_data})
    else:
        return jsonify({'success': False, 'error': '会话不存在'})


@app.route('/api/apply_cuts', methods=['POST'])
def apply_cuts():
    """应用切割，保存切割结果"""
    data = request.get_json()
    image_hash = data.get('hash')
    vertical_lines = data.get('vertical_lines', [])
    strip_horizontal_lines = data.get('strip_horizontal_lines', [])

    if not image_hash:
        return jsonify({'error': '缺少图片哈希'}), 400

    # 加载处理后的图片
    processed_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{image_hash}.png")
    if not os.path.exists(processed_path):
        return jsonify({'error': '图片不存在'}), 404

    img = load_image(processed_path)

    # 创建输出目录
    output_dir = os.path.join(OUTPUT_FOLDER, image_hash)
    os.makedirs(output_dir, exist_ok=True)

    # 按列切割图片
    cut_images = []
    idx = 0

    if strip_horizontal_lines and len(strip_horizontal_lines) > 0:
        # 使用按列分组的横向切割线
        for strip_info in strip_horizontal_lines:
            strip_index = strip_info.get('strip_index', 0)
            x_start = strip_info.get('x_start', 0)
            x_end = strip_info.get('x_end', 0)
            h_lines = strip_info.get('horizontal_lines', [])

            for i in range(len(h_lines) - 1):
                y1 = h_lines[i]
                y2 = h_lines[i + 1]

                # 切割
                piece = img[y1:y2, x_start:x_end]

                # 检测是否为空切片
                is_empty, text_ratio, _ = detect_empty_slice(piece, threshold=0.05)

                # 保存
                piece_filename = f"char_{idx:04d}.png"
                piece_path = os.path.join(output_dir, piece_filename)
                save_image(piece, piece_path)

                cut_images.append({
                    'index': idx,
                    'strip_index': strip_index,
                    'char_index': i,
                    'filename': piece_filename,
                    'x': x_start, 'y': y1,
                    'width': x_end - x_start,
                    'height': y2 - y1,
                    'is_empty': is_empty,
                    'text_ratio': round(text_ratio, 4)
                })
                idx += 1
    else:
        # 兼容旧数据：使用全局横向切割线
        horizontal_lines = data.get('horizontal_lines', [])
        for i in range(len(horizontal_lines) - 1):
            for j in range(len(vertical_lines) - 1):
                y1 = horizontal_lines[i]
                y2 = horizontal_lines[i + 1]
                x1 = vertical_lines[j]
                x2 = vertical_lines[j + 1]

                # 切割
                piece = img[y1:y2, x1:x2]

                # 检测是否为空切片
                is_empty, text_ratio, _ = detect_empty_slice(piece, threshold=0.05)

                # 保存
                piece_filename = f"char_{idx:04d}.png"
                piece_path = os.path.join(output_dir, piece_filename)
                save_image(piece, piece_path)

                cut_images.append({
                    'index': idx,
                    'strip_index': j,
                    'char_index': i,
                    'filename': piece_filename,
                    'x': x1, 'y': y1,
                    'width': x2 - x1,
                    'height': y2 - y1,
                    'is_empty': is_empty,
                    'text_ratio': round(text_ratio, 4)
                })
                idx += 1

    return jsonify({
        'success': True,
        'total_pieces': len(cut_images),
        'output_dir': output_dir,
        'pieces': cut_images
    })


@app.route('/api/get_cut_results/<image_hash>')
def get_cut_results(image_hash):
    """获取切割结果（用于切割调整页面）"""
    # 加载会话数据
    session_data = load_session(image_hash, DATA_FOLDER)
    if not session_data:
        return jsonify({'success': False, 'error': '会话不存在，请先在切割布局页面处理图片'})

    # 检查是否已有完整的切割结果（包含正确的坐标）
    characters = session_data.get('characters', [])
    has_valid_coords = characters and any(c.get('x', 0) > 0 or c.get('y', 0) > 0 for c in characters)

    output_dir = os.path.join(OUTPUT_FOLDER, image_hash)

    # 如果没有有效的坐标数据，需要重新生成
    if not has_valid_coords:
        processed_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{image_hash}.png")
        if not os.path.exists(processed_path):
            return jsonify({'success': False, 'error': '图片不存在'})

        img = load_image(processed_path)
        os.makedirs(output_dir, exist_ok=True)

        vertical_lines = session_data.get('vertical_lines', [])
        strip_horizontal_lines = session_data.get('strip_horizontal_lines', [])

        idx = 0
        characters = []

        if strip_horizontal_lines and len(strip_horizontal_lines) > 0:
            for strip_info in strip_horizontal_lines:
                strip_index = strip_info.get('strip_index', 0)
                x_start = strip_info.get('x_start', 0)
                x_end = strip_info.get('x_end', 0)
                h_lines = strip_info.get('horizontal_lines', [])

                for i in range(len(h_lines) - 1):
                    y1 = h_lines[i]
                    y2 = h_lines[i + 1]

                    piece = img[y1:y2, x_start:x_end]
                    is_empty, text_ratio, _ = detect_empty_slice(piece, threshold=0.05)

                    piece_filename = f"char_{idx:04d}.png"
                    piece_path = os.path.join(output_dir, piece_filename)
                    save_image(piece, piece_path)

                    characters.append({
                        'index': idx,
                        'strip_index': strip_index,
                        'char_index': i,
                        'filename': piece_filename,
                        'image_url': f'/output/{image_hash}/{piece_filename}',
                        'x': x_start, 'y': y1,
                        'width': x_end - x_start,
                        'height': y2 - y1,
                        'is_empty': is_empty,
                        'text_ratio': round(text_ratio, 4),
                        'needs_adjust': False
                    })
                    idx += 1
        else:
            horizontal_lines = session_data.get('horizontal_lines', [])
            for i in range(len(horizontal_lines) - 1):
                for j in range(len(vertical_lines) - 1):
                    y1 = horizontal_lines[i]
                    y2 = horizontal_lines[i + 1]
                    x1 = vertical_lines[j]
                    x2 = vertical_lines[j + 1]

                    piece = img[y1:y2, x1:x2]
                    is_empty, text_ratio, _ = detect_empty_slice(piece, threshold=0.05)

                    piece_filename = f"char_{idx:04d}.png"
                    piece_path = os.path.join(output_dir, piece_filename)
                    save_image(piece, piece_path)

                    characters.append({
                        'index': idx,
                        'strip_index': j,
                        'char_index': i,
                        'filename': piece_filename,
                        'image_url': f'/output/{image_hash}/{piece_filename}',
                        'x': x1, 'y': y1,
                        'width': x2 - x1,
                        'height': y2 - y1,
                        'is_empty': is_empty,
                        'text_ratio': round(text_ratio, 4),
                        'needs_adjust': False
                    })
                    idx += 1

        # 保存切割结果到会话
        session_data['characters'] = characters
        save_session(image_hash, session_data, DATA_FOLDER)

    return jsonify({
        'success': True,
        'characters': characters,
        'image_hash': image_hash
    })


@app.route('/api/save_adjustments', methods=['POST'])
def save_adjustments():
    """保存调整结果"""
    data = request.get_json()
    image_hash = data.get('hash')
    characters = data.get('characters', [])

    if not image_hash:
        return jsonify({'error': '缺少图片哈希'}), 400

    # 加载会话数据
    session_data = load_session(image_hash, DATA_FOLDER)
    if not session_data:
        return jsonify({'error': '会话不存在'}), 404

    # 更新字符数据
    session_data['characters'] = characters
    save_session(image_hash, session_data, DATA_FOLDER)

    return jsonify({'success': True})


@app.route('/api/process_scale', methods=['POST'])
def process_scale():
    """处理缩放校正"""
    from utils.scale_processor import apply_adjustments, scale_char
    import traceback

    try:
        data = request.get_json()
        image_hash = data.get('hash')
        characters = data.get('characters', [])
        scale = data.get('scale', 1.15)
        align = data.get('align', 'center')
        background = data.get('background', 'black')
        target_size = data.get('target_size', 512)

        if not image_hash:
            return jsonify({'error': '缺少图片哈希'}), 400

        # 创建输出目录
        output_dir = os.path.join(OUTPUT_FOLDER, image_hash, 'scaled')
        os.makedirs(output_dir, exist_ok=True)

        processed_characters = []

        for i, char in enumerate(characters):
            try:
                # 读取原始图片
                filename = char.get('filename', char.get('original_filename', ''))
                if not filename:
                    print(f"字符 {i} 缺少 filename 字段: {char}")
                    continue

                original_path = os.path.join(OUTPUT_FOLDER, image_hash, filename)
                if not os.path.exists(original_path):
                    print(f"文件不存在: {original_path}")
                    continue

                img = load_image(original_path)

                # 应用调整值（如果有）
                adjust_top = char.get('adjust_top', 0) or 0
                adjust_bottom = char.get('adjust_bottom', 0) or 0
                adjust_left = char.get('adjust_left', 0) or 0
                adjust_right = char.get('adjust_right', 0) or 0

                if adjust_top > 0 or adjust_bottom > 0 or adjust_left > 0 or adjust_right > 0:
                    img = apply_adjustments(img, adjust_top, adjust_bottom, adjust_left, adjust_right)

                # 处理缩放和居中
                processed = scale_char(img, scale, target_size, align, background)

                # 保存
                output_filename = f"scaled_{i:04d}.png"
                output_path = os.path.join(output_dir, output_filename)

                if background == 'transparent':
                    cv2.imwrite(output_path, processed)
                else:
                    save_image(processed, output_path)

                processed_characters.append({
                    'index': i,
                    'original_filename': filename,
                    'processed_filename': output_filename,
                    'processed_url': f'/output/{image_hash}/scaled/{output_filename}'
                })
            except Exception as e:
                print(f"处理字符 {i} 失败: {e}")
                traceback.print_exc()
                continue

        return jsonify({
            'success': True,
            'characters': processed_characters,
            'output_dir': output_dir,
            'total': len(processed_characters)
        })
    except Exception as e:
        print(f"process_scale 错误: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/save_scaled', methods=['POST'])
def save_scaled():
    """保存缩放校正结果"""
    data = request.get_json()
    image_hash = data.get('hash')
    characters = data.get('characters', [])

    if not image_hash:
        return jsonify({'error': '缺少图片哈希'}), 400

    # 加载会话数据
    session_data = load_session(image_hash, DATA_FOLDER)
    if not session_data:
        return jsonify({'error': '会话不存在'}), 404

    # 保存缩放校正数据
    session_data['scaled_characters'] = characters
    session_data['scale_processed'] = True
    save_session(image_hash, session_data, DATA_FOLDER)

    return jsonify({'success': True})


@app.route('/api/cleanup_intermediate', methods=['POST'])
def cleanup_intermediate():
    """清理中间过程文件，只保留最终导出目录"""
    import shutil

    data = request.get_json()
    image_hash = data.get('hash')
    keep_dir = data.get('keep_dir', '')  # 保留的最终输出目录

    if not image_hash:
        return jsonify({'error': '缺少图片哈希'}), 400

    base_dir = os.path.join(OUTPUT_FOLDER, image_hash)
    if not os.path.exists(base_dir):
        return jsonify({'success': True, 'message': '目录不存在，无需清理'})

    cleaned = []
    # 清理切割后的原始文件 (char_XXXX.png)
    for f in os.listdir(base_dir):
        fpath = os.path.join(base_dir, f)
        if os.path.isfile(fpath) and f.startswith('char_') and f.endswith('.png'):
            os.remove(fpath)
            cleaned.append(f)
        elif os.path.isdir(fpath):
            dirname = f.lower()
            # 清理 scaled 目录
            if dirname == 'scaled':
                shutil.rmtree(fpath)
                cleaned.append(f'{f}/ (整个目录)')
            # 清理旧的 exported 目录中非 keep_dir 的
            elif dirname == 'exported':
                for sub in os.listdir(fpath):
                    sub_path = os.path.join(fpath, sub)
                    if os.path.isdir(sub_path) and sub_path != keep_dir:
                        shutil.rmtree(sub_path)
                        cleaned.append(f'{f}/{sub}/ (旧导出)')

    return jsonify({
        'success': True,
        'cleaned': cleaned,
        'message': f'已清理 {len(cleaned)} 项中间文件'
    })


@app.route('/api/open_directory', methods=['POST'])
def open_directory():
    """打开目录"""
    import subprocess
    import platform

    data = request.get_json()
    path = data.get('path', '')

    if not path or not os.path.exists(path):
        return jsonify({'error': '目录不存在'}), 400

    try:
        system = platform.system()
        if system == 'Windows':
            os.startfile(path)
        elif system == 'Darwin':  # macOS
            subprocess.run(['open', path])
        else:  # Linux
            subprocess.run(['xdg-open', path])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 静态文件服务 - 输出目录
@app.route('/output/<path:filename>')
def serve_output(filename):
    """提供输出文件访问"""
    from flask import send_from_directory
    return send_from_directory(OUTPUT_FOLDER, filename)


# ==================== 标注出图 API ====================

@app.route('/api/get_scaled_results/<image_hash>')
def get_scaled_results(image_hash):
    """获取缩放校正后的结果"""
    session_data = load_session(image_hash, DATA_FOLDER)
    if not session_data:
        return jsonify({'success': False, 'error': '会话不存在'})

    # 优先获取缩放校正后的数据
    characters = session_data.get('scaled_characters', [])
    if not characters:
        # 如果没有缩放校正数据，返回原始切割结果
        characters = session_data.get('characters', [])

    output_dir = os.path.join(OUTPUT_FOLDER, image_hash, 'scaled')

    return jsonify({
        'success': True,
        'characters': characters,
        'output_dir': output_dir
    })


@app.route('/api/convert_to_traditional', methods=['POST'])
def convert_to_traditional():
    """简体转繁体"""
    try:
        import opencc
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({'success': True, 'result': ''})

        # 使用 OpenCC 转换：简体 -> 繁体
        converter = opencc.OpenCC('s2t')
        result = converter.convert(text)

        print(f"简转繁: '{text}' -> '{result}'")
        return jsonify({'success': True, 'result': result})
    except ImportError as e:
        print(f"OpenCC未安装: {e}")
        return jsonify({'success': True, 'result': text})
    except Exception as e:
        print(f"简转繁错误: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/convert_to_simplified', methods=['POST'])
def convert_to_simplified():
    """繁体转简体"""
    try:
        import opencc
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({'success': True, 'result': ''})

        # 使用 OpenCC 转换：繁体 -> 简体
        converter = opencc.OpenCC('t2s')
        result = converter.convert(text)

        print(f"繁转简: '{text}' -> '{result}'")
        return jsonify({'success': True, 'result': result})
    except ImportError as e:
        print(f"OpenCC未安装: {e}")
        return jsonify({'success': True, 'result': text})
    except Exception as e:
        print(f"繁转简错误: {e}")
        return jsonify({'success': False, 'error': str(e)})
    except ImportError:
        # 如果没有安装 OpenCC，尝试使用内置映射
        return jsonify({'success': True, 'result': text})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/export_annotated', methods=['POST'])
def export_annotated():
    """导出标注后的图片（白底黑字，UTF-8命名）"""
    from datetime import datetime

    data = request.get_json()
    image_hash = data.get('hash')
    annotations = data.get('annotations', [])
    mode = data.get('mode', 'traditional')

    print(f"导出请求: hash={image_hash}, annotations数量={len(annotations)}, mode={mode}")

    if not image_hash:
        return jsonify({'success': False, 'error': '缺少图片哈希'}), 400

    if not annotations:
        return jsonify({'success': False, 'error': '没有标注数据，请先标注字符'}), 400

    # 创建带时间戳的输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_dir = os.path.join(OUTPUT_FOLDER, image_hash, 'exported', timestamp)
    os.makedirs(export_dir, exist_ok=True)
    print(f"导出目录: {export_dir}")

    count = 0
    errors = []

    # 用于跟踪重复字符
    char_counts = {}

    for ann in annotations:
        try:
            # 源文件路径 - 尝试多个可能的位置
            src_path = None

            # 1. 尝试原始文件名
            if ann.get('filename'):
                src_path = os.path.join(OUTPUT_FOLDER, image_hash, ann['filename'])
                if not os.path.exists(src_path):
                    src_path = None

            # 2. 尝试 scaled 目录
            if not src_path:
                scaled_name = f"scaled_{ann['index']:04d}.png"
                src_path = os.path.join(OUTPUT_FOLDER, image_hash, 'scaled', scaled_name)
                if not os.path.exists(src_path):
                    src_path = None

            # 3. 尝试原始 char 文件名
            if not src_path and ann.get('original_filename'):
                src_path = os.path.join(OUTPUT_FOLDER, image_hash, ann['original_filename'])
                if not os.path.exists(src_path):
                    src_path = None

            if not src_path:
                errors.append(f"找不到文件: index={ann['index']}")
                continue

            print(f"处理文件: {src_path}")

            # 读取图片
            img = load_image(src_path)

            # 反色：黑底白字 -> 白底黑字
            inverted = cv2.bitwise_not(img)

            # 生成文件名：uniXXXX.png，重复字加后缀
            char = ann.get('character', '')
            if not char:
                errors.append(f"没有字符: index={ann['index']}")
                continue

            code = ord(char)

            # 检查是否是重复字符，添加后缀
            if char in char_counts:
                char_counts[char] += 1
                suffix = f"_{char_counts[char]:02d}"
            else:
                char_counts[char] = 0
                suffix = ""

            # 文件名：BMP用uniXXXX，扩展区用uXXXXX
            if code > 0xFFFF:
                filename = f"u{code:05X}{suffix}.png"
            else:
                filename = f"uni{code:04X}{suffix}.png"

            # 保存
            output_path = os.path.join(export_dir, filename)
            save_image(inverted, output_path)
            print(f"已保存: {output_path}")
            count += 1

        except Exception as e:
            error_msg = f"导出失败 index={ann.get('index')}: {e}"
            print(error_msg)
            errors.append(error_msg)
            continue

    print(f"导出完成: 成功 {count} 个, 错误 {len(errors)} 个")

    return jsonify({
        'success': True,
        'count': count,
        'output_dir': export_dir,
        'errors': errors
    })


@app.route('/api/export_csv', methods=['POST'])
def export_csv():
    """导出 FontLab CSV 格式"""
    import csv
    from datetime import datetime

    data = request.get_json()
    image_hash = data.get('hash')
    annotations = data.get('annotations', [])
    mode = data.get('mode', 'traditional')

    if not image_hash or not annotations:
        return jsonify({'error': '缺少参数'}), 400

    # 创建输出文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f"fontlab_{timestamp}.csv"
    csv_path = os.path.join(OUTPUT_FOLDER, image_hash, 'exported', csv_filename)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['filename', 'unicode', 'character', 'simplified', 'traditional'])

        for ann in annotations:
            char = ann.get('primary', '')
            if char:
                code = ord(char)
                if code > 0xFFFF:
                    png_name = f"u{code:05X}.png"
                else:
                    png_name = f"uni{code:04X}.png"
                writer.writerow([
                    png_name,
                    f"U+{code:04X}" if code <= 0xFFFF else f"U+{code:05X}",
                    char,
                    ann.get('simplified', ''),
                    ann.get('traditional', '')
                ])

    return jsonify({
        'success': True,
        'output_path': csv_path
    })


@app.route('/api/import_characters', methods=['POST'])
def import_characters():
    """从目录导入字符图片"""
    import hashlib

    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': '没有文件'}), 400

    # 计算目录哈希
    dir_path = os.path.dirname(files[0].filename) if files[0].filename else ''
    dir_hash = hashlib.md5(dir_path.encode()).hexdigest()[:16]

    # 创建输出目录
    output_dir = os.path.join(OUTPUT_FOLDER, dir_hash)
    os.makedirs(output_dir, exist_ok=True)

    characters = []
    idx = 0

    for file in files:
        if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            # 保存文件
            filename = f"char_{idx:04d}.png"
            filepath = os.path.join(output_dir, filename)
            file.save(filepath)

            characters.append({
                'index': idx,
                'filename': filename,
                'image_url': f'/output/{dir_hash}/{filename}'
            })
            idx += 1

    # 保存会话数据
    session_data = {
        'hash': dir_hash,
        'characters': characters,
        'imported': True
    }
    save_session(dir_hash, session_data, DATA_FOLDER)

    return jsonify({
        'success': True,
        'hash': dir_hash,
        'characters': characters,
        'output_dir': output_dir
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7500)
