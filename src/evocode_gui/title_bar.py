# src/evocode_gui/title_bar.py
"""
Кастомный, полностью стилизованный и управляемый TitleBar для приложения,
обеспечивающий перемещение безрамочного окна и кастомные кнопки управления.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen

class TitleBarButton(QWidget):
    """Кастомная кнопка для TitleBar."""
    clicked = pyqtSignal()

    _BG_COLOR = QColor(0, 0, 0, 0) # Прозрачный фон
    _SYMBOL_COLOR = QColor(148, 155, 164)
    _HOVER_BG_COLOR = QColor(71, 75, 82)
    _HOVER_SYMBOL_COLOR = QColor(224, 226, 228)
    _DANGER_HOVER_BG_COLOR = QColor(237, 66, 69, 150)

    def __init__(self, symbol: str, is_danger: bool = False, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.is_danger = is_danger
        self.setFixedSize(46, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_hovered = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.is_hovered:
            bg_color = self._DANGER_HOVER_BG_COLOR if self.is_danger else self._HOVER_BG_COLOR
            symbol_color = self._HOVER_SYMBOL_COLOR
            painter.setBrush(bg_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self.rect())
        else:
            symbol_color = self._SYMBOL_COLOR
        
        pen = QPen(symbol_color)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        symbol_rect = self.rect().adjusted(18, 11, -18, -11) # Центрируем область 10x10

        if self.symbol == "□":
            pen.setWidthF(1.2)
            painter.setPen(pen)
            painter.drawRect(symbol_rect)
        elif self.symbol == "—":
            pen.setWidthF(1.5)
            painter.setPen(pen)
            center_y = symbol_rect.center().y()
            painter.drawLine(QPointF(symbol_rect.left(), center_y), QPointF(symbol_rect.right(), center_y))
        elif self.symbol == "✕":
            pen.setWidthF(1.5)
            painter.setPen(pen)
            cross_rect = symbol_rect.adjusted(1, 1, -1, -1)
            painter.drawLine(cross_rect.topLeft(), cross_rect.bottomRight())
            painter.drawLine(cross_rect.topRight(), cross_rect.bottomLeft())

    def enterEvent(self, event): self.is_hovered = True; self.update()
    def leaveEvent(self, event): self.is_hovered = False; self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        super().mousePressEvent(event)

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.drag_position = None
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("TitleBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        title_label = QLabel("EvoCode AI")
        title_label.setStyleSheet("color: #b9bbbe; padding-left: 15px; font-weight: 500;")
        
        layout.addSpacing(5)
        layout.addWidget(title_label)
        layout.addStretch()
        
        self._create_and_connect_buttons(layout)

    def _create_and_connect_buttons(self, layout: QHBoxLayout):
        minimize_button = TitleBarButton("—")
        maximize_button = TitleBarButton("□")
        close_button = TitleBarButton("✕", is_danger=True)

        minimize_button.clicked.connect(self.window().showMinimized)
        maximize_button.clicked.connect(self.toggle_maximize)
        close_button.clicked.connect(self.window().close)
        
        layout.addWidget(minimize_button)
        layout.addWidget(maximize_button)
        layout.addWidget(close_button)

    def toggle_maximize(self):
        win = self.window()
        if win.isMaximized(): win.showNormal()
        else: win.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition() - QPointF(self.window().frameGeometry().topLeft())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.window().move((event.globalPosition() - self.drag_position).toPoint())
            event.accept()
            
    def mouseReleaseEvent(self, event):
        self.drag_position = None
        event.accept()