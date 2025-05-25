import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading # 用于异步处理，避免GUI卡死

from pdf_cropper import crop_pdf_margins

import math # 用于文件大小计算

# 导入拖拽库
from tkinterdnd2 import DND_FILES, TkinterDnD


# 将ctk.CTk() 替换为 TkinterDnD.Tk() 来支持拖拽
class PDFCropperApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__() # 调用CustomTkinter的初始化
        self.TkdndVersion = TkinterDnD._require(self)

        # 1. 窗口基本设置
        self.title("PDF White Space Cropper")
        self.geometry("800x600")
        self.resizable(True, True)

        # 配置网格布局，让组件随着窗口大小变化
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # 顶部区域（文件选择）不随行高变化
        self.grid_rowconfigure(1, weight=1) # 文件列表区域随行高变化
        self.grid_rowconfigure(2, weight=0) # 底部区域（操作）不随行高变化
        self.grid_rowconfigure(3, weight=0) # 进度条区域不随行高变化

        # 存储已选择PDF文件路径
        self.selected_pdf_files = []

        # 2. 创建主框架
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=10, pady=10)

        # 内部组件自适应
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=0)
        self.main_frame.grid_rowconfigure(3, weight=0)

        # 3. 创建顶部区域（文件选择）
        self.file_select_frame = ctk.CTkFrame(self.main_frame)
        self.file_select_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.file_select_frame.grid_columnconfigure(0, weight=1)
        self.file_select_frame.grid_columnconfigure(1, weight=1)

        self.select_files_button = ctk.CTkButton(
            self.file_select_frame,
            text="选择PDF文件",
            command=self.select_pdf_files
        )
        self.select_files_button.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.clear_list_button = ctk.CTkButton(
            self.file_select_frame,
            text="清空列表",
            command=self.clear_file_list
        )
        self.clear_list_button.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # 4. 创建文件列表区域
        # self.file_list_frame = ctk.CTkFrame(self.main_frame)
        # self.file_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        # self.file_list_frame.grid_rowconfigure(0, weight=1)
        # self.file_list_frame.grid_columnconfigure(0, weight=1)

        # # 使用 CTkTextbox 来显示文件列表，并提供滚动条
        # self.file_list_textbox = ctk.CTkTextbox(
        #     self.file_list_frame,
        #     wrap="none", # 不自动换行
        #     state="disabled" # 默认禁用，不允许用户直接编辑
        # )
        # self.file_list_textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # 变成可滚动的表格容器
        self.file_list_container = ctk.CTkScrollableFrame(self.main_frame)
        self.file_list_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        # 表格配置列
        self.file_list_container.grid_columnconfigure(0, weight=0) # 序号
        self.file_list_container.grid_columnconfigure(1, weight=1) # 文件路径
        self.file_list_container.grid_columnconfigure(2, weight=0) # 文件大小
        self.file_list_container.grid_columnconfigure(3, weight=0) # 操作按钮1
        self.file_list_container.grid_columnconfigure(4, weight=0) # 操作按钮2

        # 拖拽功能绑定
        self.file_list_container.drop_target_register(DND_FILES)
        self.file_list_container.dnd_bind('<<Drop>>', self.handle_drop)

        # 初始化时候显示拖拽提示
        self.drag_hint_label = ctk.CTkLabel(
            self.file_list_container,
            text="拖拽PDF文件到此处",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="gray"
        )
        # 放置在中间
        self.drag_hint_label.grid(row=0, column=0, columnspan=5, padx=20, pady=50, sticky="nsew")

        # 5. 创建底部操作区域（后缀输入、内边距输入、开始按钮）
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.controls_frame.grid_columnconfigure(0, weight=0) # Label - 后缀
        self.controls_frame.grid_columnconfigure(1, weight=1) # Entry - 后缀
        self.controls_frame.grid_columnconfigure(2, weight=0) # Label - 内边距
        self.controls_frame.grid_columnconfigure(3, weight=1) # Entry - 内边距
        self.controls_frame.grid_columnconfigure(4, weight=0) # Checkbox - 每页导出选项
        self.controls_frame.grid_columnconfigure(5, weight=0) # Button - 开始裁剪

        self.suffix_label = ctk.CTkLabel(self.controls_frame, text="输出后缀:")
        self.suffix_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.suffix_entry = ctk.CTkEntry(self.controls_frame, placeholder_text="_cropped")
        self.suffix_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.suffix_entry.insert(0, "_cropped") # 默认值

        self.margin_label = ctk.CTkLabel(self.controls_frame, text="内边距(点):")
        self.margin_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.margin_entry = ctk.CTkEntry(self.controls_frame, placeholder_text="5")
        self.margin_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.margin_entry.insert(0, "5") # 默认值

        # 新增的复选框
        self.export_per_page_checkbox = ctk.CTkCheckBox(
            self.controls_frame,
            text="每页导出为单独文件",
            onvalue=True, 
            offvalue=False,
        )
        self.export_per_page_checkbox.grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.export_per_page_checkbox.select() # 默认选中

        self.start_button = ctk.CTkButton(
            self.controls_frame,
            text="开始裁剪",
            command=self.start_processing
        )
        self.start_button.grid(row=0, column=5, padx=5, pady=5, sticky="e")

        # 6. 创建进度条区域
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="状态: 等待选择文件...")
        self.progress_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 7. 绑定文件列表的双击事件，允许移除文件
        # 改成按钮操作
        # self.file_list_textbox.bind("<Double-Button-1>", self.remove_selected_file)

        # 初始更新文件列表显示
        self.update_file_list_display()

    
    def format_bytes(self, size_bytes):
        """格式化文件大小为易读的B，KB，MB等"""
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
    

    def handle_drop(self, event):
        """处理拖拽文件事件。"""
        # event.data 包含了拖拽进来的文件路径，通常是一个空格分隔的字符串
        # 对于Windows，路径可能包含大括号 {}
        paths_str = event.data.strip()
        if paths_str.startswith('{') and paths_str.endswith('}'):
            # 移除大括号，并按空格分割（如果路径中没有空格）
            # 更稳健的方法是使用 shlex.split 但这里假设简单的路径
            paths = paths_str[1:-1].split('} {')
        else:
            paths = paths_str.split(' ') # macOS/Linux 可能直接是空格分隔

        pdf_paths = [p for p in paths if p.lower().endswith(".pdf")]
        if pdf_paths:
            self._add_files_to_list(pdf_paths)
            self.progress_label.configure(text=f"状态: 已拖入 {len(pdf_paths)} 个文件。")
        else:
            messagebox.showwarning("文件类型错误", "请拖入有效的PDF文件。")
    

    def _add_files_to_list(self, new_file_paths):
        """将新的文件路径添加到列表中，并避免重复。"""
        current_paths_set = set(self.selected_pdf_files)
        added_count = 0
        for path in new_file_paths:
            if path not in current_paths_set:
                self.selected_pdf_files.append(path)
                current_paths_set.add(path)
                added_count += 1
        
        # 确保排序，以便显示顺序一致
        self.selected_pdf_files.sort()
        
        if added_count > 0:
            self.update_file_list_display()
            self.progress_label.configure(text=f"状态: 已添加 {added_count} 个文件。当前 {len(self.selected_pdf_files)} 个文件。")

    
    def select_pdf_files(self):
        """打开文件对话框，选择一个或多个PDF文件。"""
        file_paths = filedialog.askopenfilenames(
            title="选择PDF文件",
            filetypes=[("PDF files", "*.pdf")]
        )
        if file_paths:
            # 清空当前文件列表
            self._add_files_to_list(file_paths)


    def clear_file_list(self):
        """清空文件列表"""
        if messagebox.askyesno("清空确认", "确定要清空文件列表吗？"):
            self.selected_pdf_files = []
            self.update_file_list_display()
            self.progress_label.configure(text="状态：文件列表已清空。")
            self.select_files_button.configure(state="normal")
            self.start_button.configure(state="normal")

    def update_file_list_display(self):
        """更新文件列表显示区域的内容(表格形式)"""
        # 清空之前的表格内容
        for widget in self.file_list_container.winfo_children():
            widget.destroy()

        if not self.selected_pdf_files:
            # 显示拖拽提示
            self.drag_hint_label = ctk.CTkLabel(
                self.file_list_container,
                text="将PDF文件拖入此处",
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color="gray"
            )
            self.drag_hint_label.grid(row=0, column=0, columnspan=5, sticky="nsew", padx=20, pady=50)
            return

        # 隐藏拖拽提示 (如果它存在)
        if hasattr(self, 'drag_hint_label') and self.drag_hint_label.winfo_exists():
            self.drag_hint_label.destroy()

        # 表格头部
        headers = ["序号", "文件名", "文件大小", "操作"]
        for col, header_text in enumerate(headers):
            ctk.CTkLabel(
                self.file_list_container,
                text=header_text,
                font=ctk.CTkFont(weight="bold")
            ).grid(row=0, column=col, padx=5, pady=5, sticky="w" if col == 1 else "nsew")

        # 表格内容
        for i, path in enumerate(self.selected_pdf_files):
            row_num = i + 1
            try:
                file_name = os.path.basename(path)
                file_size_bytes = os.path.getsize(path)
                file_size_formatted = self.format_bytes(file_size_bytes)
            except Exception as e:
                file_name = f"文件不存在或错误 ({os.path.basename(path)})"
                file_size_formatted = "错误"
                print(f"获取文件信息失败: {e}")

            # 序号
            ctk.CTkLabel(
                self.file_list_container, 
                text=str(row_num)
            ).grid(
                row=row_num, column=0, padx=5, pady=2, sticky="w"
            )
            # 文件名
            ctk.CTkLabel(
                self.file_list_container, 
                text=file_name
            ).grid(
                row=row_num, column=1, padx=5, pady=2, sticky="w"
            )
            # 文件大小
            ctk.CTkLabel(
                self.file_list_container, 
                text=file_size_formatted
            ).grid(
                row=row_num, column=2, padx=5, pady=2, sticky="e"
            )

            # 操作按钮 - 打开文件所在目录
            open_button = ctk.CTkButton(
                self.file_list_container,
                # text="📁", # 文件夹图标
                text="目录",
                width=30, height=20,
                text_color_disabled="gray",
                command=lambda p=path: self.open_file_location(p)
            )
            open_button.grid(row=row_num, column=3, padx=(5,2), pady=2, sticky="nsew")

            # 操作按钮 - 移除列表
            remove_button = ctk.CTkButton(
                self.file_list_container,
                # text="🗑️", # 垃圾桶图标
                text="移除",
                width=30, height=20,
                text_color_disabled="gray",
                command=lambda idx=i: self.remove_file_from_list(idx)
            )
            remove_button.grid(row=row_num, column=4, padx=(2,5), pady=2, sticky="nsew")

    def open_file_location(self, file_path):
        """打开文件所在目录。"""
        folder_path = os.path.dirname(file_path)
        if os.path.exists(folder_path):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
                elif os.uname().sysname == 'Darwin':  # macOS
                    os.system(f'open "{folder_path}"')
                else:  # Linux
                    os.system(f'xdg-open "{folder_path}"')
            except Exception as e:
                messagebox.showerror("错误", f"无法打开目录：{e}")
        else:
            messagebox.showwarning("警告", "文件所在目录不存在。")
    

    def remove_file_from_list(self, index):
        """从列表中移除指定索引的文件。"""
        if messagebox.askyesno("确认移除", f"确定要从列表中移除文件：\n{os.path.basename(self.selected_pdf_files[index])}?"):
            self.selected_pdf_files.pop(index)
            self.update_file_list_display()
            self.progress_label.configure(text=f"状态: 已移除文件。当前 {len(self.selected_pdf_files)} 个文件。")
    
    # def remove_selected_file(self, event):
    #     """双击文件列表的某行，移除对应的文件"""
    #     if not self.selected_pdf_files:
    #         return
        
    #     # 获取鼠标点击的行号
    #     # CTkTextbox 提供了 get_current_line() 方法或者使用标准 Tkinter index 方法
    #     try:
    #         index_str = self.file_list_textbox.index(ctk.CURRENT) # 获取点击位置的索引 (如 '2.5' 表示第2行第5个字符)
    #         line_num = int(float(index_str)) - 1 # 转换为行号（从0开始）
    #         if 0 <= line_num < len(self.selected_pdf_files):
    #             file_to_remove = self.selected_pdf_files[line_num]
    #             response = messagebox.askyesno(
    #                 "确认移除",
    #                 f"是否确认移除文件：\n{os.path.basename(file_to_remove)}？"
    #             )
    #             if response:
    #                 self.selected_pdf_files.pop(line_num) # 移除文件
    #                 self.update_file_list_display()
    #                 self.progress_label.configure(text=f"状态：已移除文件，当前 {len(self.select_pdf_files)} 个文件。")
    #     except Exception as e:
    #         print(f"移除文件时发生错误: {e}")
    
    def start_processing(self):
        """开始裁剪PDF文件的操作"""
        if not self.selected_pdf_files:
            messagebox.showwarning("警告", "请先选择要处理的PDF文件！")
            return
        
        suffix = self.suffix_entry.get().strip()
        margin_str = self.margin_entry.get().strip()
        if not suffix:
            suffix = "_cropped" # 默认后缀
        
        try:
            margin = int(margin_str)
            if margin < 0:
                raise ValueError("内边距必须是非负整数。")
        except ValueError:
            messagebox.showerror("错误", "内边距必须是一个非负整数。")
            return
        
        # 获取复选框的值
        export_per_page = self.export_per_page_checkbox.get()

        # 禁用按钮，避免重复点击
        self.select_files_button.configure(state="disabled")
        self.clear_list_button.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.export_per_page_checkbox.configure(state="disabled")
        self.progress_label.configure(text="状态：正在处理中...")

        # 使用线程处理PDF裁剪，避免GUI卡死
        self.processing_thread = threading.Thread(
            target=self._process_files_in_thread,
            args=(self.selected_pdf_files, suffix, margin, export_per_page)
        )
        self.processing_thread.start()

    
    def _process_files_in_thread(self, files_to_process, suffix, margin, export_per_page):
        """在单独的线程中处理文件"""
        processed_cnt = 0
        total_files = len(files_to_process)
        errors = []

        for i, input_path in enumerate(files_to_process):
            try:
                # 调用裁剪函数
                saved_files_cnt = crop_pdf_margins(input_path, suffix, margin, export_per_page)
                processed_cnt += saved_files_cnt # 如果是按页导出，计数会增加
                # 更新GUI状态（需要在主线程执行）
                self.after(0, self.update_progress_label, 
                           f"状态: 正在处理 {os.path.basename(input_path)} ({i+1}/{total_files})...")
            except Exception as e:
                errors.append(f"文件 {os.path.basename(input_path)} 处理失败: {e}")
                self.after(0, self.update_progress_label, 
                           f"状态: 处理 {os.path.basename(input_path)} 失败 ({i+1}/{total_files})...")

        # 处理完成，更新状态，启用按钮（在主线程执行）
        self.after(0, self._processing_finished, processed_cnt, total_files, errors)

    
    def update_progress_label(self, message):
        """更新进度标签，在主线程中执行"""
        self.progress_label.configure(text=message)

    def _processing_finished(self, processed_cnt, total_files, errors):
        """处理完成后执行回调函数，在主线程中执行"""
        self.select_files_button.configure(state="normal")
        self.clear_list_button.configure(state="normal")
        self.start_button.configure(state="normal")
        self.export_per_page_checkbox.configure(state="normal")

        if not errors:
            messagebox.showinfo(
                "处理完成",
                f"所有 {total_files} 个文件已成功处理！"
            )
            self.progress_label.configure(text=f"状态: 所有 {total_files} 个文件已成功处理！")
        else:
            error_msg = "\n".join(errors)
            messagebox.showerror(
                "处理完成(有错误)",
                f"共处理 {total_files} 个文件，成功 {processed_cnt} 个，失败 {len(errors)} 个。\n\n",
                f"错误信息：\n{error_msg}"
            )
            self.progress_label.configure(text=f"状态: 处理完成，有 {len(errors)} 个文件处理失败。")
        
        # 处理完成后，清空文件列表（可选，根据需求决定）
        # self.selected_pdf_paths = []
        # self.update_file_list_display()


if __name__ == "__main__":
    ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    app = PDFCropperApp()
    app.mainloop()