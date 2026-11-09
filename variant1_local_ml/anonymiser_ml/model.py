"""Small data types shared by every stage of the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Box:
    """Axis-aligned rectangle: (x0, y0) top-left, (x1, y1) bottom-right."""

    x0: float
    y0: float
    x1: float
    y1: float

    def pad(self, p: float) -> "Box":
        return Box(self.x0 - p, self.y0 - p, self.x1 + p, self.y1 + p)

    def scale(self, s: float) -> "Box":
        return Box(self.x0 * s, self.y0 * s, self.x1 * s, self.y1 * s)

    def shift(self, dx: float, dy: float) -> "Box":
        return Box(self.x0 + dx, self.y0 + dy, self.x1 + dx, self.y1 + dy)

    def union(self, other: "Box") -> "Box":
        return Box(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )

    def clip(self, width: float, height: float) -> "Box":
        return Box(max(0, self.x0), max(0, self.y0), min(width, self.x1), min(height, self.y1))


@dataclass
class Word:
    """One recognised word plus where it sits. `line` groups words into lines."""

    text: str
    box: Box
    line: tuple


@dataclass
class Finding:
    """Something that will be blacked out."""

    kind: str
    text: str
    boxes: list[Box] = field(default_factory=list)
    source: str = "rule"
    page: int = 0


def mask(text: str) -> str:
    """Show a hint of a finding in reports without printing the secret itself."""
    text = text.strip()
    if len(text) <= 2:
        return "*" * len(text)
    return f"{text[0]}{'*' * min(len(text) - 2, 8)}{text[-1]}"
