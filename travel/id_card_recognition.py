"""身份证图像识别（OpenCV + Tesseract）；排错与依赖见 offline/docs/开发文档.md、TESSERACT安装.md。"""
import os
import re
from datetime import datetime
from typing import Optional, Tuple
import cv2
import numpy as np
import pytesseract


# 尝试导入OCR库并检查Tesseract是否可用
TESSERACT_AVAILABLE = False

try:
    
    # 尝试自动检测Tesseract路径（Windows常见路径）
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', '')),
    ]

    # 检查Tesseract命令是否可用
    try:
        pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
    except Exception:
        # 尝试使用常见路径
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    pytesseract.pytesseract.tesseract_cmd = path
                    pytesseract.get_tesseract_version()
                    TESSERACT_AVAILABLE = True
                    break
                except:
                    continue
except ImportError:
    TESSERACT_AVAILABLE = False


def validate_id_number(id_number):
    """
    验证身份证号码格式和校验位
    
    Args:
        id_number: 身份证号码字符串
        
    Returns:
        bool: 是否为有效的身份证号码
    """
    if not id_number or len(id_number) != 18:
        return False
    
    # 前17位必须是数字
    if not id_number[:17].isdigit():
        return False
    
    # 最后一位可以是数字或X
    if id_number[17] not in '0123456789Xx':
        return False
    
    # 校验位验证
    try:
        # 身份证号码加权因子
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        # 校验码对应值
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
        
        # 计算校验位
        sum_value = sum(int(id_number[i]) * weights[i] for i in range(17))
        check_code = check_codes[sum_value % 11]
        
        # 验证校验位
        return id_number[17].upper() == check_code
    except:
        return False


def compute_id_check_code(id17: str) -> Optional[str]:
    """
    根据前17位数字计算身份证校验位。
    """
    if not id17 or len(id17) != 17 or not id17.isdigit():
        return None

    # 身份证号码加权因子
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    # 校验码对应值
    check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

    sum_value = sum(int(id17[i]) * weights[i] for i in range(17))
    return check_codes[sum_value % 11]


def is_plausible_id_number(id_number: str) -> bool:
    """
    粗略判断身份证号码是否合理（不做严格行政区划校验）。

    规则：18位、前17位数字、生日字段可解析且不在未来。
    """
    if not id_number or len(id_number) != 18:
        return False
    if not id_number[:17].isdigit():
        return False
    if id_number[17] not in '0123456789Xx':
        return False

    birth = id_number[6:14]
    try:
        y = int(birth[0:4])
        m = int(birth[4:6])
        d = int(birth[6:8])
        dt = datetime(y, m, d)
        # 合理范围：1900~当前日期
        if y < 1900:
            return False
        if dt.date() > datetime.now().date():
            return False
    except Exception:
        return False

    return True


