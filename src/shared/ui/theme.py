"""
Modern Dark Theme — Premium dark theme for the application.

Provides a cohesive, modern aesthetic with:
- Deep dark backgrounds with subtle blue tints
- Vibrant accent colors
- Rounded corners and smooth transitions
- Custom styled widgets
"""


# ─── Color Palette ─────────────────────────────────────────────────

COLORS = {
    'bg_primary':      '#0f0f1a',      # Deep dark blue-black
    'bg_secondary':    '#1a1a2e',      # Slightly lighter
    'bg_tertiary':     '#16213e',      # Card backgrounds
    'bg_widget':       '#1e2a4a',      # Input fields, etc.
    'bg_hover':        '#2a3a5c',      # Hover state
    'bg_active':       '#334775',      # Active/pressed state
    'border':          '#2a3a5c',      # Subtle borders
    'border_focus':    '#6c63ff',      # Focus border
    'text_primary':    '#e8e8f0',      # Main text
    'text_secondary':  '#9898b0',      # Secondary text
    'text_muted':      '#6868a0',      # Muted text
    'accent':          '#6c63ff',      # Primary accent (violet)
    'accent_hover':    '#7f78ff',      # Accent hover
    'accent2':         '#00d4aa',      # Secondary accent (teal)
    'accent3':         '#ff6b9d',      # Tertiary accent (pink)
    'success':         '#00d68f',      # Success green
    'warning':         '#ffaa00',      # Warning amber
    'error':           '#ff4466',      # Error red
    'scrollbar_bg':    '#1a1a2e',      # Scrollbar track
    'scrollbar_handle':'#334775',      # Scrollbar handle
    'viewer_bg':       '#ffffff',      # 3D viewer background (white)
}


def get_stylesheet():
    """Generate the complete application stylesheet."""
    return f"""
    /* ── Global ── */
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
    }}

    QWidget {{
        background-color: transparent;
        color: {COLORS['text_primary']};
        font-family: 'Segoe UI', 'SF Pro Display', 'Roboto', sans-serif;
        font-size: 13px;
    }}

    /* ── Menu Bar ── */
    QMenuBar {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border-bottom: 1px solid {COLORS['border']};
        padding: 4px 0;
        font-size: 13px;
    }}
    QMenuBar::item {{
        padding: 6px 14px;
        border-radius: 6px;
        margin: 2px 2px;
    }}
    QMenuBar::item:selected {{
        background-color: {COLORS['bg_hover']};
    }}

    QMenu {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 8px 30px 8px 20px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {COLORS['accent']};
        color: white;
    }}
    QMenu::separator {{
        height: 1px;
        background: {COLORS['border']};
        margin: 4px 10px;
    }}

    /* ── Buttons ── */
    QPushButton {{
        background-color: {COLORS['accent']};
        color: white;
        border: none;
        padding: 10px 22px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['accent_hover']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['bg_active']};
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_widget']};
        color: {COLORS['text_muted']};
    }}

    QPushButton#btnSecondary {{
        background-color: {COLORS['bg_widget']};
        border: 1px solid {COLORS['border']};
    }}
    QPushButton#btnSecondary:hover {{
        background-color: {COLORS['bg_hover']};
        border-color: {COLORS['accent']};
    }}

    QPushButton#btnSuccess {{
        background-color: {COLORS['success']};
    }}
    QPushButton#btnSuccess:hover {{
        background-color: #00e8a0;
    }}

    QPushButton#btnDanger {{
        background-color: {COLORS['error']};
    }}
    QPushButton#btnDanger:hover {{
        background-color: #ff5577;
    }}

    /* ── Text Input ── */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {COLORS['bg_widget']};
        color: {COLORS['text_primary']};
        border: 2px solid {COLORS['border']};
        border-radius: 8px;
        padding: 10px 14px;
        font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
        font-size: 14px;
        selection-background-color: {COLORS['accent']};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {COLORS['border_focus']};
    }}
    QLineEdit:hover, QTextEdit:hover {{
        border-color: {COLORS['bg_hover']};
    }}

    /* ── Labels ── */
    QLabel {{
        color: {COLORS['text_primary']};
        padding: 0px;
    }}
    QLabel#labelTitle {{
        font-size: 22px;
        font-weight: 700;
        color: {COLORS['text_primary']};
    }}
    QLabel#labelSubtitle {{
        font-size: 14px;
        color: {COLORS['text_secondary']};
    }}
    QLabel#labelSection {{
        font-size: 15px;
        font-weight: 600;
        color: {COLORS['accent2']};
        padding: 4px 0;
    }}
    QLabel#labelMuted {{
        font-size: 12px;
        color: {COLORS['text_muted']};
    }}

    /* ── Group Boxes ── */
    QGroupBox {{
        background-color: {COLORS['bg_tertiary']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        margin-top: 16px;
        padding: 18px 14px 14px 14px;
        font-weight: 600;
        font-size: 14px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 8px;
        color: {COLORS['accent2']};
    }}

    /* ── Progress Bar ── */
    QProgressBar {{
        background-color: {COLORS['bg_widget']};
        border: none;
        border-radius: 6px;
        text-align: center;
        color: {COLORS['text_primary']};
        min-height: 12px;
        max-height: 12px;
        font-size: 10px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {COLORS['accent']}, stop:1 {COLORS['accent2']});
        border-radius: 6px;
    }}

    /* ── Status Bar ── */
    QStatusBar {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        border-top: 1px solid {COLORS['border']};
        padding: 4px;
        font-size: 12px;
    }}

    /* ── Scrollbars ── */
    QScrollBar:vertical {{
        background: {COLORS['scrollbar_bg']};
        width: 10px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['scrollbar_handle']};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS['accent']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: {COLORS['scrollbar_bg']};
        height: 10px;
        border-radius: 5px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {COLORS['scrollbar_handle']};
        border-radius: 5px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {COLORS['accent']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ── Splitter ── */
    QSplitter::handle {{
        background-color: {COLORS['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}

    /* ── Tool Tips ── */
    QToolTip {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ── Tab Widget ── */
    QTabWidget::pane {{
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        background-color: {COLORS['bg_tertiary']};
    }}
    QTabBar::tab {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        padding: 10px 20px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        font-weight: 500;
    }}
    QTabBar::tab:selected {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['accent']};
        border-bottom: 2px solid {COLORS['accent']};
    }}
    QTabBar::tab:hover {{
        background-color: {COLORS['bg_hover']};
    }}

    /* ── File Dialog ── */
    QFileDialog {{
        background-color: {COLORS['bg_primary']};
    }}

    /* ── Combo Box ── */
    QComboBox {{
        background-color: {COLORS['bg_widget']};
        border: 2px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px 12px;
        color: {COLORS['text_primary']};
        min-height: 20px;
    }}
    QComboBox:hover {{
        border-color: {COLORS['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        color: {COLORS['text_primary']};
        selection-background-color: {COLORS['accent']};
    }}
    """
