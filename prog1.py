import os
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import defaultdict
from datetime import datetime
import threading
from PIL import Image, ImageTk  # Новая библиотека для работы с изображениями
import io

class DuplicateFileFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("Поиск дубликатов файлов с предпросмотром")
        self.root.geometry("1100x600")  # Увеличили ширину для предпросмотра
        
        # Переменные
        self.file_hashes = defaultdict(list)
        self.duplicates = []
        self.scanning = False
        self.selected_for_deletion = set()
        self.current_preview_image = None  # Для хранения текущего изображения
        
        self.setup_ui()
        
    def setup_ui(self):
        # Стили
        style = ttk.Style()
        style.theme_use('clam')
        
        # Основной фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка расширения сетки
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Панель выбора папки
        ttk.Label(main_frame, text="Папка для сканирования:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(main_frame, textvariable=self.path_var, width=50)
        self.path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.browse_btn = ttk.Button(main_frame, text="Обзор...", command=self.browse_folder)
        self.browse_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Опции сканирования
        options_frame = ttk.LabelFrame(main_frame, text="Опции сканирования", padding="10")
        options_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.recursive_var = tk.BooleanVar(value=True)
        self.recursive_cb = ttk.Checkbutton(options_frame, text="Рекурсивный поиск", 
                                           variable=self.recursive_var)
        self.recursive_cb.grid(row=0, column=0, padx=5)
        
        self.size_only_var = tk.BooleanVar(value=False)
        self.size_only_cb = ttk.Checkbutton(options_frame, text="Сравнивать только по размеру", 
                                           variable=self.size_only_var)
        self.size_only_cb.grid(row=0, column=1, padx=5)
        
        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.scan_btn = ttk.Button(button_frame, text="Начать сканирование", 
                                  command=self.start_scan)
        self.scan_btn.grid(row=0, column=0, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Остановить", 
                                  command=self.stop_scan, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        self.delete_btn = ttk.Button(button_frame, text="Удалить выбранные", 
                                    command=self.delete_selected, state=tk.DISABLED)
        self.delete_btn.grid(row=0, column=2, padx=5)
        
        self.clear_btn = ttk.Button(button_frame, text="Очистить список", 
                                   command=self.clear_list)
        self.clear_btn.grid(row=0, column=3, padx=5)
        
        # Статус бар
        self.status_var = tk.StringVar(value="Готов к работе")
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Прогресс бар
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                           maximum=100)
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Фрейм для списка и предпросмотра
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        content_frame.columnconfigure(0, weight=2)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Левая часть: Список дубликатов
        list_frame = ttk.LabelFrame(content_frame, text="Найденные дубликаты", padding="5")
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Дерево для отображения файлов
        columns = ('select', 'file', 'size', 'type', 'path')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')
        
        # Настройка столбцов
        self.tree.heading('select', text='Удалить')
        self.tree.heading('file', text='Имя файла')
        self.tree.heading('size', text='Размер')
        self.tree.heading('type', text='Тип')
        self.tree.heading('path', text='Путь')
        
        self.tree.column('select', width=50, anchor='center')
        self.tree.column('file', width=150)
        self.tree.column('size', width=80, anchor='e')
        self.tree.column('type', width=80)
        self.tree.column('path', width=250)
        
        # Scrollbar для дерева
        tree_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Правая часть: Предпросмотр
        preview_frame = ttk.LabelFrame(content_frame, text="Предпросмотр", padding="5")
        preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=0)
        preview_frame.rowconfigure(1, weight=1)
        
        # Информация о файле
        self.preview_info = tk.Text(preview_frame, height=4, width=30, 
                                   wrap=tk.WORD, state=tk.DISABLED)
        self.preview_info.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Область для изображения
        self.preview_label = ttk.Label(preview_frame, text="Выберите файл для предпросмотра",
                                      anchor=tk.CENTER, relief=tk.SUNKEN)
        self.preview_label.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Настройка весов для растягивания
        main_frame.rowconfigure(5, weight=1)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        
        # Привязка событий
        self.tree.bind('<Button-1>', self.on_tree_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)  # Новое событие для предпросмотра
        
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            
    def get_file_type(self, filename):
        """Определяет тип файла по расширению"""
        ext = os.path.splitext(filename)[1].lower()
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        doc_exts = ['.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx']
        
        if ext in image_exts:
            return 'Изображение'
        elif ext in doc_exts:
            return 'Документ'
        elif ext in ['.mp3', '.wav', '.flac']:
            return 'Аудио'
        elif ext in ['.mp4', '.avi', '.mkv']:
            return 'Видео'
        else:
            return 'Другой'
            
    def calculate_hash(self, filepath):
        """Вычисляет хеш файла"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"Ошибка чтения файла {filepath}: {e}")
            return None
    
    def show_preview(self, filepath):
        """Показывает предпросмотр файла"""
        # Очищаем предыдущее изображение
        if self.current_preview_image:
            self.current_preview_image = None
        
        # Обновляем информацию о файле
        self.preview_info.config(state=tk.NORMAL)
        self.preview_info.delete(1.0, tk.END)
        
        try:
            # Основная информация
            filename = os.path.basename(filepath)
            size = os.path.getsize(filepath)
            modified = datetime.fromtimestamp(os.path.getmtime(filepath))
            file_type = self.get_file_type(filename)
            
            info_text = f"Имя: {filename}\n"
            info_text += f"Тип: {file_type}\n"
            info_text += f"Размер: {self.format_size(size)}\n"
            info_text += f"Изменён: {modified.strftime('%d.%m.%Y %H:%M')}"
            
            self.preview_info.insert(1.0, info_text)
            self.preview_info.config(state=tk.DISABLED)
            
            # Показываем изображение если это картинка
            ext = os.path.splitext(filename)[1].lower()
            image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
            
            if ext in image_exts:
                try:
                    # Открываем и изменяем размер изображения
                    img = Image.open(filepath)
                    
                    # Получаем размеры области предпросмотра
                    preview_width = self.preview_label.winfo_width() or 200
                    preview_height = self.preview_label.winfo_height() or 200
                    
                    # Масштабируем с сохранением пропорций
                    img.thumbnail((preview_width, preview_height), Image.Resampling.LANCZOS)
                    
                    # Конвертируем для tkinter
                    self.current_preview_image = ImageTk.PhotoImage(img)
                    self.preview_label.config(image=self.current_preview_image, text="")
                    
                except Exception as e:
                    self.preview_label.config(image='', text=f"Не удалось загрузить изображение\n{str(e)}")
            else:
                self.preview_label.config(image='', text=f"Предпросмотр для {ext}\nне поддерживается")
                
        except Exception as e:
            self.preview_info.config(state=tk.NORMAL)
            self.preview_info.delete(1.0, tk.END)
            self.preview_info.insert(1.0, f"Ошибка: {str(e)}")
            self.preview_info.config(state=tk.DISABLED)
            self.preview_label.config(image='', text="Ошибка загрузки файла")
    
    def format_size(self, size):
        """Форматирует размер файла"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024*1024:
            return f"{size/1024:.1f} KB"
        elif size < 1024*1024*1024:
            return f"{size/(1024*1024):.1f} MB"
        else:
            return f"{size/(1024*1024*1024):.1f} GB"
    
    def on_tree_select(self, event):
        """Обработка выбора строки в дереве для предпросмотра"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            values = self.tree.item(item, 'values')
            if len(values) > 3:  # Проверяем что есть путь
                filepath = values[4]  # Путь в 5-й колонке
                if os.path.exists(filepath):
                    self.show_preview(filepath)
    
    def scan_directory(self):
        """Сканирует директорию на наличие дубликатов"""
        if self.scanning:
            return
            
        path = self.path_var.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Ошибка", "Укажите существующую папку")
            return
            
        self.scanning = True
        self.scan_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.delete_btn.config(state=tk.DISABLED)
        self.clear_list()
        self.preview_label.config(image='', text="Выберите файл для предпросмотра")
        
        self.status_var.set("Сканирование...")
        self.progress_var.set(0)
        
        # Сбор информации о файлах
        all_files = []
        if self.recursive_var.get():
            for root, dirs, files in os.walk(path):
                for file in files:
                    filepath = os.path.join(root, file)
                    all_files.append(filepath)
        else:
            for item in os.listdir(path):
                filepath = os.path.join(path, item)
                if os.path.isfile(filepath):
                    all_files.append(filepath)
        
        total_files = len(all_files)
        if total_files == 0:
            self.status_var.set("Файлы не найдены")
            self.scanning = False
            self.scan_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            return
        
        # Первый проход - группировка по размеру
        size_groups = defaultdict(list)
        for i, filepath in enumerate(all_files):
            if not self.scanning:
                break
                
            try:
                size = os.path.getsize(filepath)
                size_groups[size].append(filepath)
            except:
                continue
            
            # Обновление прогресса
            if i % 10 == 0:
                progress = (i / total_files) * 50
                self.progress_var.set(progress)
                self.status_var.set(f"Сканирование: {i}/{total_files} файлов")
                self.root.update()
        
        # Второй проход - вычисление хеша для файлов одинакового размера
        duplicates_found = 0
        for size, file_list in size_groups.items():
            if len(file_list) > 1:
                if self.size_only_var.get():
                    # Если сравнение только по размеру
                    self.duplicates.append(file_list)
                    duplicates_found += len(file_list) - 1
                else:
                    # Сравнение по хешу
                    hash_groups = defaultdict(list)
                    for filepath in file_list:
                        if not self.scanning:
                            break
                        file_hash = self.calculate_hash(filepath)
                        if file_hash:
                            hash_groups[file_hash].append(filepath)
                    
                    for files in hash_groups.values():
                        if len(files) > 1:
                            self.duplicates.append(files)
                            duplicates_found += len(files) - 1
            
            if not self.scanning:
                break
        
        # Отображение результатов
        self.display_duplicates()
        
        # Обновление интерфейса
        self.scanning = False
        self.scan_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        if duplicates_found > 0:
            self.delete_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Найдено {duplicates_found} дубликатов в {len(self.duplicates)} группах")
        else:
            self.status_var.set("Дубликаты не найдены")
        
        self.progress_var.set(100)
        
    def start_scan(self):
        """Запуск сканирования в отдельном потоке"""
        thread = threading.Thread(target=self.scan_directory)
        thread.daemon = True
        thread.start()
        
    def stop_scan(self):
        """Остановка сканирования"""
        self.scanning = False
        self.status_var.set("Сканирование остановлено")
        
    def display_duplicates(self):
        """Отображение найденных дубликатов в дереве"""
        self.tree.delete(*self.tree.get_children())
        self.selected_for_deletion.clear()
        
        for group_num, file_group in enumerate(self.duplicates):
            # Сортируем файлы по дате изменения (старые первыми)
            file_group.sort(key=lambda x: os.path.getmtime(x))
            
            for i, filepath in enumerate(file_group):
                try:
                    filename = os.path.basename(filepath)
                    size = os.path.getsize(filepath)
                    file_type = self.get_file_type(filename)
                    
                    # Форматирование размера
                    size_str = self.format_size(size)
                    
                    # Определяем, какой файл оставить (первый в группе)
                    keep = "Оставить" if i == 0 else ""
                    
                    item_id = self.tree.insert('', 'end', values=(
                        '',  # Чекбокс
                        filename,
                        size_str,
                        file_type,
                        filepath
                    ))
                    
                    # Помечаем первый файл как оставляемый
                    if i == 0:
                        self.tree.item(item_id, tags=('keep',))
                        self.tree.tag_configure('keep', background='#e6f3e6')
                    
                except Exception as e:
                    print(f"Ошибка обработки файла {filepath}: {e}")
            
            # Добавляем разделитель между группами
            if group_num < len(self.duplicates) - 1:
                self.tree.insert('', 'end', values=('─'*50, '', '', '', ''), tags=('separator',))
                self.tree.tag_configure('separator', foreground='gray')
        
    def on_tree_click(self, event):
        """Обработка кликов по дереву (чекбоксы)"""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            
            if column == "#1":  # Колонка с чекбоксами
                values = self.tree.item(item, 'values')
                filepath = values[4]
                
                # Не позволяем отметить файл для удаления, если он помечен как "оставить"
                tags = self.tree.item(item, 'tags')
                if 'keep' not in tags:
                    if filepath in self.selected_for_deletion:
                        self.selected_for_deletion.remove(filepath)
                        self.tree.set(item, column='select', value='')
                    else:
                        self.selected_for_deletion.add(filepath)
                        self.tree.set(item, column='select', value='✓')
    
    def delete_selected(self):
        """Удаление выбранных файлов"""
        if not self.selected_for_deletion:
            messagebox.showwarning("Внимание", "Не выбраны файлы для удаления")
            return
            
        confirm = messagebox.askyesno(
            "Подтверждение",
            f"Вы уверены, что хотите удалить {len(self.selected_for_deletion)} файлов?\n"
            "Эта операция необратима!"
        )
        
        if confirm:
            deleted_count = 0
            failed_count = 0
            
            for filepath in list(self.selected_for_deletion):
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    
                    # Удаляем файл из списка дубликатов
                    for group in self.duplicates:
                        if filepath in group:
                            group.remove(filepath)
                    
                except Exception as e:
                    failed_count += 1
                    print(f"Ошибка удаления {filepath}: {e}")
            
            # Обновляем отображение
            self.display_duplicates()
            
            # Очищаем предпросмотр
            self.preview_label.config(image='', text="Выберите файл для предпросмотра")
            self.preview_info.config(state=tk.NORMAL)
            self.preview_info.delete(1.0, tk.END)
            self.preview_info.config(state=tk.DISABLED)
            
            # Показываем результат
            message = f"Удалено: {deleted_count} файлов"
            if failed_count > 0:
                message += f"\nНе удалось удалить: {failed_count} файлов"
            messagebox.showinfo("Результат", message)
            
            if deleted_count > 0:
                self.status_var.set(f"Удалено {deleted_count} файлов")
    
    def clear_list(self):
        """Очистка списка дубликатов"""
        self.tree.delete(*self.tree.get_children())
        self.duplicates.clear()
        self.selected_for_deletion.clear()
        self.delete_btn.config(state=tk.DISABLED)
        self.preview_label.config(image='', text="Выберите файл для предпросмотра")
        self.preview_info.config(state=tk.NORMAL)
        self.preview_info.delete(1.0, tk.END)
        self.preview_info.config(state=tk.DISABLED)
        self.status_var.set("Список очищен")

def main():
    root = tk.Tk()
    app = DuplicateFileFinder(root)
    root.mainloop()

if __name__ == "__main__":
    main()