

# Standard library imports
import sys
import os
import json
import hashlib
import time
from time import sleep
from webbrowser import open as open_browser
from warnings import filterwarnings
from threading import Event, Lock
from multiprocessing import (
    Process, 
    Queue as multiprocessing_Queue,
    freeze_support as multiprocessing_freeze_support
)
from typing import Callable, Dict
from shutil import rmtree as remove_directory
from itertools import repeat as itertools_repeat
from threading import Thread
from multiprocessing.pool import ThreadPool

from os import (
    sep as os_separator,
    makedirs as os_makedirs,
    listdir as os_listdir,
    stat as os_stat
)

from os.path import (
    dirname as os_path_dirname,
    abspath as os_path_abspath,
    join as os_path_join,
    exists as os_path_exists,
    getsize as os_path_getsize
)

# Third-party library imports
from re import compile as re_compile
from requests import get as requests_get
from fnmatch import filter as fnmatch_filter
from PIL.Image import open as pillow_image_open
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen

# GUI imports
from tkinter import StringVar, CENTER
from customtkinter import (
    CTk,
    CTkButton,
    CTkEntry,
    CTkFont,
    CTkImage,
    CTkLabel,
    CTkToplevel,
    set_appearance_mode,
    set_default_color_theme,
)

filterwarnings("ignore")

# 新增全局变量
stop_event = Event()
download_lock = Lock()
progress_file = "download_progress.json"
app_name = "Fapello.Downloader"
version = "3.7"

# 可调整参数（需修改代码）
MAX_RETRIES = 5    # 最大重试次数
TIMEOUT = 20       # 适当增加大文件超时
RETRY_DELAY = 3    # 降低网络环境差时的等待时间

text_color      = "#F0F0F0"
app_name_color  = "#ffbf00"
 
githubme        = "https://github.com/lrzjason/Fapello.Downloader"
# telegramme      = "https://linktr.ee/j3ngystudio"
qs_link         = "https://github.com/Djdefrag/QualityScaler"

COMPLETED_STATUS   = "Completed"
DOWNLOADING_STATUS = "Downloading"
ERROR_STATUS       = "Error"
STOP_STATUS        = "Stop"

HEADERS_FOR_REQUESTS = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36" }

# Utils 

def opengithub() -> None: open_browser(githubme, new=1)

# def opentelegram() -> None: open_browser(telegramme, new=1)

def openqualityscaler() -> None: open_browser(qs_link, new=1)

def find_by_relative_path(relative_path: str) -> str:
    base_path = getattr(sys, '_MEIPASS', os_path_dirname(os_path_abspath(__file__)))
    return os_path_join(base_path, relative_path)

# ====================== 优化功能实现 ======================
def load_progress(model_name: str) -> Dict:
    try:
        if os_path_exists(progress_file):
            with open(progress_file, 'r') as f:
                data = json.load(f)
                return data.get(model_name, {})
    except:
        pass
    return {}

