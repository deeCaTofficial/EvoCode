# src/evocode_gui/neural_background.py
# Ваш код для NeuralBackgroundWidget сюда...
# Я скопирую его полностью, чтобы быть уверенным в результате.
import math
import random
import sys
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import QWidget, QPushButton, QApplication, QMainWindow
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPaintEvent, QResizeEvent, QShowEvent,
    QMouseEvent, QPainterPath
)
from PyQt6.QtCore import QTimer, QPointF, Qt, QRect, QRectF, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QPoint

class Particle:
    __slots__ = ('pos', 'vel', 'size', 'parallax_factor', 'mass')
    def __init__(self, pos: QPointF, vel: QPointF, size: float, parallax_factor: float, mass: float):
        self.pos, self.vel, self.size, self.parallax_factor, self.mass = pos, vel, size, parallax_factor, mass

class NeuralBackgroundWidget(QWidget):
    PARTICLE_COUNT: int = 80
    CONNECTION_DISTANCE: float = 120.0
    BASE_SPEED: float = 0.2
    MAX_SPEED: float = 0.3
    REPULSION_RADIUS: float = 100.0
    REPULSION_STRENGTH: float = 1.5
    BG_COLOR = QColor(32, 34, 37)
    PARTICLE_COLOR = QColor(80, 85, 97, 150)
    LINE_BASE_COLOR = QColor(80, 85, 97)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.particles: List[Particle] = []
        self.mouse_pos = QPointF(-1, -1)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_particles)
        self.setMouseTracking(True)
        self.is_animation_running = False

    def _rand_float(self, min_val: float, max_val: float) -> float: return random.uniform(min_val, max_val)
    def _create_particle(self) -> Particle:
        size = self._rand_float(1.5, 3.5)
        return Particle(QPointF(self._rand_float(0, self.width()), self._rand_float(0, self.height())), QPointF(self._rand_float(-self.BASE_SPEED, self.BASE_SPEED), self._rand_float(-self.BASE_SPEED, self.BASE_SPEED)), size, self._rand_float(0.1, 0.5), size*size)
    def init_particles(self):
        if not self.isVisible() or self.width() == 0: return
        self.particles = [self._create_particle() for _ in range(self.PARTICLE_COUNT)]
        if self.mouse_pos.x() < 0: self.mouse_pos = QPointF(self.width() / 2, self.height() / 2)
        self.update()
    def update_particles(self):
        if not self.is_animation_running: return
        w, h = self.width(), self.height()
        for p in self.particles:
            p.pos += p.vel
            if p.pos.x() < 0 or p.pos.x() > w: p.vel.setX(-p.vel.x())
            if p.pos.y() < 0 or p.pos.y() > h: p.vel.setY(-p.vel.y())
            if self.mouse_pos.x() > 0:
                vec_from_mouse = p.pos - self.mouse_pos
                dist_sq = vec_from_mouse.x()**2 + vec_from_mouse.y()**2
                if dist_sq < self.REPULSION_RADIUS**2 and dist_sq > 1e-6:
                    dist = math.sqrt(dist_sq)
                    force = (1 - dist / self.REPULSION_RADIUS) * self.REPULSION_STRENGTH
                    p.pos += (vec_from_mouse / dist) * force
        self.update()
    def start_animation(self):
        if not self.is_animation_running: self.is_animation_running = True; self.animation_timer.start(33)
    def stop_animation(self):
        if self.is_animation_running: self.is_animation_running = False; self.animation_timer.stop()
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.BG_COLOR)
        if not self.particles: return
        for i in range(len(self.particles)):
            for j in range(i + 1, len(self.particles)):
                p1, p2 = self.particles[i], self.particles[j]
                dist_sq = (p1.pos.x() - p2.pos.x())**2 + (p1.pos.y() - p2.pos.y())**2
                if dist_sq < self.CONNECTION_DISTANCE**2:
                    alpha = int(100 * (1 - dist_sq / self.CONNECTION_DISTANCE**2))
                    if alpha > 0:
                        pen_color = QColor(self.LINE_BASE_COLOR)
                        pen_color.setAlpha(alpha)
                        painter.setPen(QPen(pen_color, 1))
                        painter.drawLine(p1.pos, p2.pos)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.PARTICLE_COLOR)
        for p in self.particles: painter.drawEllipse(p.pos, p.size, p.size)
    def resizeEvent(self, event: QResizeEvent): self.init_particles()
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.init_particles()
        if self.is_animation_running and not self.animation_timer.isActive(): self.animation_timer.start(33)
    def hideEvent(self, event): super().hideEvent(event); self.animation_timer.stop()
    def update_mouse_position(self, pos: QPoint): self.mouse_pos = QPointF(pos)