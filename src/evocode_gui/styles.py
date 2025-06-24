# src/evocode_gui/styles.py
# -*- coding: utf-8 -*-
"""
Содержит финальную таблицу стилей (QSS) для создания отполированного,
современного dashboard-интерфейса.
"""

PALETTE = {
    "bg_base": "#202225",
    "bg_sidebar": "#2f3136",
    "bg_content": "#36393f",
    "bg_widget": "#202225",
    "border_color": "#40444b",
    "text_header": "#ffffff",
    "text_primary": "#f2f3f5",
    "text_secondary": "#b9bbbe",
    "text_muted": "#949ba4",
    "accent_success": "#248046",
    "accent_success_hover": "#1a5c32",
    "accent_danger": "#da373c",
    "accent_danger_hover": "#a82b2f",
    "glass_sidebar_bg": "rgba(47, 49, 54, 160)",
    "glass_content_bg": "rgba(54, 57, 63, 150)",
    "glass_border": "rgba(255, 255, 255, 15)",
}

MODERN_STYLE_SHEET = f"""
    /* --- ОБЩИЕ СТИЛИ --- */
    QWidget {{
        color: {PALETTE['text_primary']};
        font-family: 'Inter', 'Segoe UI', sans-serif;
        font-size: 10pt;
        border: none;
    }}
    
    QToolTip {{
        background-color: {PALETTE['bg_base']};
        color: {PALETTE['text_primary']};
        border: 1px solid {PALETTE['border_color']};
        padding: 5px;
        border-radius: 5px;
    }}

    #TitleBar {{
        background-color: transparent;
    }}

    /* --- ПАНЕЛИ --- */
    #Sidebar {{
        background-color: {PALETTE['glass_sidebar_bg']};
        border-radius: 10px;
        border: 1px solid {PALETTE['glass_border']};
    }}
    #ContentPane {{
        background-color: transparent;
        border: none;
    }}

    /* --- ТИПОГРАФИКА --- */
    QLabel#Header {{
        font-size: 16pt;
        font-weight: 700;
        color: {PALETTE['text_header']};
    }}
    QLabel#SubHeader {{
        font-size: 9pt;
        font-weight: 600;
        color: {PALETTE['text_muted']};
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    QLabel#PathLabel {{
        color: {PALETTE['text_secondary']};
        font-size: 9pt;
    }}
    QLabel#PathLabel:hover {{
        color: {PALETTE['text_primary']};
    }}
    
    /* --- КНОПКИ --- */
    QPushButton#RunButton {{
        background-color: {PALETTE['accent_success']};
        color: white;
        font-weight: bold;
        padding: 12px;
        border-radius: 5px;
    }}
    QPushButton#RunButton:hover {{
        background-color: {PALETTE['accent_success_hover']};
    }}
    QPushButton#RunButton:disabled {{
        background-color: {PALETTE['bg_sidebar']};
        color: {PALETTE['text_muted']};
    }}
    QPushButton#CancelButton {{
        background-color: transparent;
        color: {PALETTE['text_muted']};
        border: 1px solid {PALETTE['border_color']};
        font-weight: bold;
        padding: 11px;
        border-radius: 5px;
    }}
    QPushButton#CancelButton:hover {{
        background-color: {PALETTE['accent_danger']};
        color: white;
        border-color: {PALETTE['accent_danger']};
    }}
    QPushButton#CancelButton:disabled {{
        background-color: {PALETTE['bg_sidebar']};
        color: {PALETTE['text_muted']};
        border-color: {PALETTE['border_color']};
    }}

    /* --- КАСТОМНЫЙ VALUE SELECTOR --- */
    #ValueSelector {{
        background-color: rgba(0, 0, 0, 100);
        border: 1px solid {PALETTE['border_color']};
        border-radius: 5px;
    }}
    #ValueSelector:hover {{
        border: 1px solid {PALETTE['text_muted']};
    }}
    #ValueSelectorButton {{
        background-color: transparent;
        border: none;
        border-radius: 4px;
        min-width: 28px;
        max-width: 28px;
    }}
    #ValueSelectorButton:hover {{
        background-color: rgba(255, 255, 255, 10);
    }}
    #ValueSelectorLabel {{
        background-color: transparent;
        border: none;
        font-weight: 600;
    }}

    /* --- КАРТОЧКА СТАТУСА --- */
    #TaskCard {{
        background-color: transparent;
        border-radius: 8px;
        border: 1px solid {PALETTE['border_color']};
        padding: 20px;
    }}
    #IdeaLabel {{
        font-size: 11pt;
        font-weight: 500;
        color: {PALETTE['text_primary']};
    }}
    #PlanTextEdit {{
        background-color: transparent;
        border: none;
        color: {PALETTE['text_secondary']};
    }}
    
    /* --- РАЗДЕЛИТЕЛЬ (SPLITTER) --- */
    QSplitter::handle:horizontal {{
        background: transparent;
        width: 5px;
        margin: 0px;
    }}
    
    /* --- КОНТЕЙНЕРЫ ДЛЯ ДЕРЕВА И ЛОГА --- */
    #FileTreeContainer, #LogContainer {{
        background-color: {PALETTE['glass_content_bg']};
        border-radius: 8px;
        border: 1px solid {PALETTE['glass_border']};
    }}
    
    /* --- ВНУТРЕННИЕ ВИДЖЕТЫ (ДЕРЕВО И ЛОГ) --- */
    QPlainTextEdit, QTreeView {{
        background-color: transparent;
        border: none;
        padding: 5px;
    }}
    QPlainTextEdit {{
        font-family: 'Fira Code', 'Consolas', monospace;
    }}
    QTreeView {{
        background-color: transparent;
        border: none;
        padding: 5px;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }}
    QTreeView::item {{
        padding: 5px 0px;
        border-radius: 4px;
    }}
    QTreeView::item:selected, QTreeView::item:selected:active {{
        background-color: {PALETTE['glass_border']};
        color: {PALETTE['text_header']};
    }}
    QTreeView::item:hover:!selected {{
        background-color: rgba(255, 255, 255, 5);
    }}
    
    /* ИЗМЕНЕНИЕ: Полностью удаляем все упоминания ::branch,
       чтобы позволить Qt рисовать стандартные стрелки. */

    /* --- ПРОГРЕСС-БАР --- */
    QProgressBar {{
        background-color: rgba(0,0,0,120);
        border-radius: 3px;
        height: 6px;
    }}
    QProgressBar::chunk {{
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PALETTE['accent_success']}, stop:1 #86efac);
        border-radius: 3px;
    }}
    
    /* --- КАСТОМНЫЙ MESSAGEBOX --- */
    #MessageBoxContainer {{
        background-color: {PALETTE['bg_sidebar']};
        border: 1px solid {PALETTE['border_color']};
        border-radius: 8px;
    }}
    #MessageBoxTitle {{ font-weight: 600; color: {PALETTE['text_primary']}; }}
    #MessageBoxCloseButton {{ background-color: transparent; border-radius: 5px; }}
    #MessageBoxCloseButton:hover {{ background-color: {PALETTE['accent_danger']}; }}
    #MessageBoxOKButton {{ background-color: {PALETTE['accent_success']}; color: white; font-weight: bold; padding: 8px 25px; border-radius: 5px; }}
    #MessageBoxOKButton:hover {{ background-color: {PALETTE['accent_success_hover']}; }}

    /* ФИНАЛЬНЫЕ СТИЛИ ДЛЯ СКРОЛЛБАРОВ С "ТРЮКОМ" */
    QScrollBar:vertical {{
        border: none;
        background-color: rgba(0, 0, 0, 50); /* Полупрозрачный фон для всей полосы */
        width: 12px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background-color: {PALETTE['border_color']};
        border-radius: 6px; /* Закругляем фон ручки */
        min-height: 30px;
        margin: 2px 2px; /* Создаем отступы по бокам, чтобы ручка была тоньше полосы */
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {PALETTE['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
    
    /* Применяем те же стили к другим виджетам */
    QPlainTextEdit QScrollBar:vertical, QTextEdit QScrollBar:vertical {{
        border: none;
        background-color: rgba(0, 0, 0, 50);
        width: 12px;
        margin: 0;
    }}
"""