"""The HUD's colors and type, in one place."""

from dataclasses import dataclass, field

from PySide6.QtGui import QColor, QFont


def _rgba(red: int, green: int, blue: int, alpha: float = 1.0) -> QColor:
    return QColor(red, green, blue, round(alpha * 255))


@dataclass(frozen=True)
class Theme:
    # Surfaces
    panel: QColor = field(default_factory=lambda: _rgba(11, 14, 20, 0.86))
    panel_border: QColor = field(default_factory=lambda: _rgba(255, 255, 255, 0.12))
    divider: QColor = field(default_factory=lambda: _rgba(255, 255, 255, 0.08))
    shadow: QColor = field(default_factory=lambda: _rgba(0, 0, 0, 0.10))
    halo: QColor = field(default_factory=lambda: _rgba(5, 8, 12, 0.72))  # under lines on the map

    # Text
    text: QColor = field(default_factory=lambda: _rgba(244, 247, 250))
    text_dim: QColor = field(default_factory=lambda: _rgba(244, 247, 250, 0.56))
    text_faint: QColor = field(default_factory=lambda: _rgba(244, 247, 250, 0.30))

    # Meaning. The map itself uses green, orange, red and white, so the
    # player's marks are cyan and everything about the target is amber.
    you: QColor = field(default_factory=lambda: _rgba(86, 204, 255))
    target: QColor = field(default_factory=lambda: _rgba(255, 184, 77))
    live: QColor = field(default_factory=lambda: _rgba(74, 222, 128))
    stale: QColor = field(default_factory=lambda: _rgba(251, 191, 36))
    idle: QColor = field(default_factory=lambda: _rgba(148, 163, 184))

    # Segoe UI has digits of equal width, so numbers don't jitter as they change.
    families: tuple[str, ...] = ("Segoe UI Variable Display", "Segoe UI", "Arial")
    mono_families: tuple[str, ...] = ("Cascadia Mono", "Consolas", "Courier New")

    def font(
        self,
        px: float,
        weight: QFont.Weight = QFont.Weight.Medium,
        spacing: float = 0.0,
        mono: bool = False,
    ) -> QFont:
        """A font px pixels tall, with spacing extra pixels between letters."""
        font = QFont()
        font.setFamilies(list(self.mono_families if mono else self.families))
        font.setPixelSize(round(px))
        font.setWeight(weight)
        if spacing:
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        return font
