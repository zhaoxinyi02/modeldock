import json
import os
import sys
import threading
import urllib.request
import webbrowser
try:
    import winreg
except ImportError:
    winreg = None

from PySide6.QtCore import QObject, Qt, QTimer, Signal, QSettings
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QPixmap, QPainter, QPainterPath, QPen, QPalette
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QProgressDialog, QPushButton, QPlainTextEdit, QStackedWidget, QSystemTrayIcon, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QListWidget,
    QListWidgetItem, QInputDialog, QToolButton, QStyleFactory, QDialogButtonBox
)

from constants import *
import account_info
import codex_control
import codex_repair
import conversation_guard
import config_manager
import gateway
import restore_manager
import runtime
from version import check_update


def system_dark_mode():
    try:
        if winreg is None:
            raise RuntimeError("Windows registry is unavailable")
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        return int(winreg.QueryValueEx(key, "AppsUseLightTheme")[0]) == 0
    except Exception:
        app = QApplication.instance()
        return bool(app and app.palette().window().color().lightness() < 128)


def app_icon(dark=None):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
    dark = system_dark_mode() if dark is None else dark
    if IS_MACOS:
        names = ("app_icon_macos.png", "logo.png")
    else:
        names = (
            ("app_logo_light.png" if dark else "app_logo_dark.png"),
            ("app_icon_light.ico" if dark else "app_icon_dark.ico"),
            "app_icon.ico",
        )
    for name in names:
        path = os.path.join(base, "assets", name)
        if os.path.exists(path):
            return QIcon(path)
    return QIcon()


def tray_icon():
    if not IS_MACOS:
        return app_icon()
    roots = [
        getattr(sys, "_MEIPASS", ""),
        os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "Resources")),
        os.path.dirname(os.path.dirname(__file__)),
    ]
    paths = []
    for root in roots:
        if root:
            paths.extend((
                os.path.join(root, "assets", "menu_bar_iconTemplate@2x.png"),
                os.path.join(root, "assets", "menu_bar_iconTemplate.png"),
            ))
    icon = QIcon()
    for path in paths:
        if not os.path.isfile(path):
            continue
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            icon = QIcon(pixmap)
            break
    # Never fall back to the orange application icon in the macOS menu bar.
    if icon.isNull():
        return QIcon()
    icon.setIsMask(True)
    return icon


def eye_icon(hidden=False):
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    color = QApplication.palette().color(QPalette.Text)
    pen = QPen(color, 1.5)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    path = QPainterPath()
    path.moveTo(1.5, 9)
    path.cubicTo(4.5, 3.5, 13.5, 3.5, 16.5, 9)
    path.cubicTo(13.5, 14.5, 4.5, 14.5, 1.5, 9)
    painter.drawPath(path)
    painter.drawEllipse(6.7, 6.7, 4.6, 4.6)
    if hidden:
        painter.drawLine(3, 3, 15, 15)
    painter.end()
    return QIcon(pixmap)


LIGHT_QSS = """
QMainWindow { background: #f8f9fb; }
QWidget { font-family: "SF Pro Text", "PingFang SC", "Segoe UI", "Microsoft YaHei UI"; font-size: 13px; color: #202124; }
QLabel { border: none; background: transparent; }
QLabel#Title { font-size: 25px; font-weight: 700; color: #202124; }
QLabel#Subtitle { color: #5f6368; font-size: 13px; }
QLabel#CardTitle { font-size: 14px; font-weight: 700; color: #202124; }
QLabel#Metric { color: #70757a; font-size: 12px; }
QLabel#Value { color: #202124; font-size: 20px; font-weight: 700; }
QLabel#Pill { color: #0b57d0; background: #e8f0fe; border-radius: 8px; padding: 5px 9px; font-weight: 600; }
QWidget#Card { background: #ffffff; border: 1px solid #e1e5ea; border-radius: 10px; }
QWidget#HeroCard { background: #202124; border-radius: 12px; }
QLabel#HeroTitle { color: #ffffff; font-size: 22px; font-weight: 700; }
QLabel#HeroText { color: #e8eaed; font-size: 13px; }
QPushButton { background: #202124; color: #ffffff; border: 1px solid #202124; border-radius: 7px; padding: 8px 14px; font-weight: 600; outline: none; }
QPushButton:hover { background: #35363a; border-color: #35363a; }
QPushButton:focus { outline: none; border: 0; }
QPushButton:pressed { background: #000000; border-color: #000000; }
QPushButton:disabled { background: #f1f3f4; color: #9aa0a6; border-color: #f1f3f4; }
QPushButton#Secondary, QPushButton#ModeOption { background: #ffffff; color: #3c4043; border-color: #dadce0; }
QPushButton#Secondary:hover, QPushButton#ModeOption:hover { background: #f8fafd; border-color: #bdc1c6; }
QPushButton#Danger { background: #d93025; border-color: #d93025; }
QPushButton#Danger:hover { background: #b3261e; border-color: #b3261e; }
QPushButton#ModeActive { background: #e8f0fe; color: #0b57d0; border-color: #a8c7fa; }
QPushButton#ModeActive:disabled { background: #e8f0fe; color: #0b57d0; border-color: #a8c7fa; }
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {
  background: #ffffff; border: 1px solid #d6dee8; border-radius: 9px; padding: 8px;
}
QComboBox { min-height: 20px; padding-right: 32px; }
QComboBox QAbstractItemView { padding: 5px; border: 1px solid #d6dee8; border-radius: 8px; selection-background-color: #e8f0fe; }
QToolButton { background: transparent; border: 0; border-radius: 6px; padding: 5px 8px; color: #5f6368; }
QToolButton:hover { background: #eef2f7; }
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
  border: 1px solid #60a5fa;
}
QTableWidget { background: #ffffff; border: 1px solid #e1e5ea; border-radius: 8px; gridline-color: #eef0f2; selection-background-color: #e8f0fe; selection-color: #202124; outline: none; }
QTableWidget:focus { outline: none; border: 1px solid #c4c7c5; }
QTableWidget::item:focus { outline: none; border: 0; }
QHeaderView::section { background: #f8f9fa; color: #5f6368; padding: 9px; border: 0; border-bottom: 1px solid #e1e5ea; font-weight: 600; }
QListWidget { background: #ffffff; color: #3c4043; border: 0; border-right: 1px solid #e1e5ea; padding: 14px 10px; font-size: 14px; outline: none; }
QListWidget::item { padding: 11px 13px; border-radius: 7px; margin: 2px 0; outline: none; border: 0; }
QListWidget::item:hover { background: #f1f3f4; }
QListWidget::item:selected { background: #e8f0fe; color: #0b57d0; font-weight: 600; }
QListWidget::item:focus { outline: none; border: 0; }
QProgressDialog { background: #ffffff; border: 1px solid #e7ebf0; border-radius: 12px; }
QProgressBar { border: 1px solid #d6dee8; border-radius: 7px; background: #eef2f7; text-align: center; min-height: 14px; }
QProgressBar::chunk { background: #2563eb; border-radius: 7px; }
"""

