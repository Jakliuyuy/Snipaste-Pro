from PyQt6.QtGui import QIcon, QPixmap

SVG_ICONS = {
    "rect": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="1.5"/></svg>""",
    "ellipse": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>""",
    "arrow": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="19" x2="18" y2="6"/><polyline points="9 6 18 6 18 15"/></svg>""",
    "line": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="4" y1="20" x2="20" y2="4"/></svg>""",
    "pencil": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>""",
    "marker": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m14 12-8.5 8.5a2.12 2.12 0 1 1-3-3L11 9"/><path d="M18 10l-4-4"/><path d="m15 4 4 4"/></svg>""",
    "text": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 7 4 4 20 4 20 7"/><line x1="12" y1="4" x2="12" y2="20"/></svg>""",
    "number": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M10.5 9.5 12 8.5v7" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 16h4" stroke-linecap="round"/></svg>""",
    "mosaic": """<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="3" y="3" width="5" height="5" rx="0.5"/><rect x="10" y="3" width="5" height="5" rx="0.5" fill-opacity="0.35"/><rect x="16" y="3" width="5" height="5" rx="0.5"/><rect x="3" y="10" width="5" height="5" rx="0.5" fill-opacity="0.35"/><rect x="10" y="10" width="5" height="5" rx="0.5"/><rect x="16" y="10" width="5" height="5" rx="0.5" fill-opacity="0.35"/><rect x="3" y="16" width="5" height="5" rx="0.5"/><rect x="10" y="16" width="5" height="5" rx="0.5" fill-opacity="0.35"/><rect x="16" y="16" width="5" height="5" rx="0.5"/></svg>""",
    "blur": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 8c3-3 6-3 9 0s6 3 9 0"/><path d="M3 12c3-3 6-3 9 0s6 3 9 0"/><path d="M3 16c3-3 6-3 9 0s6 3 9 0"/></svg>""",
    "eraser": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m7 21-4.3-4.3c-1-1-1-2.5 0-3.4l9.6-9.6c1-1 2.5-1 3.4 0l5.6 5.6c1 1 1 2.5 0 3.4L13 21"/><path d="M22 21H7"/><path d="m5 11 9 9"/></svg>""",
    "undo": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11"/></svg>""",
    "redo": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 14 5-5-5-5"/><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5v0A5.5 5.5 0 0 0 9.5 20H13"/></svg>""",
    "translate": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9.5"/><line x1="2.5" y1="12" x2="21.5" y2="12"/><path d="M12 2.5a15 15 0 0 1 4 9.5 15 15 0 0 1-4 9.5 15 15 0 0 1-4-9.5 15 15 0 0 1 4-9.5z"/></svg>""",
    "pin": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-2l-2-3V5a2 2 0 0 0-2-2h-6a2 2 0 0 0-2 2v7l-2 3v2z"/></svg>""",
    "save": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>""",
    "done": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>""",
    "close": """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>"""
}

_ICON_CACHE = {}

def get_svg_icon(name: str, color: str = "#E0E3EA", size: int = 20) -> QIcon:
    cache_key = (name, color, size)
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    raw_svg = SVG_ICONS.get(name)
    if not raw_svg:
        return QIcon()

    svg = raw_svg.replace("currentColor", color)
    pix = QPixmap(size, size)
    pix.fill(pix.toImage().format()) if hasattr(pix, "isNull") and False else None
    pix.loadFromData(svg.encode("utf-8"), "SVG")

    icon = QIcon(pix)
    _ICON_CACHE[cache_key] = icon
    return icon
