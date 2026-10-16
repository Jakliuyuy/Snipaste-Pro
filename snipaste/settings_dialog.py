from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QCheckBox, QComboBox, QSpinBox,
    QPushButton, QFileDialog, QColorDialog, QFormLayout, QGroupBox
)
from snipaste.config import get_config

class SettingsDialog(QDialog):
    """
    Preferences Dialog (Recreation of Snipaste OptionsDialog + Translation Settings).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Snipaste 首选项与设置")
        self.resize(540, 480)
        self.config = get_config()
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._create_general_tab(), "常规")
        self.tab_widget.addTab(self._create_snip_tab(), "截图")
        self.tab_widget.addTab(self._create_paste_tab(), "贴图")
        self.tab_widget.addTab(self._create_hotkey_tab(), "快捷键")
        self.tab_widget.addTab(self._create_translation_tab(), "🌐 截图实时翻译")
        main_layout.addWidget(self.tab_widget)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_save = QPushButton("保存设置")
        btn_save.setStyleSheet("background-color: #1E90FF; color: white; padding: 6px 16px; border-radius: 4px;")
        btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        main_layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self.chk_sound = QCheckBox("播放音效 (截图与气泡提示音)")
        self.chk_sound.setChecked(self.config.get_bool("General", "play_sound", True))
        layout.addRow("音效设置:", self.chk_sound)

        # Save Dir
        dir_layout = QHBoxLayout()
        self.edit_save_dir = QLineEdit(self.config.get("General", "save_dir", ""))
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._browse_save_dir)
        dir_layout.addWidget(self.edit_save_dir)
        dir_layout.addWidget(btn_browse)
        layout.addRow("截图保存目录:", dir_layout)

        # Theme Color
        self.btn_theme_color = QPushButton()
        self.theme_color = self.config.get("General", "theme_color", "#1E90FF")
        self._update_color_btn(self.btn_theme_color, self.theme_color)
        self.btn_theme_color.clicked.connect(self._pick_theme_color)
        layout.addRow("主题强调色:", self.btn_theme_color)

        return widget

    def _create_snip_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self.chk_detect_win = QCheckBox("自动探测窗口及界面元素 (智能吸附)")
        self.chk_detect_win.setChecked(self.config.get_bool("Snip", "auto_detect_windows", True))
        layout.addRow("窗口嗅探:", self.chk_detect_win)

        self.chk_magnifier = QCheckBox("显示像素级放大镜与取色 HUD")
        self.chk_magnifier.setChecked(self.config.get_bool("Snip", "show_magnifier", True))
        layout.addRow("放大取色:", self.chk_magnifier)

        self.combo_color_fmt = QComboBox()
        self.combo_color_fmt.addItems(["HEX", "RGB", "HSL"])
        self.combo_color_fmt.setCurrentText(self.config.get("Snip", "color_format", "HEX"))
        layout.addRow("默认颜色格式:", self.combo_color_fmt)

        self.spin_border_w = QSpinBox()
        self.spin_border_w.setRange(1, 8)
        self.spin_border_w.setValue(self.config.get_int("Snip", "border_width", 2))
        layout.addRow("截屏边框宽度:", self.spin_border_w)

        return widget

    def _create_paste_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self.chk_magnetic = QCheckBox("开启贴图磁力吸附 (自动吸附屏幕边界与其他贴图)")
        self.chk_magnetic.setChecked(self.config.get_bool("Paste", "magnetic_snap", True))
        layout.addRow("磁力吸附:", self.chk_magnetic)

        self.spin_snap_dist = QSpinBox()
        self.spin_snap_dist.setRange(4, 30)
        self.spin_snap_dist.setValue(self.config.get_int("Paste", "magnetic_distance", 12))
        layout.addRow("吸附阈值 (px):", self.spin_snap_dist)

        self.spin_history = QSpinBox()
        self.spin_history.setRange(5, 50)
        self.spin_history.setValue(self.config.get_int("Paste", "max_history", 20))
        layout.addRow("最大历史贴图保留数:", self.spin_history)

        return widget

    def _create_hotkey_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self.lbl_hk_snip = QLabel("F1 (截屏)")
        self.lbl_hk_paste = QLabel("F3 (贴图)")
        self.lbl_hk_clickthru = QLabel("F4 (取消/切换鼠标穿透)")
        self.lbl_hk_snipcopy = QLabel("Ctrl + F1 (截屏并立即复制)")
        self.lbl_hk_trans = QLabel("T (选区实时翻译)")

        layout.addRow("截屏快捷键:", self.lbl_hk_snip)
        layout.addRow("贴图快捷键:", self.lbl_hk_paste)
        layout.addRow("鼠标穿透快捷键:", self.lbl_hk_clickthru)
        layout.addRow("一键截屏并复制:", self.lbl_hk_snipcopy)
        layout.addRow("选区实时翻译:", self.lbl_hk_trans)

        hint = QLabel("💡 提示: 全局热键随系统常驻运行，支持在任意应用程序窗口中使用。")
        hint.setStyleSheet("color: #888; font-size: 11px; margin-top: 15px;")
        layout.addRow(hint)

        return widget

    def _create_translation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self.combo_trans_engine = QComboBox()
        self.combo_trans_engine.addItems(["google_free (免配置极速网络翻译)", "openai_compatible (自定义大模型/DeepSeek)"])
        cur_engine = self.config.get("Translation", "engine", "google_free")
        self.combo_trans_engine.setCurrentIndex(1 if cur_engine == "openai_compatible" else 0)
        layout.addRow("翻译引擎后端:", self.combo_trans_engine)

        self.combo_target_lang = QComboBox()
        self.combo_target_lang.addItems(["zh-CN (简体中文)", "en (英语)", "ja (日语)", "ko (韩语)", "fr (法语)", "de (德语)", "ru (俄语)"])
        self.combo_target_lang.setCurrentText(self.config.get("Translation", "target_lang", "zh-CN (简体中文)"))
        layout.addRow("默认目标语言:", self.combo_target_lang)

        # LLM Settings Group
        llm_group = QGroupBox("自定义大模型 / DeepSeek 配置 (可选)")
        llm_layout = QFormLayout(llm_group)

        self.edit_api_key = QLineEdit(self.config.get("Translation", "api_key", ""))
        self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        llm_layout.addRow("API Key:", self.edit_api_key)

        self.edit_api_base = QLineEdit(self.config.get("Translation", "api_base", "https://api.openai.com/v1"))
        llm_layout.addRow("API Base URL:", self.edit_api_base)

        self.edit_model = QLineEdit(self.config.get("Translation", "model", "gpt-4o-mini"))
        llm_layout.addRow("模型名称:", self.edit_model)

        layout.addRow(llm_group)
        return widget

    def _browse_save_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择截图保存目录", self.edit_save_dir.text())
        if d:
            self.edit_save_dir.setText(d)

    def _pick_theme_color(self):
        c = QColorDialog.getColor(QColor(self.theme_color), self, "选择主题颜色")
        if c.isValid():
            self.theme_color = c.name()
            self._update_color_btn(self.btn_theme_color, self.theme_color)

    def _update_color_btn(self, btn: QPushButton, hex_c: str):
        btn.setStyleSheet(f"background-color: {hex_c}; min-height: 22px; border-radius: 4px; border: 1px solid #777;")

    def _save_settings(self):
        # General
        self.config.set("General", "play_sound", str(self.chk_sound.isChecked()))
        self.config.set("General", "save_dir", self.edit_save_dir.text())
        self.config.set("General", "theme_color", self.theme_color)

        # Snip
        self.config.set("Snip", "auto_detect_windows", str(self.chk_detect_win.isChecked()))
        self.config.set("Snip", "show_magnifier", str(self.chk_magnifier.isChecked()))
        self.config.set("Snip", "color_format", self.combo_color_fmt.currentText())
        self.config.set("Snip", "border_width", str(self.spin_border_w.value()))

        # Paste
        self.config.set("Paste", "magnetic_snap", str(self.chk_magnetic.isChecked()))
        self.config.set("Paste", "magnetic_distance", str(self.spin_snap_dist.value()))
        self.config.set("Paste", "max_history", str(self.spin_history.value()))

        # Translation
        engine = "openai_compatible" if self.combo_trans_engine.currentIndex() == 1 else "google_free"
        self.config.set("Translation", "engine", engine)
        target_lang = self.combo_target_lang.currentText().split(" ")[0]
        self.config.set("Translation", "target_lang", target_lang)
        self.config.set("Translation", "api_key", self.edit_api_key.text().strip())
        self.config.set("Translation", "api_base", self.edit_api_base.text().strip())
        self.config.set("Translation", "model", self.edit_model.text().strip())

        self.accept()