def extract_id_from_text(text):
    """
    从文本中提取18位身份证号码
    优先提取独立的18位序列，避免包含其他数字
    
    Args:
        text: 识别到的文本
        
    Returns:
        str: 提取到的身份证号码，如果未找到返回None
    """
    if not text:
        return None
    
    # 清理文本：只保留数字和X
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[^\dXx]', '', text)
    
    if not text:
        return None
    
    def _normalize_candidate(raw18: str) -> Tuple[Optional[str], bool, bool]:
        """
        返回 (candidate, is_valid_checksum, is_plausible)
        - 若校验位不通过但生日合理，则尝试用前17位计算校验位纠正最后一位。
        """
        if not raw18 or len(raw18) != 18:
            return None, False, False

        cand = raw18.upper()
        if not re.match(r'^\d{17}[\dXx]$', cand):
            return None, False, False

        plausible = is_plausible_id_number(cand)
        valid = validate_id_number(cand)

        # 如果生日/格式不合理，直接丢弃
        if not plausible:
            return None, False, False

        if valid:
            return cand, True, True

        # 生日合理但校验位不对：尝试纠正末位
        check_code = compute_id_check_code(cand[:17])
        if check_code:
            fixed = cand[:17] + check_code
            if validate_id_number(fixed):
                return fixed, True, True

        # 纠正失败：不返回，继续让外层尝试其他ROI/预处理/PSM
        return None, False, True

    # 1：如果文本正好是18位，但必须合理
    if len(text) == 18:
        candidate, _, _ = _normalize_candidate(text)
        if candidate:
            return candidate
    
    # 2：查找所有18位序列，优先选择校验位正确 + 独立序列 + 位置靠后
    pattern = r'\d{17}[\dXx]'
    matches = re.finditer(pattern, text)
    candidates = []
    
    for match in matches:
        normalized, is_valid, is_plausible = _normalize_candidate(match.group())
        if not normalized:
            continue
        id_candidate = normalized
        start_pos = match.start()
        end_pos = match.end()
        
        # 检查前后字符（在原始文本中检查，因为可能包含分隔符）
        # 但这里text已经清理过了，所以检查text中的位置
        before_char = text[start_pos - 1] if start_pos > 0 else ''
        after_char = text[end_pos] if end_pos < len(text) else ''
        
        # 计算候选的优先级
        priority = 0
        is_independent = not before_char.isdigit() and not after_char.isdigit()
        
        if is_independent:
            priority += 10  # 独立的序列优先级更高
        
        # 如果在校验位验证通过，优先级更高
        if is_valid:
            priority += 20
        
        # 如果位置靠后（身份证号码通常在末尾），优先级更高
        position_score = start_pos / max(len(text), 1)
        priority += position_score * 5
        
        candidates.append({
            'id': id_candidate,
            'priority': priority,
            'is_independent': is_independent,
            'is_valid': is_valid,
            'position': start_pos
        })
    
    if candidates:
        # 按优先级排序，优先选择：
        # 1. 校验位正确的
        # 2. 独立的序列（前后不是数字）
        # 3. 位置靠后的
        candidates.sort(key=lambda x: (-x['is_valid'], -x['is_independent'], -x['priority']))
        
        # 返回优先级最高的候选
        best_candidate = candidates[0]['id']
        return best_candidate
    
    # 3：如果文本长度大于18位，尝试滑动窗口查找所有可能的18位序列，必须合理
    # 从后往前查找，因为身份证号码通常在文本末尾
    if len(text) > 18:
        # 收集所有可能的18位候选
        window_candidates = []
        
        # 从后往前滑动窗口，最多向前查找10个位置
        start_pos = max(0, len(text) - 18 - 10)
        for i in range(len(text) - 18, start_pos - 1, -1):
            if i < 0:
                break
            candidate = text[i:i+18].upper()
            
            normalized, is_valid, is_plausible = _normalize_candidate(candidate)
            if normalized:
                # 检查前后字符
                before_char = text[i - 1] if i > 0 else ''
                after_char = text[i + 18] if i + 18 < len(text) else ''
                is_independent = not before_char.isdigit() and not after_char.isdigit()

                window_candidates.append({
                    'id': normalized,
                    'priority': (20 if is_valid else 0) + (10 if is_independent else 0) + (len(text) - i),
                    'is_independent': is_independent,
                    'is_valid': is_valid,
                    'position': i
                })
        
        if window_candidates:
            # 按优先级排序
            window_candidates.sort(key=lambda x: -x['priority'])
            best = window_candidates[0]['id']
            return best
        
        # 兜底：末尾18位尝试（但仍然要求生日合理；并自动纠正校验位）
        if len(text) >= 18:
            candidate, _, _ = _normalize_candidate(text[-18:])
            if candidate:
                return candidate
    
    return None


