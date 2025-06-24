# src/evocode_gui/widgets.py
# -*- coding: utf-8 -*-
"""
Содержит кастомные, стилизованные виджеты для GUI приложения EvoCode.
"""
from typing import Optional

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QDialog, QVBoxLayout, QFrame
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, QPointF
from PyQt6.QtGui import QColor, QMouseEvent
import qtawesome as qta
from .styles import PALETTE

class AnimatedButton(QPushButton):
    """Кнопка с плавной анимацией цвета фона при наведении."""
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, parent)
        if icon:
            self.setIcon(icon)

        # Сохраняем базовый стиль в отдельном атрибуте
        self._base_style = f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {PALETTE['border_color']};
                text-align: center;
                padding: 10px;
                border-radius: 5px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {PALETTE['text_muted']};
            }}
        """
        self.setStyleSheet(self._base_style)
        
        # 1. СНАЧАЛА создаем атрибут, который будет анимироваться.
        self._background_color = QColor("transparent")
        
        # 2. ТОЛЬКО ПОТОМ создаем анимацию, которая его использует.
        self._animation = QPropertyAnimation(self, b"backgroundColor")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        self.hover_color = QColor(PALETTE['glass_border'])

    def enterEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._animation.setEndValue(self.hover_color)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._animation.setEndValue(QColor("transparent"))
        self._animation.start()
        super().leaveEvent(event)
    
    @pyqtProperty(QColor)
    def backgroundColor(self) -> QColor:
        return self._background_color

    @backgroundColor.setter
    def backgroundColor(self, color: QColor):
        self._background_color = color
        # Формируем новую, валидную таблицу стилей, не накапливая стили
        current_stylesheet = self._base_style + f" QPushButton {{ background-color: {color.name(QColor.NameFormat.HexArgb)}; }}"
        self.setStyleSheet(current_stylesheet)


class ValueSelector(QWidget):
    """
    Кастомный, стилизованный виджет для выбора числового значения.
    """
    valueChanged = pyqtSignal(int)

    def __init__(self, min_val: int = 1, max_val: int = 100, initial_val: int = 1):
        super().__init__()
        self.setObjectName("ValueSelector")
        self.min_val = min_val
        self.max_val = max_val
        self._value = initial_val
        self._setup_ui()
        self._update_label()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        self.minus_button = QPushButton(qta.icon('fa5s.minus', color=PALETTE['text_muted']), "")
        self.minus_button.setObjectName("ValueSelectorButton")
        self.minus_button.setIconSize(QSize(10, 10))
        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumWidth(35)
        self.value_label.setObjectName("ValueSelectorLabel")
        self.plus_button = QPushButton(qta.icon('fa5s.plus', color=PALETTE['text_muted']), "")
        self.plus_button.setObjectName("ValueSelectorButton")
        self.plus_button.setIconSize(QSize(10, 10))
        layout.addWidget(self.minus_button)
        layout.addWidget(self.value_label, 1)
        layout.addWidget(self.plus_button)
        self.minus_button.clicked.connect(self._decrement)
        self.plus_button.clicked.connect(self._increment)
    
    def _update_label(self):
        self.value_label.setText(str(self._value))

    def _decrement(self):
        if self._value > self.min_val:
            self._value -= 1
            self._update_label()
            self.valueChanged.emit(self._value)

    def _increment(self):
        if self._value < self.max_val:
            self._value += 1
            self._update_label()
            self.valueChanged.emit(self._value)

    def value(self) -> int:
        return self._value


class CustomMessageBox(QDialog):
    """Кастомное, стилизованное диалоговое окно."""
    def __init__(self, title: str, message: str, icon_name: str, icon_color: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setObjectName("MessageBox")
        
        self.drag_position: Optional[QPointF] = None
        self._setup_ui(title, message, icon_name, icon_color)

    def _setup_ui(self, title, message, icon_name, icon_color):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        
        container = QFrame()
        container.setObjectName("MessageBoxContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 10, 20, 20)
        container_layout.setSpacing(15)

        title_bar_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("MessageBoxTitle")
        close_button = QPushButton(qta.icon('fa5s.times', color=PALETTE['text_muted']), "")
        close_button.setObjectName("MessageBoxCloseButton")
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self.reject)
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(close_button)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(QSize(48, 48)))
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        content_layout.addWidget(icon_label)
        content_layout.addWidget(message_label, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("OK")
        ok_button.setObjectName("MessageBoxOKButton")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)

        container_layout.addLayout(title_bar_layout)
        container_layout.addLayout(content_layout)
        container_layout.addLayout(button_layout)
        
        layout.addWidget(container)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition() - QPointF(self.frameGeometry().topLeft())
            event.accept()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move((event.globalPosition() - self.drag_position).toPoint())
            event.accept()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        self.drag_position = None
        event.accept()