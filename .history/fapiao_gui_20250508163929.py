import os
import sys
import re
import pdfplumber
import logging
import traceback
import datetime
import glob
import shutil
import pandas as pd
from decimal import Decimal
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                             QVBoxLayout, QHBoxLayout, QFileDialog, QWidget, 
                             QTextEdit, QProgressBar, QCheckBox, QMessageBox,
                             QSplitter, QFrame, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal, QRect
from PySide6.QtGui import QFont, QIcon

# Nuitka打包说明:
# mingw64下载地址：https://github.com/brechtsanders/winlibs_mingw/releases/
# 使用以下命令进行打包:
# python -m nuitka --standalone --enable-plugin=pyside6 --windows-disable-console --windows-icon-from-ico=icon.ico --include-data-files=icon.ico=icon.ico fapiao_gui.py
# 
# 如果需要打包时包含更多资源文件，可以使用:
# --include-data-files=资源文件路径=目标路径
#
# 其他常用选项:
# --windows-company-name="公司名称"
# --windows-product-name="发票金额统计工具"
# --windows-file-version=1.0.0
# --windows-product-version=1.0.0
# --windows-file-description="发票金额统计工具"
# --windows-uac-admin

# 导入任务栏图标设置模块
try:
    from taskbar_icon import set_taskbar_icon, set_app_icon
    has_taskbar_module = True
except ImportError:
    has_taskbar_module = False

# 自定义日志处理器，只在有错误时写入文件
class ErrorOnlyFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
        # 文件是否已经创建的标志
        self._file_created = False
        
    def emit(self, record):
        # 只有当日志级别为ERROR或更高级别时才写入文件
        if record.levelno >= logging.ERROR:
            # 如果文件尚未创建，确保目录存在
            if not self._file_created:
                directory = os.path.dirname(self.baseFilename)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                self._file_created = True
            super().emit(record)

