import cv2
import numpy as np
import time
import random
import win32gui
import subprocess
from PIL import Image
from datetime import datetime
import io
import threading
import queue
import atexit
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 设置mumu模拟器的窗口名称、位置和尺寸
mumu_title = "MuMu安卓设备"
ADB_DEVICE = "127.0.0.1:16384"

# 全局变量，用于缓存最后一次截图
last_screenshot = None
# 使用队列在线程间安全地传递截图
screenshot_queue = queue.Queue(maxsize=1)

# 手动输入间隔时间范围和循环次数
input_interval_1 = input("请输入步骤2的间隔时间范围（秒），格式为min-max，默认1-5秒：")
input_interval_2 = input("请输入步骤4的间隔时间范围（秒），格式为min-max，默认1-5秒：")
input_cycle_count = input("请输入循环次数，默认无限循环：")
input_lx = int(input("输入刷的副本类型：\n 1：魂王 \n 2：业原火: \n 3：御灵 \n 4：魂土 ： \n 5：活动：\n "))

# 新增：随机暂停概率和时间的输入
input_pause_prob = input("请输入随机暂停的概率范围（%），格式为min-max，默认20-50：")
input_pause_time = input("请输入随机暂停的时间范围（秒），格式为min-max，默认5-15：")

# 新增：邮件通知配置
sender_email = '3452154521@qq.com'
sender_password = 'zpordtllyuzbcjib'
receiver_email = '1269820768@qq.com'
smtp_server = "smtp.qq.com"  # 示例: QQ邮箱SMTP服务器
smtp_port = 587  # 示例: QQ邮箱SMTP端口


if input_interval_1:
    interval_1 = list(map(int, input_interval_1.split('-')))
else:
    interval_1 = [1, 5]

if input_interval_2:
    interval_2 = list(map(int, input_interval_2.split('-')))
else:
    interval_2 = [1, 5]

if input_cycle_count:
    cycle_count = int(input_cycle_count)
else:
    cycle_count = float('inf')

if input_pause_prob:
    pause_prob_range = list(map(int, input_pause_prob.split('-')))
else:
    pause_prob_range = [20, 50]

if input_pause_time:
    pause_time_range = list(map(float, input_pause_time.split('-')))
else:
    pause_time_range = [5, 15]

# 图像路径
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
    print("请输入类型")

x_image_path = 'img_adb/x.png'

# 循环控制
cycle_number = 0


# Function to record time for each step
def log_time(step_name, start_time):
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"{step_name} 耗时: {elapsed_time:.2f}秒")
    return elapsed_time


# ADB点击函数
def adb_click(x, y):
    print(f"ADB点击坐标: ({x}, {y})")
    subprocess.run(["adb", "-s", ADB_DEVICE, "shell", "input", "tap", str(x), str(y)], check=True)
    time.sleep(random.uniform(0.5, 1))


# ADB后台截图子线程 (使用 exec-out 方式)
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


# 图像识别函数，现在直接使用内存中的图像
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


# 随机决定是否暂停
def should_pause(min_prob, max_prob):
    pause_prob = random.randint(min_prob, max_prob)
    return random.randint(1, 100) <= pause_prob


# 新增：通用检测并点击 x.png 的函数
def check_and_click_x():
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


# 新增：等待图片出现的函数
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


def print_final_stats():
    pass


atexit.register(print_final_stats)


# 新增：邮件通知函数
def send_email_notification(subject, body):
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


# 主循环
try:
    print("开始连接ADB...")
    subprocess.run(["adb", "connect", ADB_DEVICE], check=True)
    print("ADB连接成功。")

    screen_width = 1920
    screen_height = 1080

    screenshot_thread = threading.Thread(target=screenshot_worker, daemon=True)
    screenshot_thread.start()
    time.sleep(2)

    while cycle_number < cycle_count:
        overall_start_time = time.time()
        cycle_number += 1

        if check_and_click_x():
            log_time("Step 1: 处理弹窗", overall_start_time)
            continue

        step_2_start = time.time()
        loc, w, h = wait_for_image(kaishi_img_path, timeout=5, check_interval=1)

        if loc is not None:
            x = loc[1][0] + random.randint(0, w)
            y = loc[0][0] + random.randint(0, h)
            adb_click(x, y)
        else:
            print("警告：在指定时间内未找到'开始'按钮，脚本即将终止。")
            exit()

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
            time.sleep(random.uniform(13, 18))
        log_time("Step 3: 等待时间", step_3_start)

        step_4_start = time.time()

        if check_and_click_x():
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

except Exception as e:
    # 捕获异常，发送通知
    error_message = f"脚本在第 {cycle_number} 次循环中发生错误: {e}"
    send_email_notification("阴阳师脚本错误通知", error_message)
    print(error_message)
    exit()