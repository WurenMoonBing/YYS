import io
import queue
import random
import smtplib
import subprocess
import threading
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import cv2
import numpy as np
from PIL import Image

# 设置mumu模拟器的窗口名称、位置和尺寸
mumu_title = "MuMu安卓设备"
ADB_DEVICE = "127.00.1:16384"

# 全局变量，用于缓存最后一次截图
last_screenshot = None
# 使用队列在线程间安全地传递截图
screenshot_queue = queue.Queue(maxsize=1)

# 新增：邮件通知配置
sender_email = ''
sender_password = ''
receiver_email = ''
smtp_server = ""
smtp_port = 587
email_enabled = False

# 循环控制
cycle_number = 0
cycle_count = float('inf')


def log_time(step_name, start_time):
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"{step_name} 耗时: {elapsed_time:.2f}秒")
    return elapsed_time


def adb_click(x, y):
    print(f"ADB点击坐标: ({x}, {y})")
    subprocess.run(["adb", "-s", ADB_DEVICE, "shell", "input", "tap", str(x), str(y)], check=True)
    time.sleep(random.uniform(0.5, 1))


def screenshot_worker():
    while True:
        cmd = ["adb", "-s", ADB_DEVICE, "exec-out", "screencap", "-p"]
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
            output, _ = process.communicate()
            img_bytes = io.BytesIO(output)
            img = Image.open(img_bytes)
            cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            if screenshot_queue.full():
                screenshot_queue.get()
            screenshot_queue.put(cv_image)

        except Exception as e:
            print(f"截图线程错误: {e}")

        time.sleep(1)


def image_in_memory(image_path, screenshot):
    if screenshot is None:
        return np.where(np.array([])), 0, 0

    img_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(image_path, 0)

    if template is None:
        raise FileNotFoundError(f"Template image not found at: {image_path}")

    if template.shape[0] > img_gray.shape[0] or template.shape[1] > img_gray.shape[1]:
        return np.where(np.array([])), 0, 0

    w, h = template.shape[::-1]
    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8
    loc = np.where(res >= threshold)
    return loc, w, h


def should_pause(min_prob, max_prob):
    pause_prob = random.randint(min_prob, max_prob)
    return random.randint(1, 100) <= pause_prob


def check_and_click_x(x_image_path):
    if screenshot_queue.empty():
        return False
    screenshot = screenshot_queue.get()
    loc, w, h = image_in_memory(x_image_path, screenshot)
    if loc[0].size > 0:
        print("Detected x.png, clicking...")
        x = loc[1][0] + random.randint(0, w)
        y = loc[0][0] + random.randint(0, h)
        adb_click(x, y)
        time.sleep(1)
        return True
    return False


def wait_for_image(image_path, timeout=5, check_interval=1):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if screenshot_queue.empty():
            time.sleep(check_interval)
            continue

        screenshot = screenshot_queue.get()
        loc, w, h = image_in_memory(image_path, screenshot)

        if loc[0].size > 0:
            return loc, w, h

        time.sleep(check_interval)
    return None, None, None


def send_email_notification(subject, body):
    if not email_enabled:
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print("邮件通知已发送。")
    except Exception as e:
        print(f"邮件发送失败: {e}")


def run_yys_script(config_params):
    global cycle_count, cycle_number, sender_email, sender_password, receiver_email, smtp_server, smtp_port, email_enabled

    # 从配置参数中获取值
    interval_1 = list(map(int, config_params['interval_1'].split('-')))
    interval_2 = list(map(int, config_params['interval_2'].split('-')))
    cycle_count_str = config_params['cycle_count']
    if cycle_count_str.lower() == '无限循环':
        cycle_count = float('inf')
    else:
        cycle_count = int(cycle_count_str)

    input_lx = config_params['lx_type']
    pause_prob_range = config_params['pause_prob_range']
    pause_time_range = config_params['pause_time_range']

    # 邮件配置
    email_enabled = config_params['email_enabled']
    if email_enabled:
        sender_email = config_params['sender_email']
        sender_password = config_params['sender_password']
        receiver_email = config_params['receiver_email']
        smtp_server = config_params['smtp_server']
        smtp_port = config_params['smtp_port']

    # 图像路径
    kaishi_img_path = ''
    if input_lx == 1:
        kaishi_img_path = 'img_adb/yuhun12.png'
    elif input_lx == 2:
        kaishi_img_path = 'img_adb/yeyuanhuo.png'
    elif input_lx == 3:
        kaishi_img_path = 'img_adb/yuling.png'
    elif input_lx == 4:
        kaishi_img_path = 'img_adb/yuhun11.png'
    elif input_lx == 5:
        kaishi_img_path = 'img_adb/huodong.png'
    else:
        raise ValueError("请输入类型")

    x_image_path = 'img_adb/x.png'

    print("开始连接ADB...")
    subprocess.run(["adb", "connect", ADB_DEVICE], check=True)
    print("ADB连接成功。")

    screen_width = 1920
    screen_height = 1080

    screenshot_thread = threading.Thread(target=screenshot_worker, daemon=True)
    screenshot_thread.start()
    time.sleep(2)

    cycle_number = 0
    while cycle_number < cycle_count:
        overall_start_time = time.time()
        cycle_number += 1

        if check_and_click_x(x_image_path):
            log_time("Step 1: 处理弹窗", overall_start_time)
            continue

        step_2_start = time.time()
        loc, w, h = wait_for_image(kaishi_img_path, timeout=5, check_interval=1)

        if loc is None:
            raise RuntimeError("未找到开始按钮，脚本停止。")

        x = loc[1][0] + random.randint(0, w)
        y = loc[0][0] + random.randint(0, h)
        adb_click(x, y)

        log_time("Step 2: 图像识别和点击", step_2_start)

        if should_pause(pause_prob_range[0], pause_prob_range[1]):
            print(f"随机暂停中... 概率: {pause_prob_range[0]}%-{pause_prob_range[1]}%")
            time.sleep(random.uniform(pause_time_range[0], pause_time_range[1]))

        step_3_start = time.time()
        if input_lx == 1:
            time.sleep(random.uniform(35, 40))
        elif input_lx == 2:
            time.sleep(random.uniform(28, 32))
        elif input_lx == 3:
            time.sleep(random.uniform(20, 30))
        elif input_lx == 4:
            time.sleep(random.uniform(25, 45))
        elif input_lx == 5:
            time.sleep(random.uniform(14, 18))
        log_time("Step 3: 等待时间", step_3_start)

        step_4_start = time.time()

        if check_and_click_x(x_image_path):
            print("Detected x.png at settlement, clicking...")

        if input_lx == 5:
            x = screen_width - 500 + random.randint(0, 300)
            y = screen_height - 300 + random.randint(0, 150)
        else:
            x = screen_width - 400 - 20 + random.randint(0, 400)
            y = screen_height - 150 + random.randint(50, 150)

        print(f"ADB点击窗口，坐标：x: {x}, y: {y}")
        adb_click(x, y)
        time.sleep(1.0)
        log_time("Step 4: 随机点击或图像匹配", step_4_start)

        overall_elapsed = time.time() - overall_start_time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"第 {cycle_number} 次运行，总耗时: {overall_elapsed:.2f} 秒。当前时间: {current_time}")

    send_email_notification("阴阳师脚本运行完毕", f"脚本已完成 {cycle_number} 次循环。")

# 移除原有的 try-except 块和 exit()，让主调函数来处理异常。
# send_email_notification() 函数现在也需要接受参数，或从全局变量中读取。