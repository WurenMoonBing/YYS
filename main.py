import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QGroupBox,
                             QGridLayout, QLabel, QLineEdit, QPushButton,
                             QComboBox, QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal
import configparser

# 导入您改造后的脚本文件
from mumu_adb import run_yys_script, send_email_notification

class WorkerThread(QThread):
    finished = pyqtSignal()
    status_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, config_params):
        super().__init__()
        self.config_params = config_params

    def run(self):
        try:
            self.status_update.emit("脚本正在启动...")
            run_yys_script(self.config_params)
            self.finished.emit()
            self.status_update.emit("脚本运行完毕。")
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.status_update.emit("脚本运行出错。")

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("阴阳师脚本控制面板")
        self.initUI()
        self.load_config()

    def initUI(self):
        main_layout = QVBoxLayout()

        # 脚本参数配置区
        script_group = QGroupBox("脚本配置")
        script_layout = QGridLayout()

        script_layout.addWidget(QLabel("副本类型："), 0, 0)
        self.lx_combo = QComboBox()
        self.lx_combo.addItems(["1：魂王", "2：业原火", "3：御灵", "4：魂土", "5：活动"])
        script_layout.addWidget(self.lx_combo, 0, 1)

        script_layout.addWidget(QLabel("间隔时间1 (min-max)："), 1, 0)
        self.interval1_edit = QLineEdit("1-5")
        script_layout.addWidget(self.interval1_edit, 1, 1)

        script_layout.addWidget(QLabel("间隔时间2 (min-max)："), 2, 0)
        self.interval2_edit = QLineEdit("1-5")
        script_layout.addWidget(self.interval2_edit, 2, 1)

        script_layout.addWidget(QLabel("循环次数："), 3, 0)
        self.cycle_count_edit = QLineEdit("无限循环")
        script_layout.addWidget(self.cycle_count_edit, 3, 1)

        script_layout.addWidget(QLabel("暂停概率 (%)："), 4, 0)
        self.pause_prob_edit = QLineEdit("20-50")
        script_layout.addWidget(self.pause_prob_edit, 4, 1)

        script_layout.addWidget(QLabel("暂停时间 (秒)："), 5, 0)
        self.pause_time_edit = QLineEdit("5-15")
        script_layout.addWidget(self.pause_time_edit, 5, 1)

        script_group.setLayout(script_layout)
        main_layout.addWidget(script_group)

        # 邮件通知配置区
        email_group = QGroupBox("邮件通知配置")
        email_layout = QGridLayout()

        self.email_checkbox = QCheckBox("启用邮件通知")
        self.email_checkbox.stateChanged.connect(self.toggle_email_fields)
        email_layout.addWidget(self.email_checkbox, 0, 0, 1, 2)

        self.sender_email_edit = QLineEdit()
        self.sender_password_edit = QLineEdit()
        self.receiver_email_edit = QLineEdit()
        self.smtp_server_edit = QLineEdit()
        self.smtp_port_edit = QLineEdit()

        email_layout.addWidget(QLabel("发件人邮箱："), 1, 0)
        email_layout.addWidget(self.sender_email_edit, 1, 1)
        email_layout.addWidget(QLabel("发件人密码："), 2, 0)
        email_layout.addWidget(self.sender_password_edit, 2, 1)
        email_layout.addWidget(QLabel("收件人邮箱："), 3, 0)
        email_layout.addWidget(self.receiver_email_edit, 3, 1)
        email_layout.addWidget(QLabel("SMTP服务器："), 4, 0)
        email_layout.addWidget(self.smtp_server_edit, 4, 1)
        email_layout.addWidget(QLabel("SMTP端口："), 5, 0)
        email_layout.addWidget(self.smtp_port_edit, 5, 1)
        email_group.setLayout(email_layout)
        main_layout.addWidget(email_group)

        # 按钮和状态区
        self.start_button = QPushButton("启动脚本")
        self.start_button.clicked.connect(self.start_script)

        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_config)

        main_layout.addWidget(self.start_button)
        main_layout.addWidget(self.save_button)
        self.setLayout(main_layout)
        self.toggle_email_fields() # 初始状态禁用

    def toggle_email_fields(self):
        is_checked = self.email_checkbox.isChecked()
        self.sender_email_edit.setEnabled(is_checked)
        self.sender_password_edit.setEnabled(is_checked)
        self.receiver_email_edit.setEnabled(is_checked)
        self.smtp_server_edit.setEnabled(is_checked)
        self.smtp_port_edit.setEnabled(is_checked)

    def load_config(self):
        config = configparser.ConfigParser()
        if config.read('config.ini'):
            print("读取配置中...")
            try:
                # 脚本配置
                self.interval1_edit.setText(config.get('Script', 'interval_1', fallback="1-5"))
                self.interval2_edit.setText(config.get('Script', 'interval_2', fallback="1-5"))
                self.cycle_count_edit.setText(config.get('Script', 'cycle_count', fallback="无限循环"))
                self.lx_combo.setCurrentIndex(int(config.get('Script', 'lx_type', fallback="0")))
                self.pause_prob_edit.setText(config.get('Script', 'pause_prob', fallback="20-50"))
                self.pause_time_edit.setText(config.get('Script', 'pause_time', fallback="5-15"))

                # 邮件配置
                if config.getboolean('Email', 'enabled', fallback=False):
                    self.email_checkbox.setChecked(True)
                    self.sender_email_edit.setText(config.get('Email', 'sender_email', fallback=''))
                    self.sender_password_edit.setText(config.get('Email', 'sender_password', fallback=''))
                    self.receiver_email_edit.setText(config.get('Email', 'receiver_email', fallback=''))
                    self.smtp_server_edit.setText(config.get('Email', 'smtp_server', fallback=''))
                    self.smtp_port_edit.setText(config.get('Email', 'smtp_port', fallback=''))
                else:
                    self.email_checkbox.setChecked(False)

            except configparser.Error as e:
                print(f"配置文件格式错误: {e}")
        else:
            print("config.ini 不存在，将使用默认值。")
            self.save_config() # 创建一个默认配置文件

    def save_config(self):
        config = configparser.ConfigParser()
        config['Script'] = {
            'interval_1': self.interval1_edit.text(),
            'interval_2': self.interval2_edit.text(),
            'cycle_count': self.cycle_count_edit.text(),
            'lx_type': str(self.lx_combo.currentIndex()),
            'pause_prob': self.pause_prob_edit.text(),
            'pause_time': self.pause_time_edit.text()
        }
        config['Email'] = {
            'enabled': self.email_checkbox.isChecked(),
            'sender_email': self.sender_email_edit.text(),
            'sender_password': self.sender_password_edit.text(),
            'receiver_email': self.receiver_email_edit.text(),
            'smtp_server': self.smtp_server_edit.text(),
            'smtp_port': self.smtp_port_edit.text()
        }
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        print("配置已保存。")

    def start_script(self):
        # 收集所有配置参数
        config_params = {
            'interval_1': self.interval1_edit.text(),
            'interval_2': self.interval2_edit.text(),
            'cycle_count': self.cycle_count_edit.text(),
            'lx_type': self.lx_combo.currentIndex() + 1,
            'pause_prob_range': list(map(int, self.pause_prob_edit.text().split('-'))),
            'pause_time_range': list(map(float, self.pause_time_edit.text().split('-'))),
            'email_enabled': self.email_checkbox.isChecked(),
            'sender_email': self.sender_email_edit.text(),
            'sender_password': self.sender_password_edit.text(),
            'receiver_email': self.receiver_email_edit.text(),
            'smtp_server': self.smtp_server_edit.text(),
            'smtp_port': int(self.smtp_port_edit.text()) if self.smtp_port_edit.text().isdigit() else 587
        }
        self.worker = WorkerThread(config_params)
        self.worker.status_update.connect(print)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.start()
        self.start_button.setEnabled(False) # 禁用按钮防止重复点击

    def handle_error(self, message):
        print(f"脚本发生错误：{message}")
        self.start_button.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())