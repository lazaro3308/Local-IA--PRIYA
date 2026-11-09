"""Generate the local Arasaka-inspired Priya Windows icon with Qt (no network)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "assets" / "priya_arasaka.ico"


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(256, 256, QImage.Format_ARGB32)
    image.fill(QColor("#0a0e16"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    red = QColor("#e34b55")
    painter.setPen(QPen(red, 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(22, 22, 212, 212)
    painter.drawLine(128, 54, 128, 125)
    painter.drawLine(128, 125, 76, 187)
    painter.drawLine(128, 125, 180, 187)
    painter.setBrush(red)
    painter.setPen(Qt.NoPen)
    for x, y in ((128, 54), (76, 187), (180, 187)):
        painter.drawEllipse(x - 11, y - 11, 22, 22)
    painter.end()
    if not image.save(str(TARGET), "ICO"):
        raise RuntimeError(f"Qt não conseguiu gravar o ícone: {TARGET}")
    print(f"Ícone criado: {TARGET} ({TARGET.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