# 配置日志
def setup_logging(log_file="fapiao_error.log", enable_logging=False):
    """设置日志，只在出错时才记录到文件"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # 创建logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # 清除之前的处理器
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    
    # 添加控制台处理器 - 用于开发调试
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)
    
    # 只有在启用日志时才添加文件处理器
    if enable_logging:
        # 添加自定义文件处理器 - 只记录错误
        file_handler = ErrorOnlyFileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.ERROR)  # 只记录ERROR及以上级别
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)
    
    # 降低pdfplumber库的日志级别，减少警告信息
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    
    return logger

# 全局logger变量，初始化时禁用文件日志
logger = setup_logging(enable_logging=False)

# 清理之前的输出文件
def clean_output_files(failed_list_file=None, text_files=False, directory=None):
    """清理之前的输出文件"""
    cleaned_files = []
    
    # 清理失败列表文件
    if failed_list_file and os.path.exists(failed_list_file):
        try:
            os.remove(failed_list_file)
            cleaned_files.append(failed_list_file)
        except Exception as e:
            logger.error(f"清理失败列表文件 {failed_list_file} 失败: {str(e)}")
    
    # 清理文本文件
    if text_files and directory:
        try:
            # 查找目录及子目录中的所有 *_text.txt 文件
            text_file_pattern = os.path.join(directory, "**", "*_text.txt")
            text_files_list = glob.glob(text_file_pattern, recursive=True)
            
            for file_path in text_files_list:
                try:
                    os.remove(file_path)
                    cleaned_files.append(os.path.basename(file_path))
                except Exception:
                    pass
            
            if text_files_list:
                logger.info(f"已清理 {len(text_files_list)} 个提取文本文件")
        except Exception as e:
            logger.error(f"清理文本文件时出错: {str(e)}")
    
    if cleaned_files:
        logger.info(f"已清理 {len(cleaned_files)} 个旧输出文件")
    
    return cleaned_files

def extract_amount_from_pdf(pdf_path):
    """从PDF发票中提取金额"""
    try:
        logger.info(f"开始处理文件: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            try:
                for i, page in enumerate(pdf.pages):
                    logger.debug(f"提取第 {i+1} 页文本")
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
                    else:
                        logger.warning(f"第 {i+1} 页未提取到文本")
            except Exception as e:
                logger.error(f"提取页面文本时出错: {str(e)}")
                logger.debug(traceback.format_exc())
            
            if not text:
                logger.warning(f"未能从文件中提取任何文本: {os.path.basename(pdf_path)}")
                return Decimal('0.00')
                
            logger.debug(f"提取的文本长度: {len(text)}")
            
            # 记录原始文本以便调试
            if logger.level <= logging.DEBUG:
                debug_text_file = f"{os.path.splitext(pdf_path)[0]}_text.txt"
                try:
                    with open(debug_text_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                    logger.debug(f"已保存原始文本到: {debug_text_file}")
                except Exception as e:
                    logger.debug(f"保存原始文本失败: {str(e)}")
            
            # 1. 首先尝试匹配"价税合计"行的金额 - 最通用的模式
            amount_patterns = [
                # 标准格式
                r'价税合计[：:]\s*￥?\s*([0-9,]+\.[0-9]{2})',
                r'价税合计.*?小写[：:]\s*￥?\s*([0-9,]+\.[0-9]{2})',
                r'价税合计.*?¥\s*([0-9,]+\.[0-9]{2})',
                r'价税合计.*?￥\s*([0-9,]+\.[0-9]{2})',
                # 简化格式
                r'价税合计\s*([0-9,]+\.[0-9]{2})',
                # 带括号格式
                r'价税合计.*?\(¥\s*([0-9,]+\.[0-9]{2})\)',
                r'价税合计.*?\(￥\s*([0-9,]+\.[0-9]{2})\)',
                # 无空格格式
                r'价税合计[：:]￥([0-9,]+\.[0-9]{2})',
                r'价税合计[：:]¥([0-9,]+\.[0-9]{2})'
            ]
            
            for pattern in amount_patterns:
                logger.debug(f"尝试匹配模式: {pattern}")
                matches = re.findall(pattern, text)
                if matches:
                    amount_str = matches[0].replace(',', '')
                    logger.info(f"匹配到价税合计金额: {amount_str}")
                    return Decimal(amount_str)
            
            # 2. 尝试匹配表格格式中的数据行
            table_patterns = [
                # 尝试匹配可能的表格行，其中含有货物名称、金额等
                r'(?:合\s*计|小\s*计).*?([0-9,]+\.[0-9]{2}).*?([0-9,]+\.[0-9]{2}).*?([0-9,]+\.[0-9]{2})',
                # 可能在表格中有税额和税价合计的列
                r'(?:税价合计|含税合计).*?([0-9,]+\.[0-9]{2})'
            ]
            
            for pattern in table_patterns:
                logger.debug(f"尝试匹配表格模式: {pattern}")
                matches = re.findall(pattern, text)
                if matches:
                    # 如果是元组（多个捕获组），选择最后一个作为税价合计
                    if isinstance(matches[0], tuple):
                        amount_str = matches[0][-1].replace(',', '')
                    else:
                        amount_str = matches[0].replace(',', '')
                    logger.info(f"匹配到表格中的金额: {amount_str}")
                    return Decimal(amount_str)
            
            # 3. 尝试匹配常见的替代表述
            fallback_patterns = [
                # 常见替代表述
                r'合[计總]金额[：:]\s*￥?\s*([0-9,]+\.[0-9]{2})',
                r'小写[：:]\s*￥?\s*([0-9,]+\.[0-9]{2})',
                r'（小写）[：:]\s*￥?\s*([0-9,]+\.[0-9]{2})',
                # 金额+税额=价税合计的模式
                r'金额[：:]\s*￥?\s*([0-9,]+\.[0-9]{2}).*?税额[：:]\s*￥?\s*([0-9,]+\.[0-9]{2})',
                # 大写金额后面通常会有小写
                r'人民币[：:]\s*[零壹贰叁肆伍陆柒捌玖拾佰仟万亿元角分整]+\s*[(（]?¥?([0-9,]+\.[0-9]{2})',
                # 简单模式：尝试匹配发票上任何可能的金额
                r'[¥￥]\s*([0-9,]+\.[0-9]{2})',
                # 最后的备选方案：搜索类似金额的内容
                r'(?<!发票号码|\d)([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})(?!\d)'
            ]
            
            for pattern in fallback_patterns:
                logger.debug(f"尝试备用匹配模式: {pattern}")
                matches = re.findall(pattern, text)
                if matches:
                    # 如果是元组（如金额+税额模式），计算合计
                    if isinstance(matches[0], tuple) and len(matches[0]) >= 2:
                        try:
                            amount = Decimal(matches[0][0].replace(',', ''))
                            tax = Decimal(matches[0][1].replace(',', ''))
                            total = amount + tax
                            logger.warning(f"根据金额 {amount} 和税额 {tax} 计算出价税合计: {total}")
                            return total
                        except Exception as e:
                            logger.error(f"计算金额和税额时出错: {str(e)}")
                    
                    # 否则使用第一个匹配项
                    amount_str = matches[0].replace(',', '') if not isinstance(matches[0], tuple) else matches[0][0].replace(',', '')
                    logger.warning(f"在 {os.path.basename(pdf_path)} 中未找到'价税合计'，使用其他匹配项：{amount_str}")
                    return Decimal(amount_str)
            
            # 4. 检查是否有包含金额的关键词段落
            key_sections = [
                "价税合计", "税价合计", "合计金额", "小写", "大写", "人民币", "RMB", "CHY", "CNY"
            ]
            
            for section in key_sections:
                # 搜索包含关键词的段落
                match = re.search(f".{{0,50}}{section}.{{0,100}}", text)
                if match:
                    section_text = match.group(0)
                    logger.debug(f"找到关键段落: {section_text}")
                    # 在段落中寻找金额格式
                    amount_match = re.search(r'([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})', section_text)
                    if amount_match:
                        amount_str = amount_match.group(1).replace(',', '')
                        logger.warning(f"从段落中提取金额: {amount_str}")
                        return Decimal(amount_str)
            
            # 调试：输出部分文本内容以便分析
            logger.warning(f"无法在 {os.path.basename(pdf_path)} 中找到金额")
            if len(text) > 200:
                text_sample = text[:200] + "..." + text[-200:]
            else:
                text_sample = text
            logger.debug(f"文本样本: {text_sample}")
            
            return Decimal('0.00')
    except Exception as e:
        logger.error(f"处理PDF文件 {os.path.basename(pdf_path)} 时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        return Decimal('0.00')

def extract_invoice_number(pdf_path, text=None):
    """尝试从PDF发票中提取发票号码"""
    try:
        if text is None:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text()
        
        # 常见的发票号码模式
        patterns = [
            # 标准格式，右上角带"发票号码："的格式
            r'发票号码[：:]\s*(\d{8,30})',
            r'发票号码[：:]\s*(\d{10,12})',
            # 没有冒号的格式
            r'发票号码\s*(\d{8,30})',
            # 英文标记格式
            r'No[\.:]?\s*(\d{8,30})',
            r'No[\.:]?\s*(\d{10,12})',
            # 简化的"号码"格式
            r'号码[：:]\s*(\d{8,30})',
            # 尝试匹配特殊格式，如电子发票右上角的号码
            r'发票号码：\s*(\d{20})',
            r'发票号码：\s*(\d{10,30})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # 找到最长的匹配结果作为发票号码
                longest_match = max(matches, key=len)
                logger.info(f"成功提取发票号码: {longest_match}")
                return longest_match
        
        # 如果上述模式都没匹配到，尝试提取任何看起来像发票号码的数字序列
        # 电子发票号码通常很长（如20位）
        general_number_pattern = r'[\(（]?[发票号码No\.:\s：]*[\)）]?\s*(\d{10,30})\b'
        matches = re.findall(general_number_pattern, text)
        if matches:
            longest_match = max(matches, key=len)
            logger.warning(f"使用通用模式提取到疑似发票号码: {longest_match}")
            return longest_match
            
        logger.warning(f"未能提取到发票号码")
        return ""
    except Exception as e:
        logger.error(f"提取发票号码时出错: {str(e)}")
        return ""

def move_duplicate_invoice(pdf_path, tmp_dir):
    """将重复的发票文件移动到临时目录"""
    try:
        # 确保临时目录存在
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
            logger.info(f"创建临时目录: {tmp_dir}")
        
        # 构建目标路径
        filename = os.path.basename(pdf_path)
        target_path = os.path.join(tmp_dir, filename)
        
        # 如果目标文件已存在，添加时间戳
        if os.path.exists(target_path):
            base_name, ext = os.path.splitext(filename)
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            target_path = os.path.join(tmp_dir, f"{base_name}_{timestamp}{ext}")
        
        # 移动文件
        shutil.move(pdf_path, target_path)
        logger.info(f"已移动重复发票到: {target_path}")
        return target_path
    except Exception as e:
        logger.error(f"移动重复发票时出错: {str(e)}")
        return None

def extract_company_info(pdf_path, text=None):
    """尝试从PDF发票中提取购买方和销售方信息"""
    try:
        if text is None:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text()
        
        # 初始化结果字典
        result = {
            'buyer_name': '',
            'buyer_tax_id': '',
            'seller_name': '',
            'seller_tax_id': ''
        }
        
        # 尝试提取购买方信息
        buyer_name_patterns = [
            r'购买方名称[:：]\s*(.*?)(?:\s|$)',
            r'购买方[:：]\s*(.*?)(?:\s|$)',
            r'名称[:：]\s*(.*?)(?:\s|购买方|$)',
            r'购买方.*?名称[:：]\s*(.*?)(?:\s|$)'
        ]
        
        for pattern in buyer_name_patterns:
            matches = re.findall(pattern, text)
            if matches and matches[0].strip():
                result['buyer_name'] = matches[0].strip()
                break
        
        # 尝试提取购买方税号
        buyer_tax_patterns = [
            r'购买方.*?税号[:：]\s*([0-9A-Z]{15,20})',
            r'购买方.*?统一社会信用代码[:：]\s*([0-9A-Z]{15,20})',
            r'购买方.*?纳税人识别号[:：]\s*([0-9A-Z]{15,20})',
            r'纳税人识别号[:：]\s*([0-9A-Z]{15,20})',
            r'统一社会信用代码/纳税人识别号[:：]\s*([0-9A-Z]{15,20})',
            r'统一社会信用代码.*?[:：]\s*([0-9A-Z]{15,20})'
        ]
        
        for pattern in buyer_tax_patterns:
            matches = re.findall(pattern, text)
            if matches and matches[0].strip():
                result['buyer_tax_id'] = matches[0].strip()
                break
        
        # 尝试提取销售方信息
        seller_name_patterns = [
            r'销售方名称[:：]\s*(.*?)(?:\s|$)',
            r'销售方[:：]\s*(.*?)(?:\s|$)',
            r'销售方.*?名称[:：]\s*(.*?)(?:\s|$)'
        ]
        
        for pattern in seller_name_patterns:
            matches = re.findall(pattern, text)
            if matches and matches[0].strip():
                result['seller_name'] = matches[0].strip()
                break
        
        # 尝试提取销售方税号
        seller_tax_patterns = [
            r'销售方.*?税号[:：]\s*([0-9A-Z]{15,20})',
            r'销售方.*?统一社会信用代码[:：]\s*([0-9A-Z]{15,20})',
            r'销售方.*?纳税人识别号[:：]\s*([0-9A-Z]{15,20})'
        ]
        
        for pattern in seller_tax_patterns:
            matches = re.findall(pattern, text)
            if matches and matches[0].strip():
                result['seller_tax_id'] = matches[0].strip()
                break
                
        # 如果上面的模式没有匹配到，尝试更常见的模式
        if not result['buyer_name'] or not result['seller_name']:
            # 针对发票第一行的购买方和销售方
            lines = text.split('\n')
            for line in lines:
                # 尝试查找包含"名称"的行
                if '名称' in line and ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        # 检查是否包含"购买方"或"销售方"
                        if '购买方' in parts[0]:
                            result['buyer_name'] = parts[1].strip()
                        elif '销售方' in parts[0]:
                            result['seller_name'] = parts[1].strip()
        
        # 针对发票中带有"统一社会信用代码/纳税人识别号"的情况
        if not result['buyer_tax_id'] or not result['seller_tax_id']:
            tax_id_pattern = r'统一社会信用代码[/／]?纳税人识别号[:：]?\s*([0-9A-Z]{15,20})'
            matches = re.findall(tax_id_pattern, text)
            if matches:
                # 根据上下文判断是买方还是卖方
                if not result['buyer_tax_id']:
                    result['buyer_tax_id'] = matches[0]
                elif not result['seller_tax_id'] and len(matches) > 1:
                    result['seller_tax_id'] = matches[1]
        
        # 针对特殊格式的发票，如示例中的电子发票
        # 查找"名称:"后面的内容作为公司名称
        special_name_pattern = r'名称[：:]\s*(.*?)(?:\s|$)'
        special_tax_id_pattern = r'统一社会信用代码[/／]纳税人识别号[：:]\s*([0-9A-Z]+)'
        
        special_name_matches = re.findall(special_name_pattern, text)
        special_tax_id_matches = re.findall(special_tax_id_pattern, text)
        
        if special_name_matches and len(special_name_matches) >= 2:
            if not result['buyer_name']:
                result['buyer_name'] = special_name_matches[0].strip()
            if not result['seller_name'] and len(special_name_matches) > 1:
                result['seller_name'] = special_name_matches[1].strip()
        
        if special_tax_id_matches and len(special_tax_id_matches) >= 2:
            if not result['buyer_tax_id']:
                result['buyer_tax_id'] = special_tax_id_matches[0].strip()
            if not result['seller_tax_id'] and len(special_tax_id_matches) > 1:
                result['seller_tax_id'] = special_tax_id_matches[1].strip()
        
        # 记录结果
        if result['buyer_name'] or result['seller_name']:
            logger.info(f"提取到购买方: {result['buyer_name']}, 税号: {result['buyer_tax_id']}")
            logger.info(f"提取到销售方: {result['seller_name']}, 税号: {result['seller_tax_id']}")
        else:
            logger.warning("未能提取到公司信息")
        
        return result
    except Exception as e:
        logger.error(f"提取公司信息时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        return {'buyer_name': '', 'buyer_tax_id': '', 'seller_name': '', 'seller_tax_id': ''}

def export_to_excel(data, excel_path):
    """将发票数据导出到Excel文件"""
    try:
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 设置列顺序
        columns = [
            'invoice_number', 'amount', 
            'buyer_name', 'buyer_tax_id', 
            'seller_name', 'seller_tax_id',
            'path'
        ]
        
        # 过滤仅包含需要的列
        available_columns = [col for col in columns if col in df.columns]
        df = df[available_columns]
        
        # 重命名列为中文
        column_mapping = {
            'invoice_number': '发票号码',
            'amount': '发票金额',
            'buyer_name': '购买方名称',
            'buyer_tax_id': '购买方税号',
            'seller_name': '销售方名称',
            'seller_tax_id': '销售方税号',
            'path': '文件路径'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # 导出到Excel
        df.to_excel(excel_path, index=False, engine='openpyxl')
        logger.info(f"已成功导出数据到Excel文件: {excel_path}")
        return True
    except Exception as e:
        logger.error(f"导出Excel文件时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

# 工作线程，用于处理发票
class WorkerThread(QThread):
    update_progress = Signal(int, int)  # 更新进度信号：当前处理数, 总数
    update_log = Signal(str)  # 更新日志信号
    finished_processing = Signal(dict)  # 处理完成信号，包含结果数据
    
    def __init__(self, directory, failed_list_file=None, save_debug_text=False, enable_logging=False):
        super().__init__()
        self.directory = directory
        self.failed_list_file = failed_list_file
        self.save_debug_text = save_debug_text
        self.enable_logging = enable_logging
        
    def run(self):
        try:
            self.update_log.emit(f"开始扫描目录: {self.directory}")
            
            # 配置日志级别
            global logger
            if self.save_debug_text:
                self.update_log.emit("已启用保存文本内容")
                logger = setup_logging(enable_logging=self.enable_logging)
                logging.getLogger(__name__).setLevel(logging.DEBUG)
            
            # 统计结果
            total_amount = Decimal('0.00')
            total_count = 0
            failed_count = 0
            duplicate_count = 0
            failed_list = []
            success_list = []
            duplicate_list = []
            
            # 存储已处理的发票号码，用于检测重复
            processed_invoice_numbers = {}
            
            # 创建临时目录用于保存重复发票
            tmp_dir = os.path.join(self.directory, "tmp_duplicates")
            
            # 验证目录是否存在
            if not os.path.exists(self.directory):
                self.update_log.emit(f"错误: 目录不存在: {self.directory}")
                self.finished_processing.emit({
                    'success': False,
                    'error': f"目录不存在: {self.directory}"
                })
                return
            
            if not os.path.isdir(self.directory):
                self.update_log.emit(f"错误: 路径不是目录: {self.directory}")
                self.finished_processing.emit({
                    'success': False,
                    'error': f"路径不是目录: {self.directory}"
                })
                return
            
            # 先统计所有PDF文件
            all_pdf_files = []
            for root, _, files in os.walk(self.directory):
                # 跳过tmp_duplicates目录
                if os.path.basename(root) == "tmp_duplicates":
                    continue
                    
                for file in files:
                    if file.lower().endswith('.pdf'):
                        all_pdf_files.append(os.path.join(root, file))
            
            total_files = len(all_pdf_files)
            self.update_log.emit(f"共发现 {total_files} 个PDF文件")
            
            # 遍历处理PDF文件
            for index, pdf_path in enumerate(all_pdf_files):
                try:
                    self.update_progress.emit(index + 1, total_files)
                    self.update_log.emit(f"处理文件 ({index + 1}/{total_files}): {os.path.basename(pdf_path)}")
                    
                    # 提取发票号码
                    invoice_number = extract_invoice_number(pdf_path)
                    
                    # 检查发票号码是否重复
                    if invoice_number and invoice_number in processed_invoice_numbers:
                        # 发现重复发票
                        duplicate_count += 1
                        duplicate_info = {
                            'path': pdf_path,
                            'filename': os.path.basename(pdf_path),
                            'invoice_number': invoice_number,
                            'original_path': processed_invoice_numbers[invoice_number]['path']
                        }
                        duplicate_list.append(duplicate_info)
                        
                        # 将重复发票移动到临时目录
                        moved_path = move_duplicate_invoice(pdf_path, tmp_dir)
                        if moved_path:
                            duplicate_info['moved_to'] = moved_path
                            self.update_log.emit(f"发现重复发票号码: {invoice_number}，已移动到: {moved_path}")
                        else:
                            self.update_log.emit(f"发现重复发票号码: {invoice_number}，但移动失败")
                        
                        continue  # 跳过后续处理
                    
                    amount = extract_amount_from_pdf(pdf_path)
                    if amount > 0:
                        total_amount += amount
                        total_count += 1
                        success_info = {
                            'path': pdf_path,
                            'filename': os.path.basename(pdf_path),
                            'amount': amount,
                            'invoice_number': invoice_number
                        }
                        success_list.append(success_info)
                        
                        # 记录成功处理的发票号码
                        if invoice_number:
                            processed_invoice_numbers[invoice_number] = success_info
                            
                        self.update_log.emit(f"成功提取金额: {amount}" + (f", 发票号码: {invoice_number}" if invoice_number else ""))
                    else:
                        failed_count += 1
                        failed_list.append(pdf_path)
                        self.update_log.emit(f"警告: 无法提取金额")
                except Exception as e:
                    failed_count += 1
                    failed_list.append(pdf_path)
                    self.update_log.emit(f"错误: 处理失败: {str(e)}")
            
            # 如果有匹配失败的发票，保存到文件
            if failed_list and self.failed_list_file:
                try:
                    with open(self.failed_list_file, 'w', encoding='utf-8') as f:
                        f.write(f"# 匹配失败的发票列表 - 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"# 总计: {len(failed_list)} 个发票\n\n")
                        for path in failed_list:
                            f.write(f"{path}\n")
                    self.update_log.emit(f"已将 {len(failed_list)} 个匹配失败的发票路径保存到文件: {self.failed_list_file}")
                except Exception as e:
                    self.update_log.emit(f"保存匹配失败列表时出错: {str(e)}")
            
            # 如果有重复的发票，也保存到文件
            if duplicate_list:
                duplicate_list_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "duplicate_fapiao.txt")
                try:
                    with open(duplicate_list_file, 'w', encoding='utf-8') as f:
                        f.write(f"# 重复发票列表 - 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"# 总计: {len(duplicate_list)} 个重复发票\n")
                        f.write(f"# 重复发票已移动到: {tmp_dir}\n\n")
                        for info in duplicate_list:
                            f.write(f"发票号码: {info['invoice_number']}\n")
                            f.write(f"文件路径: {info['path']}\n")
                            f.write(f"与此文件重复: {info['original_path']}\n")
                            if 'moved_to' in info:
                                f.write(f"已移动到: {info['moved_to']}\n")
                            f.write("-" * 50 + "\n")
                    self.update_log.emit(f"已将 {len(duplicate_list)} 个重复发票信息保存到文件: {duplicate_list_file}")
                except Exception as e:
                    self.update_log.emit(f"保存重复发票列表时出错: {str(e)}")
            
            # 发送处理完成信号
            self.finished_processing.emit({
                'success': True,
                'total_amount': total_amount,
                'total_count': total_count,
                'failed_count': failed_count,
                'duplicate_count': duplicate_count,
                'failed_list': failed_list,
                'success_list': success_list,
                'duplicate_list': duplicate_list
            })
            
        except Exception as e:
            self.update_log.emit(f"处理过程中发生错误: {str(e)}")
            self.update_log.emit(traceback.format_exc())
            self.finished_processing.emit({
                'success': False,
                'error': str(e)
            })

# 获取应用图标路径
def get_app_icon_path():
    # 首先尝试查找ico文件
    if getattr(sys, 'frozen', False):
        # 运行编译后的EXE
        base_path = os.path.dirname(sys.executable)
    else:
        # 运行脚本
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # 修改优先级顺序，优先使用icon.ico
    icon_candidates = [
        os.path.join(base_path, "icon.ico"),  # 现有图标文件优先
        os.path.join(base_path, "fapiao_icon.ico"),
        os.path.join(base_path, "temp_icon.ico"),
        os.path.join(base_path, "icon.png")
    ]
    
    for icon_path in icon_candidates:
        if os.path.exists(icon_path):
            print(f"使用图标文件: {icon_path}")  # 添加日志输出便于调试
            return icon_path
    
    return None

# 主窗口
class FapiaoCounterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置应用图标
        icon_path = get_app_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_ui()
        self.worker = None
        
        # 窗口居中显示
        self.center_window()
        
    def center_window(self):
        """将窗口居中显示在屏幕上"""
        # 获取屏幕可用区域
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        # 计算窗口居中位置
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        # 移动窗口
        self.move(x, y)
        
    def init_ui(self):
        # 设置窗口属性
        self.setWindowTitle("发票金额统计工具")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部控制区域
        top_controls = QGroupBox("设置")
        top_layout = QVBoxLayout(top_controls)
        
        # 第一行：目录选择
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("发票目录:")
        self.dir_path = QLabel("未选择")
        self.dir_button = QPushButton("浏览...")
        self.dir_button.clicked.connect(self.select_directory)
        
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.dir_path, 1)
        dir_layout.addWidget(self.dir_button)
        top_layout.addLayout(dir_layout)
        
        # 第二行：选项区域
        options_layout = QHBoxLayout()
        
        # 保存文本选项
        self.save_text_checkbox = QCheckBox("保存提取的文本内容")
        self.save_text_checkbox.setToolTip("启用此选项将保存从PDF中提取的原始文本，便于调试")
        
        # 清理文件选项
        self.clean_files_checkbox = QCheckBox("清理历史文件")
        self.clean_files_checkbox.setChecked(True)
        self.clean_files_checkbox.setToolTip("启用此选项将在处理前清理之前生成的日志和输出文件")
        
        # 添加生成日志选项
        self.enable_logging_checkbox = QCheckBox("生成错误日志")
        self.enable_logging_checkbox.setChecked(False)  # 默认不选中
        self.enable_logging_checkbox.setToolTip("启用此选项将记录处理过程中的错误到日志文件")
        self.enable_logging_checkbox.stateChanged.connect(self.toggle_logging)
        
        options_layout.addWidget(self.save_text_checkbox)
        options_layout.addWidget(self.clean_files_checkbox)
        options_layout.addWidget(self.enable_logging_checkbox)
        options_layout.addStretch(1)
        
        # 开始处理按钮
        self.start_button = QPushButton("开始处理")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_processing)
        options_layout.addWidget(self.start_button)
        
        top_layout.addLayout(options_layout)
        main_layout.addWidget(top_controls)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(10)
        main_layout.addWidget(splitter, 1)
        
        # 进度和日志区域
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        # 进度条
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("进度:")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v/%m - %p%")
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar, 1)
        log_layout.addLayout(progress_layout)
        
        # 日志区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text, 1)
        
        # 结果区域
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)
        
        results_label = QLabel("统计结果")
        results_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        results_label.setFont(font)
        results_layout.addWidget(results_label)
        
        # 结果显示
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        font = QFont("Consolas", 10)
        self.results_text.setFont(font)
        results_layout.addWidget(self.results_text)
        
        # 添加到分割器
        splitter.addWidget(log_widget)
        splitter.addWidget(results_widget)
        splitter.setSizes([300, 200])
        
        # 设置初始日志
        self.add_log("程序已启动，请选择包含发票的目录")
    
    def select_directory(self):
        """打开文件选择对话框，选择发票目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择发票目录")
        # 在PySide6中，如果用户取消选择，将返回空字符串
        if directory:
            self.dir_path.setText(directory)
            self.log_text.clear()  # 清空日志文本
            self.add_log(f"已选择目录: {directory}")
            
            # 检查目录
            if os.path.exists(directory) and os.path.isdir(directory):
                # 统计目录中的PDF文件
                pdf_files = []
                for root, _, files in os.walk(directory):
                    pdf_files.extend([os.path.join(root, file) for file in files if file.lower().endswith('.pdf')])
                
                if pdf_files:
                    self.add_log(f"发现 {len(pdf_files)} 个PDF文件")
                    self.start_button.setEnabled(True)
                else:
                    self.add_log("警告: 所选目录中没有找到PDF文件")
                    self.start_button.setEnabled(False)
            else:
                self.add_log("错误: 所选路径不是有效目录")
                self.start_button.setEnabled(False)
    
    def add_log(self, message):
        self.log_text.append(message)
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def toggle_logging(self, state):
        """启用或禁用日志记录"""
        global logger
        enable_logging = state == Qt.Checked
        logger = setup_logging(enable_logging=enable_logging)
        if enable_logging:
            self.add_log("已启用错误日志记录")
        else:
            self.add_log("已禁用错误日志记录")
    
    def start_processing(self):
        # 禁用开始按钮，防止重复点击
        self.start_button.setEnabled(False)
        self.dir_button.setEnabled(False)
        
        # 清空结果
        self.results_text.clear()
        
        # 获取设置
        directory = self.dir_path.text()
        save_debug_text = self.save_text_checkbox.isChecked()
        clean_files = self.clean_files_checkbox.isChecked()
        enable_logging = self.enable_logging_checkbox.isChecked()
        
        # 确保使用当前的日志设置
        global logger
        logger = setup_logging(enable_logging=enable_logging)
        
        # 失败列表文件路径
        failed_list_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failed_fapiao.txt")
        
        # 清理历史文件
        if clean_files:
            self.add_log("正在清理历史文件...")
            clean_output_files(failed_list_file, save_debug_text, directory)
        
        # 重置进度条
        self.progress_bar.setValue(0)
        
        # 创建并启动工作线程
        self.worker = WorkerThread(directory, failed_list_file, save_debug_text, enable_logging)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.update_log.connect(self.add_log)
        self.worker.finished_processing.connect(self.processing_finished)
        self.worker.start()
    
    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
    
    def processing_finished(self, result):
        # 重新启用控件
        self.start_button.setEnabled(True)
        self.dir_button.setEnabled(True)
        
        if not result['success']:
            QMessageBox.critical(self, "处理错误", f"处理过程中发生错误:\n{result.get('error', '未知错误')}")
            return
        
        # 显示统计结果
        total_amount = result['total_amount']
        total_count = result['total_count']
        failed_count = result['failed_count']
        duplicate_count = result['duplicate_count']
        
        # 格式化金额，加入千位分隔符
        formatted_amount = "{:,.2f}".format(total_amount)
        
        results_text = f"""
统计结果:
-------------------------------
发票总数: {total_count + failed_count + duplicate_count} 个
成功识别: {total_count} 个
识别失败: {failed_count} 个
重复发票: {duplicate_count} 个
总金额: {formatted_amount} 元
-------------------------------
"""
        if failed_count > 0:
            failed_list_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failed_fapiao.txt")
            results_text += f"\n注意: 有 {failed_count} 个发票无法识别金额，详情请查看:\n{failed_list_file}"
        
        if duplicate_count > 0:
            results_text += f"\n注意: 有 {duplicate_count} 个重复发票，详情请查看:\n{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'duplicate_fapiao.txt')}"
        
        # 添加日志文件信息
        if self.enable_logging_checkbox.isChecked():
            log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fapiao_error.log")
            if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                results_text += f"\n错误日志已保存到:\n{log_file}"
                
        # 显示结果
        self.results_text.setText(results_text)
        self.add_log(f"处理完成: 共 {total_count} 个发票，总金额 {formatted_amount} 元")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序图标 - 用于任务栏和左上角
    # 首先尝试使用taskbar_icon模块
    icon_set = False
    if has_taskbar_module:
        icon_set = set_app_icon(app)
    
    # 如果taskbar_icon模块不可用或设置失败，使用内部函数
    if not icon_set:
        icon_path = get_app_icon_path()
        if icon_path:
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon)
    
    window = FapiaoCounterApp()
    window.show()
    sys.exit(app.exec()) 