import fitz
import argparse
import os

def crop_pdf_margins(input_pdf_path: str, suffix: str, margin: int, export_per_page: bool) -> int:
    """自动裁剪PDF文件四周的空白，然后保存为新文件

    Args:
        input_pdf_path (str): 输入PDF文件路径
        output_pdf_path (str): 输出PDF文件路径
        margin (int): 裁剪时的内边距，单位为点
        export_per_page (bool): 是否为每一页单独导出裁剪后的PDF
    """
    saved_files_cnt = 0
    try:
        doc = fitz.open(input_pdf_path)
        base_name, ext = os.path.splitext(input_pdf_path)

        if export_per_page:
            # 按页裁剪并导出
            for page_num in range(len(doc)):
                page = doc[page_num] # 获取当前页面
                # 获取页面内容的边界框
                content_bbox = find_content_bounding_box(page, margin)

                new_single_page_doc = fitz.open() # 创建新的PDF文档
                new_page_in_doc = new_single_page_doc.new_page(
                    width=page.rect.width,
                    height=page.rect.height,
                    pno=0
                )
                new_page_in_doc.show_pdf_page(
                    new_page_in_doc.rect,
                    doc,
                    page_num
                )

                if content_bbox:
                    new_page_in_doc.set_cropbox(content_bbox) # 设置页面裁剪框
                    print(f"页面 {page_num + 1} 的裁剪框设置为: {content_bbox}")
                else:
                    print(f"页面 {page_num + 1} 没有找到内容边界框，跳过裁剪。")
                # 保存裁剪后的PDF
                output_pdf_path = f"{base_name}_page{page_num + 1}{suffix}{ext}"
                new_single_page_doc.save(output_pdf_path)
                new_single_page_doc.close()
                saved_files_cnt += 1
                print(f"页面 {page_num+1} 已裁剪并保存到: {output_pdf_path}")
        else:
            for page_num in range(len(doc)):
                page = doc[page_num] # 获取当前页面
                # 获取页面内容的边界框
                content_bbox = find_content_bounding_box(page, margin)

                if content_bbox:
                    # 设置页面裁剪框
                    # PyMuPDF的Rect对象的坐标是(x0, y0, x1, y1)
                    page.set_cropbox(content_bbox)
                    print(f"页面 {page_num + 1} 的裁剪框设置为: {content_bbox}")
                else:
                    print(f"页面 {page_num + 1} 没有找到内容边界框，跳过裁剪。")
            # 保存裁剪后的PDF
            output_pdf_path = f"{base_name}{suffix}{ext}"
            doc.save(output_pdf_path)
            doc.close()
            saved_files_cnt = 1
            print(f"裁剪后的PDF已保存到: {output_pdf_path}")
    except Exception as e:
        print(f"处理文件 {input_pdf_path} 时发生错误: {e}")
        saved_files_cnt = 0
    finally:
        if 'doc' in locals() and not doc.is_closed:
            doc.close()
    return saved_files_cnt


def find_content_bounding_box(page: fitz.Page, margin: int = 5) -> fitz.Rect | None:
    """尝试从页面中识别所有可见内容的最小外接矩形

    Args:
        page (fitz.Page): 输入页面对象

    Returns:
        fitz.Rect: 内容的最小外接矩形
    """
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')

    # 辅助函数：更新边界值
    def update_bounds(bbox: fitz.Rect):
        nonlocal min_x, min_y, max_x, max_y
        if bbox.width > 0 and bbox.height > 0:
            min_x = min(min_x, bbox.x0)
            min_y = min(min_y, bbox.y0)
            max_x = max(max_x, bbox.x1)
            max_y = max(max_y, bbox.y1)

    # 1. 检查文件内容
    text_blocks = page.get_text("blocks") # 获取文本块
    for block in text_blocks:
        bbox = fitz.Rect(block[:4]) # 获取文本块的边界框
        update_bounds(bbox)
    
    # 2. 检查图片内容
    images = page.get_images(full=True) # 获取图片
    for img_info in images:
        # img_info 是一个元组，包含图片的xref和bbox
        bbox = page.get_image_bbox(img_info) # 获取图片的边界框
        update_bounds(bbox)
    
    # 3. 检查矢量图形
    """
    page.get_drawings() 返回一个包含字典的列表，每个字典描述一个图形对象
    字典中通常包含 'rect' 键，表示图形的外接矩形
    """
    drawings = page.get_drawings()
    # 为什么PowerPoint导出的PDF，第一个drawing的rect总是y0<0?
    for draw_num in range(1, len(drawings)): # 从第二个图形开始
        draw = drawings[draw_num]
        if 'rect' in draw:
            bbox = fitz.Rect(draw['rect'])
            update_bounds(bbox)

    if min_x != float('inf'): # 如果检测到任何内容
        # 稍微增加一些内边距(margin)，以防内容边界过于贴近裁剪线
        # PDF的默认单位是点，1点 = 1/72英寸
        original_rect = page.rect # 页面原始矩形，确保裁剪不会超出页面边界

        final_x0 = max(min_x - margin, original_rect.x0)
        final_y0 = max(min_y - margin, original_rect.y0)
        final_x1 = min(max_x + margin, original_rect.x1)
        final_y1 = min(max_y + margin, original_rect.y1)
        content_bbox = fitz.Rect(final_x0, final_y0, final_x1, final_y1)
        if content_bbox.width > 0 and content_bbox.height > 0:
            return content_bbox
        else:
            # 如果计算出的裁剪框无效，返回None
            print("计算出的裁剪框无效，返回None")
            return None
    else:
        # 如果没有找到内容，返回None
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自动裁剪PDF文件四周的空白")
    parser.add_argument("--input_pdf", required=True, help="输入PDF文件路径")
    parser.add_argument("--suffix", default="_cropped", help="裁剪后文件的后缀")
    parser.add_argument("--margin", type=int, default=5, help="裁剪时的内边距，单位为点")
    parser.add_argument("--export_per_page", action="store_true", help="是否为每一页单独导出裁剪后的PDF")
    args = parser.parse_args()

    # 检查输入文件是否存在
    if not os.path.isfile(args.input_pdf):
        print(f"输入文件不存在: {args.input_pdf}")
        exit(1)
    
    # 检查文件扩展名
    if not args.input_pdf.lower().endswith('.pdf'):
        print("输入文件不是PDF格式")
        exit(1)

    # 检查内边距参数
    if args.margin < 0:
        print("内边距参数必须为非负整数")
        exit(1)

    # 调用裁剪函数
    crop_pdf_margins(args.input_pdf, args.suffix, args.margin, args.export_per_page)