def save_progress(model_name: str, progress: Dict):
    try:
        data = {}
        if os_path_exists(progress_file):
            with open(progress_file, 'r') as f:
                data = json.load(f)
        data[model_name] = progress
        with open(progress_file, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass

def calculate_hash(file_path: str) -> str:
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

def validate_file(file_path: str, expected_size: int, expected_hash: str) -> bool:
    if not os_path_exists(file_path):
        return False
    if os_path_getsize(file_path) != expected_size:
        return False
    return calculate_hash(file_path) == expected_hash

# ====================== 修改核心函数 ======================
def create_temp_dir(name_dir: str) -> None:
    if not os_path_exists(name_dir):
        os_makedirs(name_dir, mode=0o777, exist_ok=True)

def stop_thread() -> None: 
    stop = 1 + "x"

def prepare_filename(file_url, index, file_type) -> str:
    first_part_filename = str(file_url).split("/")[-3]

    if   file_type == "image": extension = ".jpg"
    elif file_type == "video": extension = ".mp4"

    filename = first_part_filename + "_" + str(index) + extension

    return filename

def show_error_message(exception: str) -> None:
  
    messageBox_title    = "Download error"
    messageBox_subtitle = "Please report the error on Github or Telegram"
    messageBox_text     = f" {str(exception)} "

    CTkMessageBox(
        messageType   = "error", 
        title         = messageBox_title, 
        subtitle      = messageBox_subtitle,
        default_value = None,
        option_list   = [messageBox_text]
    )

# 修改状态读取函数
def read_process_status() -> str:
    try:
        actual_step = processing_queue.get_nowait()
        if DOWNLOADING_STATUS in actual_step:
            _, count = actual_step.split("|")
            return f"{DOWNLOADING_STATUS}|{count}"
        return actual_step
    except:
        return DOWNLOADING_STATUS  # 队列为空时返回默认状态
def write_process_status(
        processing_queue: multiprocessing_Queue,
        step: str
        ) -> None:
    try:
        # 非阻塞方式清除旧消息
        while not processing_queue.empty():
            processing_queue.get_nowait()
        processing_queue.put_nowait(f"{step}")
    except:
        pass

def count_files_in_directory(target_dir: str) -> int:
    return len(fnmatch_filter(os_listdir(target_dir), '*.*'))

# 修改状态检查线程
def thread_check_steps_download(
        link: str, 
        how_many_files: int
        ) -> None:
    
    def safe_update(message: str):
        if not stop_event.is_set():
            info_message.set(message)
            window.update_idletasks()
    
    try:
        while not stop_event.is_set():
            actual_step = read_process_status()
            
            if DOWNLOADING_STATUS in actual_step:
                _, current, total = actual_step.split("|")
                failed = count_failed_files(link.split("/")[3])
                safe_update(f"Downloading {current}/{total} | Failed: {failed}")
                
            elif actual_step == COMPLETED_STATUS:
                safe_update("Download completed! :)")
                break
                
            elif actual_step == STOP_STATUS:
                safe_update("Download stopped")
                break
                
            elif ERROR_STATUS in actual_step:
                error = actual_step.replace(ERROR_STATUS, "")
                safe_update("Error while downloading :(")
                window.after(0, lambda: show_error_message(error))
                break
                
            sleep(0.3)  # 更快的刷新频率
            
    except Exception as e:
        print(f"Monitor error: {str(e)}")
    finally:
        window.after(0, place_download_button)


# Core

def get_url(url: str):
    if url.startswith("http"):
        return [url]
    elif "," in url:
        models = url.split(",")
        urls = [f"https://fapello.com/{url}/" for url in models]
        return urls
    else:
       return f"https://fapello.com/{url}/"

def check_button_command() -> None:

    links = get_url(selected_url.get())
    # check links is list or not
    if not isinstance(links, list): links = [links]
    total = 0
    for link in links:
        selected_link = str(link).strip()

        if selected_link == "Paste link here https://fapello.com/emily-rat---/": info_message.set("Insert a valid Fapello.com link")

        elif selected_link == "": info_message.set("Insert a valid Fapello.com link")

        elif "https://fapello.com" in selected_link:

            if not selected_link.endswith("/"): selected_link = selected_link + '/'

            total += get_Fapello_files_number(selected_link)

        else: info_message.set("Insert a valid Fapello.com link")

    if total == 0:
        info_message.set("No files found for this link")
    else: 
        info_message.set(f"Found {total} files for this link")

def download_button_command() -> None:
    global process_download
    global cpu_number
    global processing_queue

    info_message.set("Starting download")
    write_process_status(processing_queue, "Starting download")

    try: cpu_number = int(float(str(selected_cpu_number.get())))
    except:
        info_message.set("Cpu number must be a numeric value")
        return

    links = get_url(selected_url.get())
    # check links is list or not
    if not isinstance(links, list): links = [links]
    for link in links:
        selected_link = str(link).strip()

        if selected_link == "Paste link here https://fapello.com/emily-rat---/":
            info_message.set("Insert a valid Fapello.com link")

        elif selected_link == "":
            info_message.set("Insert a valid Fapello.com link")

        elif "https://fapello.com" in selected_link:

            download_type = 'fapello.com'

            if not selected_link.endswith("/"): selected_link = selected_link + '/'

            how_many_images = get_Fapello_files_number(selected_link)

            if how_many_images == 0:
                info_message.set("No files found for this link")
            else: 
                process_download = Process(
                    target = download_orchestrator,
                    args = (
                        processing_queue,
                        selected_link, 
                        cpu_number
                        )
                    )
                process_download.start()

                thread_wait = Thread(
                    target = thread_check_steps_download,
                    args = (
                        selected_link, 
                        how_many_images
                        )
                    )
                thread_wait.start()

                place_stop_button()

        else:
            info_message.set("Insert a valid Fapello.com link")

# ====================== 改进停止机制 ======================
def stop_download_process() -> None:
    stop_event.set()

def stop_button_command() -> None:
    stop_download_process()
    write_process_status(processing_queue, f"{STOP_STATUS}")

def get_Fapello_file_url(link: str) -> tuple:
    
    page = requests_get(link, headers = HEADERS_FOR_REQUESTS)
    soup = BeautifulSoup(page.content, "html.parser")
    file_element = soup.find("div", class_="flex justify-between items-center")
    try: 
        if 'type="video/mp4' in str(file_element):
            file_url  = file_element.find("source").get("src")
            file_type = "video"
            print(f" > Video: {file_url}")
        else:
            file_url  = file_element.find("img").get("src")
            file_type = "image"
            print(f" > Image: {file_url}")

        return file_url, file_type
    except:
        return None, None

def get_Fapello_files_number(url: str) -> int:
    
    page = requests_get(url, headers = HEADERS_FOR_REQUESTS)
    soup = BeautifulSoup(page.content, "html.parser")

    all_href_links = soup.find_all('a', href = re_compile(url))

    for link in all_href_links:
        link_href          = link.get('href')
        link_href_stripped = link_href.rstrip('/')
        link_href_numeric  = link_href_stripped.split('/')[-1]
        if link_href_numeric.isnumeric():
            print(f"> Found {link_href_numeric} files")
            return int(link_href_numeric) + 1

    return 0
# 修改线程下载函数
def thread_download_file(
        link: str,
        target_dir: str,
        index: int,
        stop_flag: Event
) -> None:
    if stop_flag.is_set():
        return

    model_name = link.split('/')[3]
    file_url, file_type = get_Fapello_file_url(link + str(index))
    
    if not file_url or model_name not in file_url:
        return

    filename = prepare_filename(file_url, index, file_type)
    file_path = os_path_join(target_dir, filename)
    
    progress = load_progress(model_name)
    # 检查文件有效性时包含重试记录
    if filename in progress:
        if progress[filename].get('status') == 'completed':
            if validate_file(file_path, progress[filename]['size'], progress[filename]['hash']):
                return
        elif progress[filename].get('retries', 0) >= MAX_RETRIES:
            return

    retry_count = 0
    while retry_count < MAX_RETRIES and not stop_flag.is_set():
        try:
            request = Request(file_url, headers=HEADERS_FOR_REQUESTS)
            with urlopen(request, timeout=TIMEOUT) as response:
                content = response.read()
                # 检查停止信号
                if stop_flag.is_set():
                    return
                
                # 验证内容完整性
                if len(content) < 1024:  # 最小文件尺寸保护
                    raise ValueError("Incomplete content")
                
                file_size = len(content)
                file_hash = hashlib.sha1(content).hexdigest()
                
                with open(file_path, 'wb') as output_file:
                    output_file.write(content)
                
                # 更新成功状态
                with download_lock:
                    progress[filename] = {
                        'status': 'completed',
                        'size': file_size,
                        'hash': file_hash,
                        'timestamp': time.time()
                    }
                    save_progress(model_name, progress)
                break
                    
        except Exception as e:
            print(f"Download error ({retry_count+1}/{MAX_RETRIES}): {e}")
            # 更新重试记录
            with download_lock:
                progress.setdefault(filename, {}).update({
                    'status': 'retrying',
                    'retries': retry_count + 1,
                    'last_error': str(e),
                    'timestamp': time.time()
                })
                save_progress(model_name, progress)
            
            retry_count += 1
            if retry_count < MAX_RETRIES:
                sleep(RETRY_DELAY * retry_count)  # 指数退避
            else:
                print(f"Skip file after {MAX_RETRIES} retries: {filename}")
                # 标记最终失败状态
                with download_lock:
                    progress[filename] = {
                        'status': 'failed',
                        'retries': MAX_RETRIES,
                        'errors': [str(e) for _ in range(retry_count)],
                        'timestamp': time.time()
                    }
                    save_progress(model_name, progress)
                return
                # 修改下载协调器增加实时进度更新
def download_orchestrator(
        processing_queue: multiprocessing_Queue,
        selected_link: str,
        cpu_number: int
):
    stop_event.clear()
    model_dir = selected_link.split("/")[3]
    target_dir = f"output/{model_dir}"
    create_temp_dir(target_dir)
    
    try:
        how_many_files = get_Fapello_files_number(selected_link)
        total_files = how_many_files
        completed_files = 0
        
        # 实时进度更新线程
        def progress_monitor():
            nonlocal completed_files
            while not stop_event.is_set():
                current_count = count_files_in_directory(target_dir)
                if current_count > completed_files:
                    completed_files = current_count
                    write_process_status(
                        processing_queue, 
                        f"{DOWNLOADING_STATUS}|{completed_files}|{total_files}"
                    )
                sleep(0.5)  # 每500ms更新一次
        
        monitor_thread = Thread(target=progress_monitor)
        monitor_thread.start()
        
        with ThreadPool(cpu_number) as pool:
            pool.starmap(
                thread_download_file,
                zip(
                    itertools_repeat(selected_link),
                    itertools_repeat(target_dir),
                    range(how_many_files),
                    itertools_repeat(stop_event)
                )
            )
        
        stop_event.set()
        monitor_thread.join()
        
        if not stop_event.is_set():
            write_process_status(processing_queue, COMPLETED_STATUS)
            
    except Exception as error:
        write_process_status(processing_queue, f"{ERROR_STATUS}{str(error)}")


#  UI function 

def place_github_button():
    git_button = CTkButton(master      = window, 
                            command    = opengithub,
                            image      = logo_git,
                            width         = 30,
                            height        = 30,
                            border_width  = 1,
                            fg_color      = "transparent",
                            text_color    = "#C0C0C0",
                            border_color  = "#404040",
                            anchor        = "center",                           
                            text          = "", 
                            font          = bold11)
    
    git_button.place(relx = 0.055, rely = 0.875, anchor = CENTER)

# def place_telegram_button():
#     telegram_button = CTkButton(master     = window, 
#                                 image      = logo_telegram,
#                                 command    = opentelegram,
#                                 width         = 30,
#                                 height        = 30,
#                                 border_width  = 1,
#                                 fg_color      = "transparent",
#                                 text_color    = "#C0C0C0",
#                                 border_color  = "#404040",
#                                 anchor        = "center",                           
#                                 text          = "", 
#                                 font          = bold11)
#     telegram_button.place(relx = 0.055, rely = 0.95, anchor = CENTER)
 
def place_qualityscaler_button():
    qualityscaler_button = CTkButton(
        master = window, 
        image  = logo_qs,
        command = openqualityscaler,
        width         = 30,
        height        = 30,
        border_width  = 1,
        fg_color      = "transparent",
        text_color    = "#C0C0C0",
        border_color  = "#404040",
        anchor        = "center",                           
        text          = "", 
        font          = bold11)
    qualityscaler_button.place(relx = 0.055, rely = 0.8, anchor = CENTER)

def open_info_simultaneous_downloads():

    CTkMessageBox(
        messageType = 'info',
        title = "Simultaneous downloads",
        subtitle = "This widget allows to choose how many files are downloaded simultaneously",
        default_value = "6",
        option_list = []
    )

def open_info_tips():
    CTkMessageBox(
        messageType   = 'info',
        title         = "Connection tips",
        subtitle      = "In case of problems with reaching the website, follow these tips",
        default_value = None,
        option_list   = [
            " Many internet providers block access to websites such as fapello.com",
            " In this case you can use custom DNS or use a VPN",

            "\n To facilitate there is a free program called DNSJumper\n" +
            "    • it can find the best custom DNS for your internet line and set them directly\n" + 
            "    • it can quickly revert to the default DNS in case of problems \n" + 
            "    • has also a useful function called DNS Flush that solves problems connecting to the Fapello.com \n",

            " On some occasions, the download may freeze, just stop and restart the download"
        ]
    )

def place_app_name():
    app_name_label = CTkLabel(master     = window, 
                              text       = app_name + " " + version,
                              text_color = app_name_color,
                              font       = bold20,
                              anchor     = "w")
    
    app_name_label.place(relx = 0.5, 
                         rely = 0.1, 
                         anchor = CENTER)

def place_link_textbox():
    link_textbox = create_text_box(selected_url, 150, 32)
    link_textbox.place(relx = 0.435, rely = 0.3, relwidth = 0.7, anchor = CENTER)

def place_check_button():
    check_button = CTkButton(
        master     = window, 
        command    = check_button_command,
        text       = "CHECK",
        width      = 60,
        height     = 30,
        font       = bold11,
        border_width = 1,
        fg_color     = "#282828",
        text_color   = "#E0E0E0",
        border_color = "#0096FF"
    )
    check_button.place(relx = 0.865, rely = 0.3, anchor = CENTER)

def place_simultaneous_downloads_textbox():
    cpu_button  = create_info_button(open_info_simultaneous_downloads, "Simultaneous downloads")
    cpu_textbox = create_text_box(selected_cpu_number, 110, 32)

    cpu_button.place(relx = 0.42, rely = 0.42, anchor = CENTER)
    cpu_textbox.place(relx = 0.75, rely = 0.42, anchor = CENTER)

def place_tips():
    tips_button = create_info_button(open_info_tips, "Connection tips", width = 110)
    tips_button.place(relx = 0.8, rely = 0.9, anchor = CENTER)

def place_message_label():
    message_label = CTkLabel(
        master  = window, 
        textvariable = info_message,
        height       = 25,
        font         = bold11,
        fg_color     = "#ffbf00",
        text_color   = "#000000",
        anchor       = "center",
        corner_radius = 25
    )
    message_label.place(relx = 0.5, rely = 0.78, anchor = CENTER)

def place_download_button(): 
    download_button = CTkButton(
        master     = window, 
        command    = download_button_command,
        text       = "DOWNLOAD",
        image      = download_icon,
        width      = 140,
        height     = 30,
        font       = bold11,
        border_width = 1,
        fg_color     = "#282828",
        text_color   = "#E0E0E0",
        border_color = "#0096FF"
    )
    download_button.place(relx = 0.5, rely = 0.9, anchor = CENTER)
    
def place_stop_button(): 
    stop_button = CTkButton(
        master     = window, 
        command    = stop_button_command,
        text       = "STOP",
        image      = stop_icon,
        width      = 140,
        height     = 30,
        font       = bold11,
        border_width = 1,
        fg_color     = "#282828",
        text_color   = "#E0E0E0",
        border_color = "#0096FF"
    )
    stop_button.place(relx = 0.5, rely = 0.9, anchor = CENTER)



# Main/GUI functions ---------------------------

def on_app_close() -> None:
    window.grab_release()
    window.destroy()
    stop_download_process()

class CTkMessageBox(CTkToplevel):

    def __init__(
            self,
            messageType: str,
            title: str,
            subtitle: str,
            default_value: str,
            option_list: list,
            ) -> None:

        super().__init__()

        self._running: bool = False

        self._messageType = messageType
        self._title = title        
        self._subtitle = subtitle
        self._default_value = default_value
        self._option_list = option_list
        self._ctkwidgets_index = 0

        self.title('')
        self.lift()                          # lift window on top
        self.attributes("-topmost", True)    # stay on top
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.after(10, self._create_widgets)  # create widgets with slight delay, to avoid white flickering of background
        self.resizable(False, False)
        self.grab_set()                       # make other windows not clickable

    def _ok_event(
            self, 
            event = None
            ) -> None:
        self.grab_release()
        self.destroy()

    def _on_closing(
            self
            ) -> None:
        self.grab_release()
        self.destroy()

    def createEmptyLabel(
            self
            ) -> CTkLabel:
        
        return CTkLabel(master = self, 
                        fg_color = "transparent",
                        width    = 500,
                        height   = 17,
                        text     = '')

    def placeInfoMessageTitleSubtitle(
            self,
            ) -> None:

        spacingLabel1 = self.createEmptyLabel()
        spacingLabel2 = self.createEmptyLabel()

        if self._messageType == "info":
            title_subtitle_text_color = "#3399FF"
        elif self._messageType == "error":
            title_subtitle_text_color = "#FF3131"

        titleLabel = CTkLabel(
            master     = self,
            width      = 500,
            anchor     = 'w',
            justify    = "left",
            fg_color   = "transparent",
            text_color = title_subtitle_text_color,
            font       = bold22,
            text       = self._title
            )
        
        if self._default_value != None:
            defaultLabel = CTkLabel(
                master     = self,
                width      = 500,
                anchor     = 'w',
                justify    = "left",
                fg_color   = "transparent",
                text_color = "#3399FF",
                font       = bold17,
                text       = f"Default: {self._default_value}"
                )
        
        subtitleLabel = CTkLabel(
            master     = self,
            width      = 500,
            anchor     = 'w',
            justify    = "left",
            fg_color   = "transparent",
            text_color = title_subtitle_text_color,
            font       = bold14,
            text       = self._subtitle
            )
        
        spacingLabel1.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 0, pady = 0, sticky = "ew")
        
        self._ctkwidgets_index += 1
        titleLabel.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 25, pady = 0, sticky = "ew")
        
        if self._default_value != None:
            self._ctkwidgets_index += 1
            defaultLabel.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 25, pady = 0, sticky = "ew")
        
        self._ctkwidgets_index += 1
        subtitleLabel.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 25, pady = 0, sticky = "ew")
        
        self._ctkwidgets_index += 1
        spacingLabel2.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 0, pady = 0, sticky = "ew")

    def placeInfoMessageOptionsText(
            self,
            ) -> None:
        
        for option_text in self._option_list:
            optionLabel = CTkLabel(master = self,
                                    width  = 600,
                                    height = 45,
                                    corner_radius = 6,
                                    anchor     = 'w',
                                    justify    = "left",
                                    text_color = "#C0C0C0",
                                    fg_color   = "#282828",
                                    bg_color   = "transparent",
                                    font       = bold12,
                                    text       = option_text)
            
            self._ctkwidgets_index += 1
            optionLabel.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 25, pady = 4, sticky = "ew")

        spacingLabel3 = self.createEmptyLabel()

        self._ctkwidgets_index += 1
        spacingLabel3.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 0, pady = 0, sticky = "ew")

    def placeInfoMessageOkButton(
            self
            ) -> None:
        
        ok_button = CTkButton(
            master  = self,
            command = self._ok_event,
            text    = 'OK',
            width   = 125,
            font         = bold11,
            border_width = 1,
            fg_color     = "#282828",
            text_color   = "#E0E0E0",
            border_color = "#0096FF"
            )
        
        self._ctkwidgets_index += 1
        ok_button.grid(row = self._ctkwidgets_index, column = 1, columnspan = 1, padx = (10, 20), pady = (10, 20), sticky = "e")

    def _create_widgets(
            self
            ) -> None:

        self.grid_columnconfigure((0, 1), weight=1)
        self.rowconfigure(0, weight=1)

        self.placeInfoMessageTitleSubtitle()
        self.placeInfoMessageOptionsText()
        self.placeInfoMessageOkButton()

