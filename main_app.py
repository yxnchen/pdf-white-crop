import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading # 用于异步处理，避免GUI卡死

from pdf_cropper import crop_pdf_margins


class PDFCropperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

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

        self.select_files_button = ctk.CTkButton(
            self.file_select_frame,
            text="选择PDF文件",
            command=self.select_pdf_files
        )
        self.select_files_button.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # 4. 创建文件列表区域
        self.file_list_frame = ctk.CTkFrame(self.main_frame)
        self.file_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.file_list_frame.grid_rowconfigure(0, weight=1)
        self.file_list_frame.grid_columnconfigure(0, weight=1)

        # 使用 CTkTextbox 来显示文件列表，并提供滚动条
        self.file_list_textbox = ctk.CTkTextbox(
            self.file_list_frame,
            wrap="none", # 不自动换行
            state="disabled" # 默认禁用，不允许用户直接编辑
        )
        self.file_list_textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # 5. 创建底部操作区域（后缀输入、内边距输入、开始按钮）
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.controls_frame.grid_columnconfigure(0, weight=0) # Label - 后缀
        self.controls_frame.grid_columnconfigure(1, weight=1) # Entry - 后缀
        self.controls_frame.grid_columnconfigure(2, weight=0) # Label - 内边距
        self.controls_frame.grid_columnconfigure(3, weight=1) # Entry - 内边距
        self.controls_frame.grid_columnconfigure(4, weight=0) # Button - 开始裁剪

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

        self.start_button = ctk.CTkButton(
            self.controls_frame,
            text="开始裁剪",
            command=self.start_processing
        )
        self.start_button.grid(row=0, column=4, padx=5, pady=5, sticky="e")

        # 6. 创建进度条区域
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="状态: 等待选择文件...")
        self.progress_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 7. 绑定文件列表的双击事件，允许移除文件
        self.file_list_textbox.bind("<Double-Button-1>", self.remove_selected_file)

    
    def select_pdf_files(self):
        """打开文件对话框，选择一个或多个PDF文件。"""
        file_paths = filedialog.askopenfilenames(
            title="选择PDF文件",
            filetypes=[("PDF files", "*.pdf")]
        )
        if file_paths:
            # 清空当前文件列表
            self.selected_pdf_files = list(file_paths)
            self.update_file_list_display()
            self.progress_label.configure(text=f"状态：已选择 {len(self.selected_pdf_files)} 个文件。")

    def update_file_list_display(self):
        """更新文件列表显示区域的内容"""
        self.file_list_textbox.configure(state="normal") # 允许编辑
        self.file_list_textbox.delete("1.0", "end") # 清空所有内容
        if self.selected_pdf_files:
            for i, path in enumerate(self.selected_pdf_files):
                self.file_list_textbox.insert("end", f"{i+1}. {path}\n")
        else:
            self.file_list_textbox.insert("end", "没有选择任何文件。")
        self.file_list_textbox.configure(state="disabled") # 禁用编辑

    
    def remove_selected_file(self, event):
        """双击文件列表的某行，移除对应的文件"""
        if not self.selected_pdf_files:
            return
        
        # 获取鼠标点击的行号
        # CTkTextbox 提供了 get_current_line() 方法或者使用标准 Tkinter index 方法
        try:
            index_str = self.file_list_textbox.index(ctk.CURRENT) # 获取点击位置的索引 (如 '2.5' 表示第2行第5个字符)
            line_num = int(float(index_str)) - 1 # 转换为行号（从0开始）
            if 0 <= line_num < len(self.selected_pdf_files):
                file_to_remove = self.selected_pdf_files[line_num]
                response = messagebox.askyesno(
                    "确认移除",
                    f"是否确认移除文件：\n{os.path.basename(file_to_remove)}？"
                )
                if response:
                    self.selected_pdf_files.pop(line_num) # 移除文件
                    self.update_file_list_display()
                    self.progress_label.configure(text=f"状态：已移除文件，当前 {len(self.select_pdf_files)} 个文件。")
        except Exception as e:
            print(f"移除文件时发生错误: {e}")
    
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

        # 禁用按钮，避免重复点击
        self.select_files_button.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.progress_label.configure(text="状态：正在处理中...")

        # 使用线程处理PDF裁剪，避免GUI卡死
        self.processing_thread = threading.Thread(
            target=self._process_files_in_thread,
            args=(self.selected_pdf_files, suffix, margin)
        )
        self.processing_thread.start()

    
    def _process_files_in_thread(self, files_to_process, suffix, margin):
        """在单独的线程中处理文件"""
        processed_cnt = 0
        total_files = len(files_to_process)
        errors = []

        for i, input_path in enumerate(files_to_process):
            base_name, ext = os.path.splitext(input_path)
            output_path = f"{base_name}{suffix}{ext}"

            try:
                # 调用裁剪函数
                crop_pdf_margins(input_path, output_path, margin)
                processed_cnt += 1
                # 更新GUI状态（需要在主线程执行）
                self.after(0, self.update_progress_label, f"状态: 正在处理 {os.path.basename(input_path)} ({i+1}/{total_files})...")
            except Exception as e:
                errors.append(f"文件 {os.path.basename(input_path)} 处理失败: {e}")
                self.after(0, self.update_progress_label, f"状态: 处理 {os.path.basename(input_path)} 失败 ({i+1}/{total_files})...")

        # 处理完成，更新状态，启用按钮（在主线程执行）
        self.after(0, self._processing_finished, processed_cnt, total_files, errors)

    
    def update_progress_label(self, message):
        """更新进度标签，在主线程中执行"""
        self.progress_label.configure(text=message)

    def _processing_finished(self, processed_cnt, total_files, errors):
        """处理完成后执行回调函数，在主线程中执行"""
        self.select_files_button.configure(state="normal")
        self.start_button.configure(state="normal")

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