# src/evocode_gui/main_window.py
# -*- coding: utf-8 -*-
"""
Определяет главный класс QMainWindow для графического интерфейса EvoCode.
"""
from pathlib import Path
from typing import Dict, Any, Optional

import markdown
import qtawesome as qta
from PyQt6.QtCore import QThread, Qt, QSize, QRect, pyqtSlot, QModelIndex
from PyQt6.QtGui import QMouseEvent, QResizeEvent, QBitmap, QPainter, QColor, QStandardItemModel, QStandardItem, QFontMetrics
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox, QFormLayout,
    QProgressBar, QFrame, QSplitter, QTreeView,
    QAbstractItemView, QTextEdit, QStyleFactory, QPlainTextEdit
)

from .worker import Worker, ScanTask, EvoTask
from evocode_core import ImprovementIdea, ImplementationPlan
from .styles import MODERN_STYLE_SHEET, PALETTE
from .title_bar import TitleBar
from .neural_background import NeuralBackgroundWidget
from .widgets import ValueSelector, AnimatedButton, CustomMessageBox

class MainWindow(QMainWindow):
    """Главное окно приложения EvoCode с кастомным дизайном."""

    def __init__(self, prompts: Dict[str, Any]):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.prompts = prompts
        self.thread: Optional[QThread] = None
        self.worker: Optional[Worker] = None
        self.scanner_worker: Optional[Worker] = None
        self.project_path: Optional[Path] = None

        self._setup_ui()
        self._create_connections()
        self.background.start_animation()

    def _setup_ui(self):
        self.setWindowTitle("EvoCode AI")
        self.setMinimumSize(1100, 750)
        self.resize(1200, 800)
        self.setStyleSheet(MODERN_STYLE_SHEET)
        
        main_container = QWidget()
        self.setCentralWidget(main_container)
        
        self.background = NeuralBackgroundWidget(main_container)
        self.overlay_widget = QWidget(main_container)
        
        main_layout = QVBoxLayout(self.overlay_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        main_layout.addWidget(self.title_bar)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(15, 10, 15, 15)
        body_layout.setSpacing(15)
        
        sidebar = self._create_sidebar_panel()
        content_pane = self._create_content_panel()
        
        body_layout.addWidget(sidebar)
        body_layout.addWidget(content_pane, 1)

        main_layout.addLayout(body_layout, 1)

    def _create_sidebar_panel(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("EvoCode")
        header.setObjectName("Header")
        layout.addWidget(header)
        layout.addSpacing(20)
        
        layout.addWidget(QLabel("Проект", objectName="SubHeader"))
        self.select_dir_button = AnimatedButton(
            "Выбрать директорию",
            qta.icon('fa5s.folder-open', color=PALETTE['text_muted'])
        )
        self.path_label = QLabel("Не выбран")
        self.path_label.setObjectName("PathLabel")
        self.path_label.setWordWrap(False)
        layout.addWidget(self.select_dir_button)
        layout.addWidget(self.path_label)
        layout.addSpacing(20)
        
        layout.addWidget(QLabel("Настройки", objectName="SubHeader"))
        settings_form = QFormLayout()
        settings_form.setSpacing(100)
        self.cycles_selector = ValueSelector()
        self.cycles_selector.setFixedWidth(100)
        settings_form.addRow("Циклы:", self.cycles_selector)
        layout.addLayout(settings_form)

        layout.addStretch()

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setObjectName("CancelButton")
        self.cancel_button.setEnabled(False)
        self.run_button = QPushButton("Запустить")
        self.run_button.setObjectName("RunButton")
        
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.run_button)
        return sidebar

    def _create_content_panel(self) -> QWidget:
        content_pane = QWidget()
        content_pane.setObjectName("ContentPane")
        layout = QVBoxLayout(content_pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        status_header_layout = QHBoxLayout()
        self.status_icon = QLabel()
        status_header_layout.addWidget(self.status_icon)
        status_header_layout.addWidget(QLabel("Статус выполнения", objectName="SubHeader"))
        status_header_layout.addStretch()
        self.status_label = QLabel("Готово")
        self.status_label.setObjectName("MutedLabel")
        status_header_layout.addWidget(self.status_label)
        layout.addLayout(status_header_layout)
        
        task_card = QFrame()
        task_card.setObjectName("TaskCard")
        task_layout = QVBoxLayout(task_card)
        task_layout.setSpacing(10)
        self.idea_title_label = QLabel("Ожидание запуска...")
        self.idea_title_label.setObjectName("IdeaLabel")
        self.idea_title_label.setWordWrap(True)
        self.plan_text_edit = QTextEdit()
        self.plan_text_edit.setObjectName("PlanTextEdit")
        self.plan_text_edit.setReadOnly(True)
        self.plan_text_edit.setMinimumHeight(100)
        task_layout.addWidget(self.idea_title_label)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet(f"border-color: {PALETTE['border_color']};")
        task_layout.addWidget(line)
        task_layout.addWidget(self.plan_text_edit)
        layout.addWidget(task_card)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(5)
        
        file_tree_container = QWidget()
        file_tree_container.setObjectName("FileTreeContainer")
        file_tree_layout = QVBoxLayout(file_tree_container)
        file_tree_layout.setContentsMargins(15, 15, 15, 15)
        file_tree_layout.setSpacing(10)
        file_tree_layout.addWidget(QLabel("Структура проекта", objectName="SubHeader"))
        
        self.file_tree = QTreeView()
        self.file_tree.setObjectName("FileTree")
        self.file_tree.setIndentation(15)
        self.file_tree.setAnimated(True)
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.file_tree_model = QStandardItemModel()
        self.file_tree.setModel(self.file_tree_model)
        self.file_tree_path_map = {}
        
        file_tree_layout.addWidget(self.file_tree)
        
        log_container = QWidget()
        log_container.setObjectName("LogContainer")
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(15, 15, 15, 15)
        log_layout.setSpacing(10)
        log_layout.addWidget(QLabel("Детальный лог", objectName="SubHeader"))
        
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)

        splitter.addWidget(file_tree_container)
        splitter.addWidget(log_container)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        return content_pane
    
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.overlay_widget.setGeometry(self.rect())
        self.background.setGeometry(self.rect())
        
        mask = QBitmap(self.size())
        mask.fill(Qt.GlobalColor.white)
        painter = QPainter(mask)
        painter.setBrush(Qt.GlobalColor.black)
        painter.drawRoundedRect(self.rect(), 12, 12)
        painter.end()
        self.setMask(mask)

    def mouseMoveEvent(self, event: QMouseEvent):
        super().mouseMoveEvent(event)
        if hasattr(self, 'background') and self.background:
            self.background.update_mouse_position(event.pos())
            
    def _create_connections(self):
        self.select_dir_button.clicked.connect(self.select_project_directory)
        self.run_button.clicked.connect(self.start_processing)
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.file_tree.expanded.connect(self._on_item_expanded)
        self.file_tree.collapsed.connect(self._on_item_collapsed)
        
    def _populate_file_tree(self, structure: Dict[str, Any]):
        """
        Рекурсивно заполняет QTreeView на основе готовой структуры данных (словаря).
        """
        self.file_tree_model.clear()
        self.file_tree_path_map.clear()
        
        def add_items(parent_item, data_dict, current_path):
            # ИСПРАВЛЕНИЕ: Итерируемся по словарю, а не по пути
            sorted_items = sorted(data_dict.items(), key=lambda x: (not isinstance(x[1], dict), x[0].lower()))
            
            for name, content in sorted_items:
                item = QStandardItem(name)
                item.setEditable(False)
                
                new_path = f"{current_path}/{name}" if current_path else name
                self.file_tree_path_map[new_path] = item
                
                if isinstance(content, dict):
                    item.setIcon(qta.icon('fa5s.folder', color=PALETTE['text_muted']))
                    parent_item.appendRow(item)
                    add_items(item, content, new_path)
                else:
                    item.setIcon(qta.icon('fa5s.file-alt', color=PALETTE['text_secondary']))
                    parent_item.appendRow(item)
        
        root_item = self.file_tree_model.invisibleRootItem()
        add_items(root_item, structure, "")
        self.file_tree.expandToDepth(0)

    @pyqtSlot(QModelIndex)
    def _on_item_expanded(self, index: QModelIndex):
        item = self.file_tree_model.itemFromIndex(index)
        if item:
            item.setIcon(qta.icon('fa5s.folder-open', color=PALETTE['text_muted']))

    @pyqtSlot(QModelIndex)
    def _on_item_collapsed(self, index: QModelIndex):
        item = self.file_tree_model.itemFromIndex(index)
        if item:
            item.setIcon(qta.icon('fa5s.folder', color=PALETTE['text_muted']))

    @pyqtSlot(str)
    def _highlight_active_file(self, file_path_str: str):
        if file_path_str in self.file_tree_path_map:
            item = self.file_tree_path_map[file_path_str]
            index = self.file_tree_model.indexFromItem(item)
            if index.isValid():
                self.file_tree.setCurrentIndex(index)
                self.file_tree.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)

    def select_project_directory(self):
        path_str = QFileDialog.getExistingDirectory(self, "Выберите директорию проекта")
        if path_str:
            self.project_path = Path(path_str)
            self.path_label.setText("Сканирование...")
            self.path_label.setToolTip(str(self.project_path))
            
            self.thread = QThread()
            scan_task = ScanTask(self.project_path)
            self.scanner_worker = Worker(scan_task)
            self.scanner_worker.moveToThread(self.thread)
            
            self.scanner_worker.scan_finished.connect(self._on_scan_finished)
            self.scanner_worker.error.connect(self.on_processing_error)
            
            self.thread.started.connect(self.scanner_worker.run)
            self.thread.start()

    @pyqtSlot(dict)
    def _on_scan_finished(self, structure: Dict[str, Any]):
        if not self.project_path: return

        full_path_str = str(self.project_path)
        metrics = QFontMetrics(self.path_label.font())
        elided_text = metrics.elidedText(full_path_str, Qt.TextElideMode.ElideMiddle, self.path_label.width())
        self.path_label.setText(elided_text)
        
        self._populate_file_tree(structure)
        
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    def start_processing(self):
        if not self.project_path:
            msg_box = CustomMessageBox("Проект не выбран", "Пожалуйста, выберите директорию проекта.", 'fa5s.exclamation-triangle', PALETTE['accent_danger'], parent=self)
            msg_box.exec()
            return

        self._set_ui_enabled(False)
        self._clear_task_info()
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.status_icon.setPixmap(qta.icon('fa5s.hourglass-half', color=PALETTE['text_muted']).pixmap(QSize(16, 16)))
        
        self.thread = QThread()
        evo_task = EvoTask(self.project_path, self.cycles_selector.value(), self.prompts)
        self.worker = Worker(evo_task)
        self.worker.moveToThread(self.thread)
        
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error.connect(self.on_processing_error)
        self.worker.stage_changed.connect(self.update_log_and_status)
        self.worker.idea_approved.connect(self.display_idea)
        self.worker.plan_approved.connect(self.display_plan)
        self.worker.file_activity_changed.connect(self._highlight_active_file)
        
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def cancel_processing(self):
        if self.worker:
            self.status_label.setText("Отмена операции...")
            self.cancel_button.setEnabled(False)
            self.worker.cancel()

    def on_processing_finished(self):
        status_msg = "Операция отменена" if self.worker and self.worker._is_cancelled else "Готово"
        self.status_label.setText(status_msg)
        if status_msg == "Готово":
            self.status_icon.setPixmap(qta.icon('fa5s.check-circle', color=PALETTE['accent_success']).pixmap(QSize(16, 16)))
            if self.progress_bar.value() > 0: self.progress_bar.setValue(100)
        else:
             self.status_icon.setPixmap(qta.icon('fa5s.times-circle', color=PALETTE['accent_danger']).pixmap(QSize(16, 16)))
        self._set_ui_enabled(True)
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        self.thread = None
        self.worker = None

    def on_processing_error(self, title: str, message: str):
        msg_box = CustomMessageBox(title, message, 'fa5s.bomb', PALETTE['accent_danger'], parent=self)
        msg_box.exec()
        self.on_processing_finished()

    def update_log_and_status(self, text: str):
        clean_text = text.strip()
        if not clean_text: return
        self.log_output.appendPlainText(clean_text)
        self.status_label.setText(clean_text)
        progress_map = { "Генерация идей": 10, "Фильтрация": 20, "Создание плана": 30, "Запуск агента-кодера": 45, "Запуск агента-тестировщика": 75, "Запуск QA-агента": 90, "Контроль качества пройден": 100 }
        for key, value in progress_map.items():
            if key in clean_text:
                self.progress_bar.setValue(value)
                break

    def display_idea(self, idea: ImprovementIdea):
        clean_title = idea.title.replace("`", "").replace("*", "")
        self.idea_title_label.setText(clean_title)
        self.idea_title_label.setToolTip(f"Приоритет: {idea.priority}\nОписание: {idea.description}")

    def display_plan(self, plan: ImplementationPlan):
        html_plan = markdown.markdown(plan.description)
        styled_html = f"""
        <style>
            body {{ color: {PALETTE['text_secondary']}; font-family: 'Inter', 'Segoe UI'; font-size: 10pt; }}
            strong {{ color: {PALETTE['text_primary']}; }}
            code {{ background-color: {PALETTE['bg_widget']}; border-radius: 3px; padding: 2px 4px; }}
            ul {{ padding-left: 20px; }}
        </style>
        {html_plan}
        """
        self.plan_text_edit.setHtml(styled_html)
        
    def _clear_task_info(self):
        self.idea_title_label.setText("Ожидание новой идеи...")
        self.plan_text_edit.setHtml("")

    def _set_ui_enabled(self, enabled: bool):
        self.run_button.setEnabled(enabled)
        self.select_dir_button.setEnabled(enabled)
        self.cycles_selector.setEnabled(enabled)
        self.cancel_button.setEnabled(not enabled)

    def closeEvent(self, event):
        if hasattr(self, 'background'):
            self.background.stop_animation()
        if self.thread and self.thread.isRunning():
            self.cancel_processing()
            self.thread.quit()
            self.thread.wait()
        event.accept()