def create_info_button(
        command: Callable, 
        text: str,
        width: int = 150
        ) -> CTkButton:
    
    return CTkButton(
        master  = window, 
        command = command,
        text          = text,
        fg_color      = "transparent",
        hover_color   = "#181818",
        text_color    = "#C0C0C0",
        anchor        = "w",
        height        = 22,
        width         = width,
        corner_radius = 10,
        font          = bold12,
        image         = info_icon
    )

def create_text_box(textvariable, width, heigth):
    return CTkEntry(
        master        = window, 
        textvariable  = textvariable,
        border_width  = 1,
        width         = width,
        height        = heigth,
        font          = bold11,
        justify       = "center",
        fg_color      = "#000000",
        border_color  = "#404040"
    )

def count_failed_files(target_dir: str) -> int:
    try:
        model_name = target_dir.split('/')[-1]
        progress = load_progress(model_name)
        return sum(1 for f in progress.values() if f.get('status') == 'failed')
    except:
        return 0

# 修复后的place_advanced_settings函数
def place_advanced_settings():
    settings_button = create_info_button(
        command=lambda: CTkMessageBox(
            messageType='info',
            title="Advanced Settings",
            subtitle=f"Current configuration:\nRetries: {MAX_RETRIES}\nTimeout: {TIMEOUT}s",
            default_value=None,  # 新增必填参数
            option_list=[
                "These settings can be modified in code:",
                f"MAX_RETRIES = {MAX_RETRIES}",
                f"TIMEOUT = {TIMEOUT}",
                f"RETRY_DELAY = {RETRY_DELAY}"
            ]
        ), 
        text="Advanced Settings",
        width=140
    )
    settings_button.place(relx=0.42, rely=0.5, anchor=CENTER)