def recognize_id_number(image_path):
    """
    识别身份证号码
    使用OpenCV预处理 + OCR识别
    
    Args:
        image_path: 身份证图片路径
        
    Returns:
        str: 识别到的身份证号码，如果识别失败返回None
    """
    if not TESSERACT_AVAILABLE:
        return None
    
    try:
        print("=" * 60)
        print("开始识别身份证号码")
        print("=" * 60)
        
        # 读取原始图像
        img = cv2.imread(image_path)
        if img is None:
            print("无法读取图像文件")
            return None
        
        # 检查是否为彩色图像
        is_color_image = len(img.shape) == 3 and img.shape[2] == 3
        height, width = img.shape[:2]
        print(f"图像信息: {width}x{height} 像素, {'彩色' if is_color_image else '灰度'}图像")
        
        # 如果是彩色图片，进行去噪处理
        if is_color_image:
            print("对彩色图像进行去噪处理...")
            img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        
        # 如果图像太小，先放大
        if height < 400 or width < 600:
            scale = max(400 / height, 600 / width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            print(f"图像尺寸过小，放大 {scale:.2f} 倍: {new_width}x{new_height}")
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            height, width = img.shape[:2]
        
        # ROI区域配置（身份证号码通常在下方区域）
        roi_configs = [
            # 裁掉 公民身份证号码 文字，保留数字
            {'y_start': 0.78, 'y_end': 0.96, 'x_start': 0.25, 'x_end': 0.98, 'name': '号码数字区域(去左边文字)'},
            {'y_start': 0.76, 'y_end': 0.97, 'x_start': 0.20, 'x_end': 1.00, 'name': '号码数字区域(稍宽)'},
            {'y_start': 0.72, 'y_end': 0.92, 'x_start': 0.10, 'x_end': 0.90, 'name': '标准位置'},
            {'y_start': 0.70, 'y_end': 0.95, 'x_start': 0.05, 'x_end': 0.95, 'name': '宽范围'},
            {'y_start': 0.0, 'y_end': 1.0, 'x_start': 0.0, 'x_end': 1.0, 'name': '全图'},
        ]
        
        # PSM模式（Page Segmentation Mode）
        psm_modes = [('7', '单行文本'), ('11', '稀疏文本'), ('6', '统一文本块')]
        
        roi_index = 0
        for roi_config in roi_configs:
            roi_index += 1
            print(f"\n{'─' * 60}")
            print(f"ROI区域 {roi_index}/{len(roi_configs)}: {roi_config['name']}")
            print(f"{'─' * 60}")
            try:
                # 提取ROI区域
                roi_y_start = int(height * roi_config['y_start'])
                roi_y_end = int(height * roi_config['y_end'])
                roi_x_start = int(width * roi_config['x_start'])
                roi_x_end = int(width * roi_config['x_end'])
                
                roi = img[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
                
                if roi is None or roi.size == 0:
                    continue
                
                # 预处理方式
                processed_images = []
                processed_names = []
                
                # 检查是否为彩色图像
                is_color = len(roi.shape) == 3 and roi.shape[2] == 3
                print(f"  图像类型: {'彩色' if is_color else '灰度'}, ROI尺寸: {roi.shape[1]}x{roi.shape[0]}")
                
                if is_color:
                    # 彩色图片处理：尝试多种色彩空间提取最佳通道
                    print(" 生成预处理图像...")
                    
                    # 方式1：LAB色彩空间的L通道（亮度通道，通常效果最好）
                    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
                    l_channel = lab[:, :, 0]
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced_l = clahe.apply(l_channel)
                    _, binary_lab = cv2.threshold(enhanced_l, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    processed_images.append(binary_lab)
                    processed_names.append("LAB-L通道+OTSU")
                    
                    # 方式2：HSV色彩空间的V通道（明度通道）
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    v_channel = hsv[:, :, 2]
                    enhanced_v = clahe.apply(v_channel)
                    _, binary_hsv = cv2.threshold(enhanced_v, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    processed_images.append(binary_hsv)
                    processed_names.append("HSV-V通道+OTSU")
                    
                    # 方式3：LAB的L通道 + 自适应阈值
                    adaptive_lab = cv2.adaptiveThreshold(enhanced_l, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                         cv2.THRESH_BINARY, 11, 2)
                    processed_images.append(adaptive_lab)
                    processed_names.append("LAB-L通道+自适应阈值")
                    
                    # 方式4：使用灰度图（保留原有方法）
                    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    enhanced_gray = clahe.apply(gray)
                    _, binary_gray = cv2.threshold(enhanced_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    processed_images.append(binary_gray)
                    processed_names.append("灰度图+OTSU")
                    
                    # 方式5：灰度图 + 自适应阈值
                    adaptive_gray = cv2.adaptiveThreshold(enhanced_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                          cv2.THRESH_BINARY, 11, 2)
                    processed_images.append(adaptive_gray)
                    processed_names.append("灰度图+自适应阈值")
                    
                    # 方式6：反转LAB的L通道（深色背景）
                    inverted_l = cv2.bitwise_not(l_channel)
                    enhanced_inv_l = clahe.apply(inverted_l)
                    _, binary_inv_lab = cv2.threshold(enhanced_inv_l, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    processed_images.append(binary_inv_lab)
                    processed_names.append("反转LAB-L通道+OTSU")
                else:
                    # 灰度图处理（原有逻辑）
                    gray = roi if len(roi.shape) == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    print("  生成预处理图像...")
                    
                    # 方式1：CLAHE增强对比度 + OTSU二值化
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(gray)
                    _, binary1 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    processed_images.append(binary1)
                    processed_names.append("CLAHE+OTSU")
                    
                    # 方式2：自适应阈值
                    adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                     cv2.THRESH_BINARY, 11, 2)
                    processed_images.append(adaptive)
                    processed_names.append("CLAHE+自适应阈值")
                    
                    # 方式3：反转图像（如果背景是深色）
                    inverted = cv2.bitwise_not(gray)
                    clahe_inv = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced_inv = clahe_inv.apply(inverted)
                    _, binary_inv = cv2.threshold(enhanced_inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    processed_images.append(binary_inv)
                    processed_names.append("反转+CLAHE+OTSU")
                
                # 如果ROI太小，放大后再处理
                if roi.shape[0] < 200 or roi.shape[1] < 400:
                    scale_factor = max(200 / roi.shape[0], 400 / roi.shape[1], 2.0)
                    print(f"  ROI尺寸过小，放大 {scale_factor:.2f} 倍...")
                    roi_large = cv2.resize(roi, 
                                         (int(roi.shape[1] * scale_factor), 
                                          int(roi.shape[0] * scale_factor)), 
                                         interpolation=cv2.INTER_CUBIC)
                    
                    if is_color:
                        # 彩色图片放大后的处理
                        lab_large = cv2.cvtColor(roi_large, cv2.COLOR_BGR2LAB)
                        l_channel_large = lab_large[:, :, 0]
                        clahe_large = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                        enhanced_large = clahe_large.apply(l_channel_large)
                        _, binary_large = cv2.threshold(enhanced_large, 0, 255, 
                                                        cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        processed_images.append(binary_large)
                        processed_names.append("放大后LAB-L+OTSU")
                        
                        # 放大后的自适应阈值
                        adaptive_large = cv2.adaptiveThreshold(enhanced_large, 255, 
                                                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                               cv2.THRESH_BINARY, 11, 2)
                        processed_images.append(adaptive_large)
                        processed_names.append("放大后LAB-L+自适应阈值")
                    else:
                        # 灰度图放大后的处理
                        gray_large = roi_large if len(roi_large.shape) == 2 else cv2.cvtColor(roi_large, cv2.COLOR_BGR2GRAY)
                        clahe_large = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                        enhanced_large = clahe_large.apply(gray_large)
                        _, binary_large = cv2.threshold(enhanced_large, 0, 255, 
                                                        cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        processed_images.append(binary_large)
                        processed_names.append("放大后CLAHE+OTSU")
                
                # 对每种预处理图像尝试不同的PSM模式
                process_index = 0
                for processed_img, process_name in zip(processed_images, processed_names):
                    process_index += 1
                    print(f"\n  预处理方式 {process_index}/{len(processed_images)}: {process_name}")
                    
                    for psm, psm_desc in psm_modes:
                        try:
                            # 降噪
                            kernel = np.ones((2, 2), np.uint8)
                            cleaned = cv2.morphologyEx(processed_img, cv2.MORPH_CLOSE, kernel)
                            
                            # OCR识别 - 只识别数字和X/x
                            custom_config = (
                                f'--oem 3 --psm {psm} '
                                f'-c tessedit_char_whitelist=0123456789Xx '
                                f'-c classify_bln_numeric_mode=1'
                            )
                            text = pytesseract.image_to_string(cleaned, config=custom_config)
                            original_text = text.strip()
                            
                            # 显示识别过程
                            print(f"  PSM {psm} ({psm_desc}): 原始='{original_text}'", end="")
                            
                            # 使用改进的提取函数提取身份证号码
                            id_number = extract_id_from_text(text)
                            
                            if id_number:
                                # 验证校验位
                                is_valid = validate_id_number(id_number)
                                valid_mark = "YES" if is_valid else "NO"
                                print(f" -> {valid_mark} 提取成功: {id_number}", end="")
                                
                                if is_valid:
                                    print(" (校验位正确)")
                                else:
                                    print(" (校验位未通过，但格式正确)")
                                
                                print(f"\n{'=' * 60}")
                                print(f"识别成功！身份证号码: {id_number}")
                                if not is_valid:
                                    print(" 注意: 校验位验证未通过，请人工确认")
                                print(f"{'=' * 60}")
                                return id_number
                            else:
                                # 检查是否有部分数字
                                digits_only = re.sub(r'[^\dXx]', '', text)
                                if len(digits_only) >= 15:
                                    print(f" ->   部分识别: {digits_only} ({len(digits_only)}位)")
                                else:
                                    print(f" ->  未找到有效号码")
                            
                            # 如果白名单模式失败，尝试不使用白名单（仅在PSM 7模式下）
                            if psm == '7':
                                config_no_whitelist = f'--oem 3 --psm {psm}'
                                text_full = pytesseract.image_to_string(cleaned, config=config_no_whitelist)
                                original_full = text_full.strip()
                                
                                # 使用改进的提取函数
                                id_number = extract_id_from_text(text_full)
                                
                                if id_number:
                                    is_valid = validate_id_number(id_number)
                                    valid_mark = "YES" if is_valid else "NO"
                                    print(f"   无白名单模式: 原始='{original_full}' -> {valid_mark} 提取成功: {id_number}")
                                    print(f"\n{'=' * 60}")
                                    print(f"YES 识别成功！身份证号码: {id_number}")
                                    if not is_valid:
                                        print("NO  注意: 校验位验证未通过，请人工确认")
                                    print(f"{'=' * 60}")
                                    return id_number
                                
                        except Exception as e:
                            print(f"     PSM {psm} 识别出错: {str(e)}")
                            continue
                            
            except Exception as e:
                print(f"   ROI处理出错: {str(e)}")
                continue
        
        print(f"\n{'=' * 60}")
        print(" 识别失败: 所有方法均未识别到有效的18位身份证号码")
        print(f"{'=' * 60}")
        return None
    except Exception as e:
        print(f"\n{'=' * 60}")
        print(f" 身份证识别错误: {e}")
        print(f"{'=' * 60}")
        import traceback
        traceback.print_exc()
        return None

