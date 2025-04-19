import os
import sys
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess
    print("正在安装Pillow库...")
    subprocess.call([sys.executable, '-m', 'pip', 'install', 'Pillow'])
    from PIL import Image, ImageDraw, ImageFont

def create_fapiao_icon(output_filename='fapiao_icon.ico', also_create_png=True):
    """
    创建发票工具图标
    :param output_filename: 输出的ICO文件名
    :param also_create_png: 是否同时创建PNG格式图标
    """
    # 输出当前工作目录
    current_dir = os.path.abspath(os.path.dirname(__file__))
    print(f"当前工作目录: {current_dir}")
    
    # 确保输出文件名是绝对路径
    if not os.path.isabs(output_filename):
        output_filename = os.path.join(current_dir, output_filename)
        
    print(f"将创建图标文件: {output_filename}")
    
    # 创建图标 - 包含多个尺寸以符合Windows要求
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    
    # 为每个尺寸创建图标
    for size in sizes:
        # 创建图像
        img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 绘制圆形背景
        center = size // 2
        radius = size // 2 - max(1, size // 25)  # 保证小图标也有足够的边距
        
        # 使用鲜明的品牌色
        primary_color = (24, 144, 255)  # 蓝色
        secondary_color = (255, 255, 255)  # 白色
        
        # 绘制圆形背景
        draw.ellipse((center - radius, center - radius, center + radius, center + radius), 
                    fill=primary_color)
        
        # 绘制发票矩形
        rect_width = int(radius * 1.2)
        rect_height = int(radius * 1.5)
        left = center - rect_width // 2
        top = center - rect_height // 2
        
        # 保证矩形至少有1px边距
        left = max(1, left)
        top = max(1, top)
        right = min(size - 2, left + rect_width)
        bottom = min(size - 2, top + rect_height)
        
        # 绘制白色矩形（发票）
        draw.rectangle((left, top, right, bottom), fill=secondary_color)
        
        # 添加发票横线
        line_count = 4
        line_spacing = (bottom - top) // (line_count + 1)
        line_thickness = max(1, size // 96)  # 根据图标大小调整线条粗细
        
        for i in range(1, line_count + 1):
            y = top + i * line_spacing
            draw.line(
                (left + size//16, y, right - size//16, y), 
                fill=primary_color, 
                width=line_thickness
            )
        
        # 添加¥符号或其他标识
        try:
            symbol_size = int(rect_width * 0.5)
            if symbol_size > 0:
                # 尝试常见的系统字体
                font_names = ["arial", "segoeui", "simhei", "msyhbd", "verdana"]
                font = None
                
                for font_name in font_names:
                    try:
                        font = ImageFont.truetype(font_name, symbol_size)
                        break
                    except:
                        continue
                
                if font:
                    text_y_offset = -symbol_size // 8  # 轻微上移以视觉居中
                    draw.text(
                        (center, center + text_y_offset), 
                        "¥", 
                        fill=primary_color,
                        font=font,
                        anchor="mm"  # 居中
                    )
                else:
                    raise Exception("没有找到合适的字体")
        except Exception as e:
            print(f"无法使用字体，使用简单符号代替: {e}")
            # 如果无法使用字体，绘制简单的¥符号
            # 计算符号尺寸
            symbol_width = max(1, rect_width // 3)
            symbol_height = max(1, rect_height // 3)
            
            # 绘制垂直线
            draw.line(
                (center, center - symbol_height // 2, center, center + symbol_height // 2),
                fill=primary_color,
                width=max(1, line_thickness)
            )
            
            # 绘制两条横线
            draw.line(
                (center - symbol_width // 2, center - symbol_height // 4,
    # 创建图标 
    icon_sizes = [16, 32, 48, 64, 128, 256]  # Windows图标的常见尺寸
    icons = []
    
    for icon_size in icon_sizes:
        img = Image.new('RGBA', (icon_size, icon_size), color=(255, 255, 255, 0)) 
        draw = ImageDraw.Draw(img) 
        
        # 绘制圆形背景 
        center = icon_size // 2 
        radius = icon_size // 2 - max(2, icon_size // 25)  # 根据图标大小调整边距
        draw.ellipse((center-radius, center-radius, center+radius, center+radius), fill=(41, 128, 185)) 
        
        # 添加一个发票样式图标
        rect_width = radius * 1.2 
        rect_height = radius * 1.5 
        left = center - rect_width // 2 
        top = center - rect_height // 2 
        draw.rectangle((left, top, left + rect_width, top + rect_height), fill=(255, 255, 255)) 
        
        # 添加发票线条 
        line_spacing = rect_height // 6 
        line_thickness = max(1, icon_size // 100)  # 根据图标大小调整线条粗细
        for i in range(1, 5): 
            y = top + i * line_spacing 
            draw.line((left + 10, y, left + rect_width - 10, y), fill=(41, 128, 185), width=line_thickness) 
        
        # 添加¥符号 
        try: 
            # 尝试使用系统字体 
            font_size = int(rect_width // 2) 
            # 尝试多种常见字体
            font_names = ["arial", "simhei", "simsun", "msyh", "verdana", "tahoma", "segoeui"]
            font = None
            
            for font_name in font_names:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                    break
                except:
                    continue
                    
            if font:
                # 在较小图标上调整位置
                y_offset = -font_size//4 if icon_size >= 48 else 0
                draw.text((center, center + y_offset), "¥", fill=(41, 128, 185), font=font, anchor="mm")
            else:
                raise Exception("No font available")
        except Exception: 
            # 如果无法加载字体，则绘制一个简单的符号 
            vert_line_thickness = max(1, icon_size // 50)
            horiz_line_thickness = max(1, icon_size // 50)
            vert_line_length = rect_height // 3
            horiz_line_length = rect_width // 4
            
            # 垂直线
            draw.line((center, top + rect_height//3, center, top + rect_height*2//3), 
                      fill=(41, 128, 185), width=vert_line_thickness) 
            # 横线
            draw.line((center - horiz_line_length//2, top + rect_height//2, 
                       center + horiz_line_length//2, top + rect_height//2), 
                      fill=(41, 128, 185), width=horiz_line_thickness) 
        
        icons.append(img)
    
    # 保存为ico文件 (包含所有尺寸)
    largest_icon = icons[-1]  # 最大尺寸的图标
    
    try:
        # 保存ICO文件
        largest_icon.save(output_filename, format='ICO', sizes=[(size, size) for size in icon_sizes])
        print(f"已生成图标文件: {output_filename}")
        
        # 同时保存为PNG文件 (如果需要)
        if also_create_png:
            png_filename = os.path.splitext(output_filename)[0] + '.png'
            largest_icon.save(png_filename, format='PNG')
            print(f"已生成PNG图标: {png_filename}")
            
            # 列出当前目录中的图标文件
            icon_files = [f for f in os.listdir(current_dir) if f.endswith('.ico') or f.endswith('.png')]
            print(f"当前目录中的图标文件: {icon_files}")
            
        return output_filename
    except Exception as e:
        print(f"保存图标文件时出错: {e}")
        return None

if __name__ == "__main__":
    # 如果作为脚本运行，则创建图标
    create_fapiao_icon()
    
    # 生成各种格式的图标文件
    create_fapiao_icon('icon.ico')
    print("\n图标创建完成。可以通过build_exe_with_icon.bat打包带图标的可执行文件。")