class App:
    def __init__(self, window):
        window.title('')
        width        = 500
        height       = 500
        window.geometry("500x500")
        window.minsize(width, height)
        window.resizable(False, False)
        window.iconbitmap(find_by_relative_path("Assets" + os_separator + "logo.ico"))

        window.protocol("WM_DELETE_WINDOW", on_app_close)

        place_app_name()
        place_qualityscaler_button()
        place_github_button()
        # place_telegram_button()
        place_link_textbox()
        place_check_button()
        place_simultaneous_downloads_textbox()
        place_tips()
        place_message_label()             
        place_download_button()
        place_advanced_settings()

if __name__ == "__main__":
    multiprocessing_freeze_support()
    
    # 使用Manager确保跨进程通信
    from multiprocessing import Manager
    manager = Manager()
    processing_queue = manager.Queue(maxsize=10)
    
    set_appearance_mode("Dark")
    set_default_color_theme("dark-blue")

    window = CTk()
    selected_url        = StringVar()
    info_message        = StringVar()
    selected_cpu_number = StringVar()

    selected_url.set("Paste model name here or link https://fapello.com/emily-rat---/")
    selected_cpu_number.set("6")
    info_message.set("Hi :) - Optimized v3.7")
    
    # 新增初始化停止事件
    stop_event = Event()
    
    font   = "Segoe UI"    
    bold8  = CTkFont(family = font, size = 8, weight = "bold")
    bold9  = CTkFont(family = font, size = 9, weight = "bold")
    bold10 = CTkFont(family = font, size = 10, weight = "bold")
    bold11 = CTkFont(family = font, size = 11, weight = "bold")
    bold12 = CTkFont(family = font, size = 12, weight = "bold")
    bold13 = CTkFont(family = font, size = 13, weight = "bold")
    bold14 = CTkFont(family = font, size = 14, weight = "bold")
    bold16 = CTkFont(family = font, size = 16, weight = "bold")
    bold17 = CTkFont(family = font, size = 17, weight = "bold")
    bold18 = CTkFont(family = font, size = 18, weight = "bold")
    bold19 = CTkFont(family = font, size = 19, weight = "bold")
    bold20 = CTkFont(family = font, size = 20, weight = "bold")
    bold21 = CTkFont(family = font, size = 21, weight = "bold")
    bold22 = CTkFont(family = font, size = 22, weight = "bold")
    bold23 = CTkFont(family = font, size = 23, weight = "bold")
    bold24 = CTkFont(family = font, size = 24, weight = "bold")

    # Images
    logo_git       = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}github_logo.png")),    size=(15, 15))
    logo_telegram  = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}telegram_logo.png")),  size=(15, 15))
    stop_icon      = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}stop_icon.png")),      size=(15, 15))
    info_icon      = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}info_icon.png")),      size=(14, 14))
    download_icon  = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}download_icon.png")), size=(15, 15))
    logo_qs        = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}qs_logo.png")),  size=(15, 15))

    app = App(window)
    window.update()
    window.mainloop()
    