DARK_QSS = LIGHT_QSS + """
QMainWindow { background: #111315; }
QWidget { color: #e8eaed; }
QLabel#Title, QLabel#CardTitle, QLabel#Value { color: #f1f3f4; }
QLabel#Subtitle, QLabel#Metric { color: #9aa0a6; }
QWidget#Card { background: #1b1e22; border-color: #30343a; }
QWidget#HeroCard { background: #050607; border: 1px solid #30343a; }
QPushButton { background: #f1f3f4; color: #17191c; border-color: #f1f3f4; }
QPushButton:hover { background: #ffffff; border-color: #ffffff; }
QPushButton:pressed { background: #d8dadd; border-color: #d8dadd; }
QPushButton:disabled { background: #272a2f; color: #6f7378; border-color: #272a2f; }
QPushButton#Secondary, QPushButton#ModeOption { background: #202328; color: #e8eaed; border-color: #3a3e44; }
QPushButton#Secondary:hover, QPushButton#ModeOption:hover { background: #292d32; border-color: #5f6368; }
QPushButton#ModeActive, QPushButton#ModeActive:disabled { background: #263b61; color: #a8c7fa; border-color: #4d74b7; }
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit { background: #191c20; color: #e8eaed; border-color: #3a3e44; }
QTableWidget { background: #17191c; color: #e8eaed; border-color: #30343a; gridline-color: #292d32; selection-background-color: #263b61; selection-color: #ffffff; }
QHeaderView::section { background: #202328; color: #bdc1c6; border-bottom-color: #3a3e44; }
QListWidget { background: #111315; color: #d7d9dd; border-right-color: #30343a; }
QListWidget::item:hover { background: #202328; }
QListWidget::item:selected { background: #263b61; color: #a8c7fa; }
QProgressDialog { background: #1b1e22; border-color: #30343a; }
QProgressBar { background: #292d32; border-color: #3a3e44; }
"""

# On macOS, leave buttons, text fields, combo boxes, menus and scroll bars to
# QMacStyle/AppKit.  Only product structure and typography are customized.
MACOS_QSS = """
QWidget { font-family: ".AppleSystemUIFont", "SF Pro Text", "PingFang SC"; font-size: 13px; }
QLabel#Title { font-size: 26px; font-weight: 700; }
QLabel#Subtitle, QLabel#Metric { color: palette(mid); font-size: 12px; }
QLabel#CardTitle { font-size: 14px; font-weight: 600; }
QLabel#Value { font-size: 20px; font-weight: 600; }
QLabel#Pill { color: palette(highlighted-text); background: palette(highlight); border-radius: 8px; padding: 5px 9px; font-weight: 600; }
QWidget#Card, QWidget#HeroCard { background: palette(base); border: 1px solid palette(midlight); border-radius: 10px; }
QLabel#HeroTitle { font-size: 21px; font-weight: 650; }
QLabel#HeroText { color: palette(mid); }
QPushButton#Danger { color: #d70015; }
QPushButton#ModeActive { font-weight: 650; }
QTableWidget { border: 1px solid palette(midlight); border-radius: 8px; gridline-color: palette(midlight); }
QHeaderView::section { padding: 7px; font-weight: 600; }
QListWidget { border: 0; border-right: 1px solid palette(midlight); padding: 14px 10px; font-size: 14px; }
QListWidget::item { padding: 10px 12px; border-radius: 7px; margin: 2px 0; }
QListWidget::item:selected { background: palette(highlight); color: palette(highlighted-text); }
QToolButton { border: 0; padding: 4px 7px; }
"""


class Card(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(10)
        label = QLabel(title)
        label.setObjectName("CardTitle")
        self.layout.addWidget(label)


class HeroCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeroCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(22, 18, 22, 18)
        self.layout.setSpacing(8)
        self.title = QLabel("检测中")
        self.title.setObjectName("HeroTitle")
        self.text = QLabel("")
        self.text.setObjectName("HeroText")
        self.text.setWordWrap(True)
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.text)


class Metric(QWidget):
    def __init__(self, label):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.value = QLabel("-")
        self.value.setObjectName("Value")
        caption = QLabel(label)
        caption.setObjectName("Metric")
        layout.addWidget(self.value)
        layout.addWidget(caption)


class TaskSignals(QObject):
    finished = Signal(object, object)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME + " " + APP_VERSION)
        self.setWindowIcon(app_icon())
        self.resize(1280, 800)
        self.setMinimumSize(1080, 680)
        saved_geometry = QSettings(APP_NAME, APP_NAME).value("mainWindowGeometry")
        if saved_geometry:
            self.restoreGeometry(saved_geometry)
            if self.width() < 1280 or self.height() < 800:
                self.resize(max(1280, self.width()), max(800, self.height()))
        self._allow_exit = False
        self._task_signals = []
        self._busy_dialog = None
        self._dark_mode = None
        self._build_ui()
        self._remove_focus_frames()
        self._build_tray()
        self.refresh_all()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(8000)
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self._refresh_theme)
        self.theme_timer.start(2000)

    def _build_ui(self):
        root = QWidget()
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        self.nav = QListWidget()
        self.nav.setFixedWidth(190 if IS_MACOS else 220)
        for text in ("首页", "配置管理", "回退点", "设置"):
            QListWidgetItem(text, self.nav)
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self._switch_page)
        self.stack = QStackedWidget()
        main.addWidget(self.nav)
        main.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.stack.addWidget(self._status_page())
        self.stack.addWidget(self._config_page())
        self.stack.addWidget(self._restore_page())
        self.stack.addWidget(self._settings_page())

    def _refresh_theme(self, force=False):
        dark = system_dark_mode()
        if not force and dark == self._dark_mode:
            return
        self._dark_mode = dark
        QApplication.instance().setStyleSheet(MACOS_QSS if IS_MACOS else (DARK_QSS if dark else LIGHT_QSS))
        icon = app_icon(dark)
        self.setWindowIcon(icon)
        if hasattr(self, "tray"):
            self._tray_template_icon = tray_icon() if IS_MACOS else icon
            self.tray.setIcon(self._tray_template_icon)

    def _page(self, title, subtitle):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        h = QLabel(title)
        h.setObjectName("Title")
        s = QLabel(subtitle)
        s.setObjectName("Subtitle")
        layout.addWidget(h)
        layout.addWidget(s)
        return page, layout

    def _status_page(self):
        page, layout = self._page("Codex Gateway", "纯官方直连；混合模式由本地网关转发官方订阅与第三方 API")
        self.mode_hero = HeroCard()
        layout.addWidget(self.mode_hero)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        layout.addLayout(grid)
        self.gateway_card = Card("本地网关")
        self.gateway_status = QLabel("检测中")
        self.gateway_status.setObjectName("Pill")
        self.gateway_detail = QLabel("")
        self.gateway_models = QLabel("")
        self.gateway_card.layout.addWidget(self.gateway_status)
        self.gateway_card.layout.addWidget(self.gateway_detail)
        self.gateway_card.layout.addWidget(self.gateway_models)
        btns = QHBoxLayout()
        self.gateway_start_btn = QPushButton("启动网关")
        self.gateway_stop_btn = QPushButton("停止网关")
        self.gateway_restart_btn = QPushButton("重启网关")
        self.gateway_stop_btn.setObjectName("Secondary")
        self.gateway_restart_btn.setObjectName("Secondary")
        self.gateway_start_btn.clicked.connect(lambda: self._run_task("正在启动网关", self._start_gateway, self._gateway_done))
        self.gateway_stop_btn.clicked.connect(lambda: self._run_task("正在停止网关", self._stop_gateway, self._gateway_done))
        self.gateway_restart_btn.clicked.connect(lambda: self._run_task("正在重启网关", self._restart_gateway, self._gateway_done))
        for b in (self.gateway_start_btn, self.gateway_stop_btn, self.gateway_restart_btn):
            btns.addWidget(b)
        self.gateway_card.layout.addLayout(btns)

        self.codex_card = Card("Codex Desktop")
        self.codex_status = QLabel("检测中")
        self.codex_status.setObjectName("Pill")
        self.codex_detail = QLabel("")
        self.codex_card.layout.addWidget(self.codex_status)
        self.codex_card.layout.addWidget(self.codex_detail)
        codex_btns = QHBoxLayout()
        self.codex_toggle_btn = QPushButton("打开 Codex")
        self.codex_restart_btn = QPushButton("重启 Codex")
        self.codex_restart_btn.setObjectName("Secondary")
        self.codex_toggle_btn.clicked.connect(lambda: self._run_task("正在处理 Codex", self._toggle_codex, self._codex_done))
        self.codex_restart_btn.clicked.connect(lambda: self._run_task("正在重启 Codex", self._restart_codex, self._codex_done))
        codex_btns.addWidget(self.codex_toggle_btn)
        codex_btns.addWidget(self.codex_restart_btn)
        self.codex_card.layout.addLayout(codex_btns)

        self.account_card = Card("官方账号")
        self.account_status = QLabel("")
        self.account_status.setTextFormat(Qt.RichText)
        self.account_card.layout.addWidget(self.account_status)
        grid.addWidget(self.gateway_card, 0, 0)
        grid.addWidget(self.codex_card, 0, 1)
        grid.addWidget(self.account_card, 1, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addStretch(1)
        return page

    def _config_page(self):
        page, layout = self._page("配置管理", "内置模型固定为 0 号，用户模型从 1 开始")
        self.config_table = QTableWidget(0, 7)
        self.config_table.setHorizontalHeaderLabels(["序号", "名称", "上游模型", "类型", "URL", "上下文", "最大输出"])
        self.config_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.config_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.config_table.verticalHeader().setVisible(False)
        self.config_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.config_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.config_table.setAlternatingRowColors(True)
        self.config_table.setTextElideMode(Qt.ElideMiddle)
        self.config_table.cellDoubleClicked.connect(lambda _row, _column: self._modify_model())
        for column, width in {0: 48, 1: 180, 2: 145, 3: 135, 4: 280, 5: 95, 6: 95}.items():
            self.config_table.setColumnWidth(column, width)
        layout.addWidget(self.config_table, 1)
        btns = QHBoxLayout()
        for text, fn, obj in [
            ("刷新", self.refresh_config, "Secondary"),
            ("添加模型", self._add_model, ""),
            ("修改", self._modify_model, "Secondary"),
            ("上移", lambda: self._move_model(-1), "Secondary"),
            ("下移", lambda: self._move_model(1), "Secondary"),
            ("删除", self._remove_model, "Danger"),
            ("查看脱敏配置", self._view_config, "Secondary"),
        ]:
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        layout.addLayout(btns)
        return page

    def _restore_page(self):
        page, layout = self._page("回退点", "自动回退和手动回退分开保存，可恢复 Codex 与网关配置")
        self.restore_table = QTableWidget(0, 5)
        self.restore_table.setHorizontalHeaderLabels(["类型", "名称", "时间", "备注", "项目数"])
        self.restore_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.restore_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.restore_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.restore_table, 1)
        btns = QHBoxLayout()
        for text, fn, obj in [
            ("刷新", self.refresh_restore_points, "Secondary"),
            ("新建手动回退点", self._manual_restore_point, ""),
            ("恢复选中回退点", self._restore_selected, "Danger"),
        ]:
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        layout.addLayout(btns)
        return page

    def _settings_page(self):
        page, layout = self._page("设置", "模式、会话保护、网关与版本")
        status = Card("Codex 登录状态")
        self.mode_label = QLabel("检测中")
        status.layout.addWidget(self.mode_label)
        self.provider_state_label = QLabel("")
        status.layout.addWidget(self.provider_state_label)
        login_btn = QPushButton("登录/刷新网关官方订阅凭据")
        login_btn.setObjectName("Secondary")
        login_btn.clicked.connect(self._codex_login)
        status.layout.addWidget(login_btn)
        usage_btn = QPushButton("打开官方 Usage 页面")
        usage_btn.setObjectName("Secondary")
        usage_btn.clicked.connect(lambda: webbrowser.open("https://chatgpt.com/codex/settings/usage"))
        status.layout.addWidget(usage_btn)
        mode_btns = QHBoxLayout()
        self.mode_buttons = {}
        for key, text, fn in [
            ("pure_official", "纯官方订阅", self._switch_official_only),
            ("official_plus_api", "官方订阅 + 第三方 API", lambda: self._repair_codex(True)),
            ("api_only", "纯 API + 第三方模型", lambda: self._repair_codex(False)),
        ]:
            b = QPushButton(text)
            b.setObjectName("ModeOption")
            b.clicked.connect(fn)
            self.mode_buttons[key] = b
            mode_btns.addWidget(b)
        status.layout.addLayout(mode_btns)
        layout.addWidget(status)

        conversations = Card("会话保护")
        self.conversation_label = QLabel("")
        conversations.layout.addWidget(self.conversation_label)
        conversation_btns = QHBoxLayout()
        snapshot = QPushButton("创建会话索引快照")
        repair = QPushButton("修复并统一会话列表")
        repair.setObjectName("Secondary")
        snapshot.clicked.connect(self._snapshot_conversations)
        repair.clicked.connect(self._repair_conversation_index)
        conversation_btns.addWidget(snapshot)
        conversation_btns.addWidget(repair)
        conversation_btns.addStretch(1)
        conversations.layout.addLayout(conversation_btns)
        layout.addWidget(conversations)

        auto = Card("开机自启与端口")
        self.auto_label = QLabel("")
        self.port_edit = QLineEdit()
        self.port_edit.setFixedWidth(120)
        pbtn = QPushButton("应用端口并重启")
        pbtn.clicked.connect(self._apply_port)
        row = QHBoxLayout()
        row.addWidget(QLabel("端口"))
        row.addWidget(self.port_edit)
        row.addWidget(pbtn)
        row.addStretch(1)
        auto.layout.addWidget(self.auto_label)
        auto.layout.addLayout(row)
        abtns = QHBoxLayout()
        on = QPushButton("开启自启")
        off = QPushButton("关闭自启")
        off.setObjectName("Secondary")
        on.clicked.connect(self._enable_autostart)
        off.clicked.connect(self._disable_autostart)
        abtns.addWidget(on)
        abtns.addWidget(off)
        abtns.addStretch(1)
        auto.layout.addLayout(abtns)
        layout.addWidget(auto)

        about = Card("关于")
        self.version_label = QLabel(APP_VERSION + "  ·  ModelDock")
        about.layout.addWidget(self.version_label)
        up = QPushButton("检查更新")
        up.clicked.connect(lambda: self._run_task("正在检查更新", self._check_update, self._update_done))
        about.layout.addWidget(up)
        layout.addWidget(about)
        layout.addStretch(1)
        return page

    def _remove_focus_frames(self):
        if IS_MACOS:
            # Preserve AppKit keyboard focus and VoiceOver/accessibility on Mac.
            return
        for button in self.findChildren(QPushButton):
            button.setFocusPolicy(Qt.NoFocus)
        for table in self.findChildren(QTableWidget):
            table.setFocusPolicy(Qt.NoFocus)
        self.nav.setFocusPolicy(Qt.NoFocus)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        self._tray_template_icon = tray_icon()
        self.tray.setIcon(self._tray_template_icon)
        self.tray.setToolTip(APP_NAME)
        menu = self.tray.contextMenu()
        if menu is None:
            from PySide6.QtWidgets import QMenu
            menu = QMenu()
            self.tray.setContextMenu(menu)
        show = QAction("显示窗口", self)
        show.triggered.connect(self.show_window)
        start = QAction("启动/重启网关", self)
        start.triggered.connect(self._tray_restart_gateway)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.exit_app)
        menu.addAction(show)
        menu.addAction(start)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.activated.connect(lambda reason: self.show_window() if reason == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()
        # AppKit can briefly replace an early tray icon with the application icon
        # while the menu-bar item is being attached. Reapply it after attachment.
        QTimer.singleShot(0, lambda: self.tray.setIcon(self._tray_template_icon))
        QTimer.singleShot(500, lambda: self.tray.setIcon(self._tray_template_icon))

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 1:
            self.refresh_config()
        elif index == 2:
            self.refresh_restore_points()
        elif index == 3:
            self.refresh_settings()

    def refresh_all(self):
        self.refresh_status()
        self.refresh_config()
        self.refresh_restore_points()
        self.refresh_settings()

    def refresh_status(self):
        s = gateway.get_status()
        if s["running"] and s["responding"]:
            self.gateway_status.setText("运行中 · 正常响应")
        elif s["running"]:
            self.gateway_status.setText("运行中 · 暂无响应")
        else:
            self.gateway_status.setText("已停止")
        self.gateway_detail.setText("PID: {}    地址: {}".format(s.get("pid") or "-", s.get("url") or "-"))
        self.gateway_models.setText("模型数量: " + str(len(s.get("models") or [])))
        self.gateway_start_btn.setEnabled(not s["running"])
        self.gateway_stop_btn.setEnabled(s["running"])
        self.gateway_restart_btn.setEnabled(True)

        cs = codex_control.get_status()
        self.codex_status.setText("运行中" if cs["running"] else "未运行")
        self.codex_detail.setText("进程数: {}".format(cs["count"]))
        self.codex_toggle_btn.setText("停止 Codex" if cs["running"] else "打开 Codex")
        self.codex_restart_btn.setEnabled(cs["running"])

        ai = account_info.get_account_info()
        if ai["mode_key"] == "pure_official":
            self.gateway_start_btn.setEnabled(False)
            self.gateway_restart_btn.setEnabled(False)
            self.gateway_status.setText("已按纯官方模式停止")
            self.gateway_detail.setText("纯官方订阅模式不会启动本地网关")
        self.mode_hero.title.setText(ai["mode"])
        desc_map = {
            "pure_official": "当前 Codex 使用官方 provider，没有接入本地 CLIProxyAPI 第三方模型网关。",
            "official_plus_api": "当前由本地网关转发官方订阅凭据与第三方 API，可在同一模型列表中切换。",
            "api_only": "当前 Codex 使用本地 CLIProxyAPI provider，不依赖官方订阅登录，适合只用自配 API 的用户。",
            "not_logged_in": "Codex 已安装，但未检测到官方账号登录。",
            "not_installed": "未检测到 Codex Desktop 安装。",
        }
        self.mode_hero.text.setText(desc_map.get(ai["mode_key"], "当前模式需要检查 Codex 配置。"))
        self.account_status.setText(
            "<b>邮箱</b>：{email}<br>"
            "<b>套餐</b>：{plan}（本机最新凭据返回）<br>"
            "<b>状态更新时间</b>：{refreshed_at}<br>"
            "<b>订阅有效期至</b>：{expired}<br>"
            "<b>网关订阅凭据</b>：{gateway_auth}<br>"
            "<b>第三方模型</b>：{third_party_count}<br>"
            "<b>用量</b>：{usage}".format(
                gateway_auth="已就绪" if ai.get("gateway_logged_in") else "未配置（混合模式需登录一次）",
                **ai
            )
        )

    def refresh_config(self):
        try:
            summary = config_manager.get_summary()
            entries = sorted(summary["entries"], key=lambda x: (x.get("order", 10**9), x["number"]))
            self.config_table.setRowCount(len(entries))
            self._entry_by_row = {}
            for row, e in enumerate(entries):
                vals = [
                    e.get("display_number", e["number"]), e["display_name"], e["upstream"],
                    self._type_label(e["section"]), e["base_url"], e.get("context_window") or "-",
                    e.get("max_output_tokens") or "-",
                ]
                for col, val in enumerate(vals):
                    item = QTableWidgetItem(str(val))
                    if e.get("built_in"):
                        item.setForeground(Qt.darkGray)
                    item.setToolTip(str(val))
                    self.config_table.setItem(row, col, item)
                self._entry_by_row[row] = e
        except Exception as ex:
            self._error(str(ex))

    @staticmethod
    def _type_label(section):
        return {
            "codex-api-key": "OpenAI Responses",
            "openai-compatibility": "OpenAI 兼容",
            "claude-api-key": "Anthropic 兼容",
        }.get(section, section)

    def refresh_restore_points(self):
        points = restore_manager.list_restore_points()
        self.restore_table.setRowCount(len(points))
        self._restore_by_row = {}
        for row, p in enumerate(points):
            vals = [("手动" if p["kind"] == "manual" else "自动"), p["name"], p["created_at"], p["notes"], p["items"]]
            for col, val in enumerate(vals):
                self.restore_table.setItem(row, col, QTableWidgetItem(str(val)))
            self._restore_by_row[row] = p

    def refresh_settings(self):
        ai = account_info.get_account_info()
        self.mode_label.setText("当前模式：{mode}\n账号：{email}    套餐：{plan}".format(**ai))
        st = codex_repair.read_effective_provider_state()
        auth = st["requires_openai_auth"]
        if auth is True:
            auth_text = "true（保留官方订阅登录）"
        elif auth is False:
            auth_text = "false（纯 API 模式）"
        else:
            auth_text = "未设置"
        self.provider_state_label.setText(
            "实际配置：model_provider = {model_provider}；requires_openai_auth = {auth}".format(
                model_provider=st["model_provider"], auth=auth_text
            )
        )
        for key, button in getattr(self, "mode_buttons", {}).items():
            active = key == ai["mode_key"]
            button.setObjectName("ModeActive" if active else "ModeOption")
            button.setEnabled(not active)
            button.style().unpolish(button)
            button.style().polish(button)
        conversation = conversation_guard.get_status()
        self.conversation_label.setText(
            "本地会话：{active_sessions} 个活动 / {archived_sessions} 个归档；侧栏索引：{indexed_threads} 条；索引快照：{snapshots} 份。"
            .format(**conversation)
        )
        try:
            self.port_edit.setText(str(config_manager.get_port()))
        except Exception:
            self.port_edit.setText(str(GATEWAY_DEFAULT_PORT))
        state = gateway.get_scheduled_task_state()
        self.auto_label.setText("自启状态: " + ("已开启" if state in ("ready", "running") else "未开启"))

    def selected_entry(self):
        row = self.config_table.currentRow()
        return getattr(self, "_entry_by_row", {}).get(row)

    def _after_config_change(self, name):
        config_manager.ensure_builtin_model()
        if account_info.get_account_info()["mode_key"] == "pure_official":
            gateway.stop()
            return True
        ok = gateway.restart()
        if ok and gateway.is_responding():
            restore_manager.create_restore_point("auto", name, "配置修改后自动保存")
        return ok

    def _add_model(self):
        dlg = ModelDialog(self)
        if dlg.exec() == QDialog.Accepted:
            r = dict(dlg.result)
            dlg.deleteLater()
            def work():
                config_manager.add_model(**r)
                return self._after_config_change("add-model")
            self._run_task("正在添加模型并重启网关", work, lambda ok: self._config_done(ok, "模型已添加。"))

    def _modify_model(self):
        e = self.selected_entry()
        if not e:
            self._warn("请先选择一个模型。")
            return
        if e.get("built_in"):
            self._warn("内置免费模型不可修改。")
            return
        dlg = ModelDialog(self, e)
        if dlg.exec() == QDialog.Accepted:
            result = dict(dlg.result)
            dlg.deleteLater()
            def work():
                config_manager.modify_model(e["number"], **result)
                return self._after_config_change("modify-model")
            self._run_task("正在修改模型并重启网关", work, lambda ok: self._config_done(ok, "模型已修改。"))

    def _remove_model(self):
        e = self.selected_entry()
        if not e:
            self._warn("请先选择一个模型。")
            return
        if e.get("built_in"):
            self._warn("内置免费模型不可删除。")
            return
        if QMessageBox.question(self, "确认删除", "确认删除 {} ?".format(e["display_name"])) == QMessageBox.Yes:
            def work():
                config_manager.remove_model(e["number"])
                return self._after_config_change("remove-model")
            self._run_task("正在删除模型并重启网关", work, lambda ok: self._config_done(ok, "模型已删除。"))

    def _move_model(self, direction):
        e = self.selected_entry()
        if not e:
            self._warn("请先选择一个模型。")
            return
        if e.get("built_in"):
            self._warn("内置免费模型固定在最上方。")
            return
        if not config_manager.move_model(e["number"], direction):
            return
        self.refresh_config()
        for row, item in self._entry_by_row.items():
            if item["number"] == e["number"]:
                self.config_table.selectRow(row)
                break
        if account_info.get_account_info()["mode_key"] != "pure_official":
            config_manager.invalidate_codex_model_cache()

    def _view_config(self):
        dlg = TextDialog("脱敏后的 config.yaml", config_manager.get_redacted_config(), self)
        dlg.exec()

    def _manual_restore_point(self):
        name, ok = QInputDialog.getText(self, "手动回退点", "名称")
        if not ok:
            return
        notes, _ = QInputDialog.getMultiLineText(self, "备注", "备注")
        restore_manager.create_restore_point("manual", name, notes)
        self.refresh_restore_points()

    def _restore_selected(self):
        row = self.restore_table.currentRow()
        p = getattr(self, "_restore_by_row", {}).get(row)
        if not p:
            self._warn("请先选择一个回退点。")
            return
        if QMessageBox.question(self, "确认回退", "回退会覆盖当前 Codex/网关配置，继续?") == QMessageBox.Yes:
            def work():
                restore_manager.restore(p["id"])
                if account_info.get_account_info()["mode_key"] == "pure_official":
                    gateway.stop()
                    return True
                return gateway.restart()
            self._run_task("正在恢复回退点并重启网关", work, lambda ok: self._config_done(ok, "已恢复回退点。"))

    def _repair_codex(self, requires_auth):
        def work():
            was_running = codex_control.is_running()
            if was_running and not codex_control.stop():
                return False, "无法安全停止 Codex，未切换模式。"
            # The desktop app has now flushed its current sidebar/archive state.
            # Keep a safety snapshot, but do not overwrite the live state after
            # switching: provider changes never need to rewrite conversations.
            conversation_guard.capture_state("before-mode-switch")
            conversation_guard.synchronize_sidebar_indexes()
            restore_manager.create_restore_point("auto", "before-codex-mode-switch", "切换登录模式前自动保存")
            migration = None
            config_switched = False
            try:
                config_manager.expose_display_names_to_codex()
                credential_message = ""
                if requires_auth:
                    auth = account_info.get_account_info()
                    if not auth.get("gateway_logged_in") and IS_MACOS:
                        imported, import_message = gateway.import_desktop_codex_auth()
                        if imported:
                            auth = account_info.get_account_info()
                            credential_message = import_message
                    if not auth.get("gateway_logged_in"):
                        return False, (
                            "未找到可供本地网关使用的官方订阅凭据。"
                            "请先点击“登录/刷新网关官方订阅凭据”，完成后再切换。"
                        )
                gateway_ok = gateway.start()
                if not gateway_ok:
                    return False, "网关未能启动，未切换 Codex 配置。"
                migration = conversation_guard.migrate_desktop_conversations("cliproxyapi")
                ok, msg = codex_repair.repair_codex_config(requires_auth)
                if ok:
                    config_switched = True
                    restore_manager.create_restore_point("auto", "codex-mode-switch", "切换登录模式后自动保存")
                    if requires_auth:
                        suffix = " 已检测到可刷新官方凭据；实时额度、限流和模型可用性不影响模式切换。"
                        if credential_message:
                            suffix += " " + credential_message
                    else:
                        suffix = ""
                    return True, msg + " 网关已启动。已同步迁移 {} 条桌面会话。".format(migration["sessions_seen"]) + suffix
                if migration:
                    conversation_guard.restore_provider_snapshot(migration["snapshot"])
                gateway.stop()
                return False, msg
            except Exception:
                if migration and not config_switched:
                    conversation_guard.restore_provider_snapshot(migration["snapshot"])
                gateway.stop()
                raise
            finally:
                if was_running:
                    codex_control.start()
        self._run_task("正在切换 Codex 登录模式", work, self._mode_switch_done)

    def _switch_official_only(self):
        def work():
            was_running = codex_control.is_running()
            if was_running and not codex_control.stop():
                return False, "无法安全停止 Codex，未切换模式。"
            conversation_guard.capture_state("before-official-switch")
            conversation_guard.synchronize_sidebar_indexes()
            restore_manager.create_restore_point("auto", "before-official-only", "切换纯官方订阅前自动保存")
            migration = None
            config_switched = False
            try:
                migration = conversation_guard.migrate_desktop_conversations("openai")
                ok, msg = codex_repair.switch_to_official_only()
                if not ok:
                    conversation_guard.restore_provider_snapshot(migration["snapshot"])
                    return False, msg
                config_switched = True
                gateway.disable_autostart()
                stopped = gateway.stop()
                if ok and stopped:
                    restore_manager.create_restore_point("auto", "official-only", "切换纯官方订阅后自动保存")
                    return True, msg + " 网关已停止，自启已关闭。已同步迁移 {} 条桌面会话。".format(migration["sessions_seen"])
                return False, msg if not ok else "已写入官方模式，但网关未能停止。"
            except Exception:
                if migration and not config_switched:
                    conversation_guard.restore_provider_snapshot(migration["snapshot"])
                raise
            finally:
                if was_running:
                    codex_control.start()
        self._run_task("正在切换为纯官方订阅", work, self._mode_switch_done)

    def _snapshot_conversations(self):
        conversation_guard.snapshot("manual")
        self.refresh_settings()
        self._info("已创建会话索引快照。会话内容文件未被复制、移动或修改。")

    def _repair_conversation_index(self):
        if QMessageBox.question(
            self,
            "修复会话列表",
            "此操作会先完整记录会话首行元数据并备份 SQLite，然后把所有桌面会话统一到当前模式的 provider，同时修复侧栏索引。不会改动会话正文，失败会自动回滚。继续？",
        ) != QMessageBox.Yes:
            return
        def work():
            was_running = codex_control.is_running()
            if was_running and not codex_control.stop():
                raise RuntimeError("无法安全停止 ChatGPT/Codex，未修改会话。")
            try:
                mode = account_info.get_account_info()["mode_key"]
                target = "openai" if mode == "pure_official" else "cliproxyapi"
                migration = conversation_guard.migrate_desktop_conversations(target)
                index = conversation_guard.rebuild_visible_index()
                migration.update(index)
                return migration
            finally:
                if was_running:
                    codex_control.start()
        self._run_task("正在备份、统一并修复会话", work, self._conversation_repair_done)

    def _conversation_repair_done(self, result):
        self.refresh_settings()
        self._info(
            "已统一 {} 条桌面会话到 {}，其中修改会话文件 {} 条、数据库记录 {} 条；侧栏索引现有 {} 条。请重新打开 ChatGPT/Codex。".format(
                result["sessions_seen"], result["target_provider"], result["sessions_changed"],
                result["database_changed"], result["recovered"]
            )
        )

    def _codex_login(self):
        ok, message = gateway.run_codex_login()
        if ok:
            self.refresh_settings()
            self.refresh_status()
            self._info(message)
        else:
            self._error(message)

    def _start_gateway(self):
        return gateway.start()

    def _tray_restart_gateway(self):
        if account_info.get_account_info()["mode_key"] == "pure_official":
            self._warn("当前是纯官方订阅模式。请先在设置中切换到“官方订阅 + 第三方 API”或“纯 API + 第三方模型”。")
            return
        self._run_task("正在重启网关", self._restart_gateway, self._gateway_done)

    def _stop_gateway(self):
        return gateway.stop()

    def _restart_gateway(self):
        return gateway.restart()

    def _toggle_codex(self):
        return codex_control.stop() if codex_control.is_running() else codex_control.start()

    def _restart_codex(self):
        return codex_control.restart()

    def _apply_port(self):
        try:
            port = int(self.port_edit.text().strip())
            if port < 1 or port > 65535:
                raise ValueError()
        except ValueError:
            self._warn("端口必须是 1-65535。")
            return
        restore_manager.create_restore_point("auto", "before-port-change", "修改端口前自动保存")
        config_manager.set_port(port)
        self._run_task("正在应用端口并重启网关", self._restart_gateway, self._gateway_done)

    def _enable_autostart(self):
        self._info("已开启自启。" if gateway.enable_autostart() else "开启自启失败。")
        self.refresh_settings()

    def _disable_autostart(self):
        self._info("已关闭自启。" if gateway.disable_autostart() else "未找到自启任务。")
        self.refresh_settings()

    def _check_update(self):
        return check_update()

    def _run_task(self, title, fn, on_done=None):
        if self._busy_dialog is not None:
            self._warn("已有任务正在执行，请稍等一下。")
            return

        dialog = QProgressDialog(title + "…", None, 0, 0, self)
        dialog.setWindowTitle(APP_NAME)
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setValue(0)
        dialog.show()
        self._busy_dialog = dialog
        central = self.centralWidget()
        if central:
            central.setEnabled(False)

        signals = TaskSignals()
        self._task_signals.append(signals)

        def finish(result, error):
            try:
                if self._busy_dialog is dialog:
                    self._busy_dialog = None
                dialog.close()
                if central:
                    central.setEnabled(True)
                try:
                    self.refresh_status()
                except Exception:
                    pass
                if error is not None:
                    self._error(str(error))
                    return
                if on_done:
                    on_done(result)
            finally:
                if signals in self._task_signals:
                    self._task_signals.remove(signals)

        signals.finished.connect(finish)

        def worker():
            try:
                result = fn()
                signals.finished.emit(result, None)
            except Exception as ex:
                signals.finished.emit(None, ex)

        threading.Thread(target=worker, daemon=True).start()

    def _gateway_done(self, ok):
        self.refresh_all()
        if ok:
            self.tray.showMessage(APP_NAME, "网关操作完成。")
        else:
            self._error("网关操作失败，请检查端口是否被占用，或查看配置是否有效。")

    def _codex_done(self, ok):
        self.refresh_all()
        if not ok:
            self._error("Codex 操作失败：没有成功启动/停止 Codex。请确认 Codex Desktop 已安装。")

    def _config_done(self, ok, message):
        self.refresh_all()
        if ok:
            if account_info.get_account_info()["mode_key"] == "pure_official":
                message += " 当前是纯官方模式；切换到“官方订阅 + 第三方 API”或“纯 API + 第三方模型”后，Codex 才会显示这些模型。"
            self._info(message)
        else:
            self._error("操作已执行，但网关未正常响应。配置已保留，请检查端口、API 地址或模型配置。")

    def _mode_switch_done(self, result):
        self.refresh_all()
        ok, msg = result
        if ok:
            self._info(msg)
        else:
            self._error(msg)

    def _update_done(self, result):
        if result.get("error"):
            msg = (
                "检查更新失败，但程序不会再卡死。\n\n"
                "原因：{error}\n\n"
                "你也可以手动打开 Release 页面查看：\n{url}"
            ).format(error=result.get("error"), url=result.get("release_url", ""))
            self._warn(msg)
            return
        if result.get("has_update"):
            latest = result.get("latest_version") or "新版"
            current = result.get("current_version") or APP_VERSION
            if QMessageBox.question(
                self,
                "发现新版本",
                "当前版本：{current}\n最新版本：{latest}\n\n是否打开下载页面？".format(current=current, latest=latest),
            ) == QMessageBox.Yes:
                webbrowser.open(result.get("download_url") or result.get("release_url"))
        else:
            self._info("当前已是最新版本：{}".format(result.get("current_version") or APP_VERSION))

    def _info(self, text):
        QMessageBox.information(self, APP_NAME, text)

    def _warn(self, text):
        QMessageBox.warning(self, APP_NAME, text)

    def _error(self, text):
        QMessageBox.critical(self, APP_NAME, text)

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent):
        QSettings(APP_NAME, APP_NAME).setValue("mainWindowGeometry", self.saveGeometry())
        if self._allow_exit:
            event.accept()
            return
        event.ignore()
        self.hide()
        self.tray.showMessage(APP_NAME, "已最小化到菜单栏/系统托盘，网关继续运行。")

    def exit_app(self):
        self._allow_exit = True
        QApplication.instance().quit()


class ModelDialog(QDialog):
    def __init__(self, parent=None, entry=None):
        super().__init__(parent)
        self.result = None
        self.entry = entry or {}
        self.setWindowTitle("模型配置")
        self.resize(760, 400)
        self.setMinimumSize(720, 380)
        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.api_type = QComboBox()
        for label, value in (
            ("OpenAI Responses", "responses"),
            ("OpenAI 兼容", "openai"),
            ("Anthropic 兼容", "claude"),
        ):
            self.api_type.addItem(label, value)
        if self.entry:
            section_type = {"codex-api-key": "responses", "openai-compatibility": "openai", "claude-api-key": "claude"}
            target_type = section_type.get(self.entry.get("section"), "responses")
            self.api_type.setCurrentIndex(max(0, self.api_type.findData(target_type)))
            self.api_type.setEnabled(False)
        self.base_url = QLineEdit(self.entry.get("base_url", ""))
        self.api_key = QLineEdit(self.entry.get("api_key", ""))
        self.api_key.setEchoMode(QLineEdit.Password)
        self.model_id = QComboBox()
        self.model_id.setEditable(True)
        self.model_id.setEditText(self.entry.get("upstream", ""))
        self.name = QLineEdit(self.entry.get("display_name", self.entry.get("alias", "")))
        self.provider_name = QLineEdit(self.entry.get("provider_name", ""))
        self.ctx = QLineEdit(str(self.entry.get("context_window") or ""))
        self.maxout = QLineEdit(str(self.entry.get("max_output_tokens") or ""))
        form.addRow("接口类型", self.api_type)
        form.addRow("API Base URL", self.base_url)
        key_row = QHBoxLayout()
        key_row.addWidget(self.api_key, 1)
        self.key_toggle = QToolButton()
        self.key_toggle.setIcon(eye_icon(False))
        self.key_toggle.setToolTip("显示 API Key")
        self.key_toggle.setCheckable(True)
        self.key_toggle.toggled.connect(self._toggle_key)
        key_row.addWidget(self.key_toggle)
        form.addRow("API Key", key_row)
        row = QHBoxLayout()
        row.addWidget(self.model_id, 1)
        fetch = QPushButton("获取模型列表")
        fetch.clicked.connect(self._fetch_models)
        row.addWidget(fetch)
        form.addRow("上游模型 ID", row)
        form.addRow("名称", self.name)
        form.addRow("供应商名称", self.provider_name)
        form.addRow("上下文 token", self.ctx)
        form.addRow("最大输出 token", self.maxout)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _toggle_key(self, visible):
        self.api_key.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        self.key_toggle.setIcon(eye_icon(visible))
        self.key_toggle.setToolTip("隐藏 API Key" if visible else "显示 API Key")

    def _model_list_candidates(self, base, api_type):
        from urllib.parse import urlparse
        candidates = [base + "/models"]
        host = (urlparse(base).hostname or "").lower()
        # 火山方舟: plan/coding 等专用接口没有 /models 列表, 统一回退到 /api/v3/models
        if host == "ark.cn-beijing.volces.com":
            candidates.append("https://ark.cn-beijing.volces.com/api/v3/models")
        # Anthropic 官方: 用 x-api-key, 列表地址固定
        if api_type == "claude" and "anthropic.com" in host:
            candidates.append("https://api.anthropic.com/v1/models")
        seen, out = set(), []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def _fetch_models(self):
        base = self.base_url.text().strip().rstrip("/")
        key = self.api_key.text().strip()
        if not base or not key:
            QMessageBox.warning(self, "提示", "请先填写 URL 和 API Key。")
            return
        api_type = self.api_type.currentData()
        headers = {"User-Agent": APP_NAME}
        if api_type == "claude":
            headers["x-api-key"] = key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = "Bearer " + key
        last_error = None
        ids = []
        for url in self._model_list_candidates(base, api_type):
            try:
                req = urllib.request.Request(url, headers=headers)
                data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
                found = [str(x.get("id") or x.get("name")) for x in data.get("data", []) if isinstance(x, dict) and (x.get("id") or x.get("name"))]
                if found:
                    ids = sorted(set(found))
                    break
            except Exception as ex:
                last_error = ex
                continue
        if ids:
            self.model_id.clear()
            self.model_id.addItems(ids)
        else:
            QMessageBox.warning(self, "获取失败", "该接口未返回模型列表，可手动填写模型 ID。\n\n" + (str(last_error) if last_error else ""))

    def _int_or_none(self, text):
        text = text.strip()
        return int(text) if text.isdigit() else None

    def _ok(self):
        model_id = self.model_id.currentText().strip()
        name = self.name.text().strip() or model_id
        if not self.entry and (not self.base_url.text().strip() or not self.api_key.text().strip() or not model_id):
            QMessageBox.warning(self, "提示", "URL、Key、模型 ID 不能为空。")
            return
        if self.entry:
            self.result = {
                "base_url": self.base_url.text().strip(),
                "api_key": self.api_key.text().strip() or None,
                "upstream": model_id,
                "alias": name,
                "display_name": name,
                "provider_name": self.provider_name.text().strip() or "Custom",
                "context_window": self._int_or_none(self.ctx.text()),
                "max_output_tokens": self._int_or_none(self.maxout.text()),
            }
        else:
            self.result = {
                "api_type": self.api_type.currentData(),
                "provider_name": self.provider_name.text().strip() or "Custom",
                "base_url": self.base_url.text().strip(),
                "api_key": self.api_key.text().strip(),
                "model_id": model_id,
                "alias": name,
                "display_name": name,
                "context_window": self._int_or_none(self.ctx.text()),
                "max_output_tokens": self._int_or_none(self.maxout.text()),
            }
        self.accept()


class TextDialog(QDialog):
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 620)
        layout = QVBoxLayout(self)
        editor = QPlainTextEdit()
        editor.setPlainText(text)
        editor.setReadOnly(True)
        layout.addWidget(editor)


def _takeover_if_needed():
    if not gateway.is_running() or gateway.is_managed_running():
        runtime.ensure_all()
        return True
    info = gateway.get_process_info() or {}
    msg = (
        "检测到已有 CLIProxyAPI 正在运行，但不是当前软件托管的实例。\n\n"
        "进程: {pid}\n路径: {path}\n\n"
        "请选择“接管”，软件会停止当前命令行版本，继承现有配置并改由本软件托管；"
        "如果不同意，软件将退出。"
    ).format(pid=info.get("pid", "-"), path=info.get("path", "-"))
    box = QMessageBox()
    box.setWindowIcon(app_icon())
    box.setWindowTitle("接管 CLIProxyAPI")
    box.setText(msg)
    takeover = box.addButton("接管并继承配置", QMessageBox.AcceptRole)
    box.addButton("退出软件", QMessageBox.RejectRole)
    box.exec()
    if box.clickedButton() != takeover:
        return False
    restore_manager.create_restore_point("auto", "before-takeover", "接管外部 CLIProxyAPI 前自动保存")
    before = account_info.get_account_info()
    requires_auth = before.get("mode_key") != "api_only" and before.get("logged_in")
    config_manager.merge_external_config(gateway.running_config_path())
    gateway.stop()
    runtime.ensure_all()
    runtime.update_cli_proxy_runtime_if_possible()
    codex_repair.repair_codex_config(bool(requires_auth))
    gateway.start()
    restore_manager.create_restore_point("auto", "after-takeover", "接管外部 CLIProxyAPI 后自动保存")
    return True


def run():
    app = QApplication([])
    if IS_MACOS and "macOS" in QStyleFactory.keys():
        app.setStyle(QStyleFactory.create("macOS"))
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())
    app.setStyleSheet(MACOS_QSS if IS_MACOS else (DARK_QSS if system_dark_mode() else LIGHT_QSS))
    if not _takeover_if_needed():
        return
    w = MainWindow()
    w.show()
    app.exec()
