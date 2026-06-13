from pydantic import BaseModel
from typing import List

class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class Bubble(BaseModel):
    jp_text: str
    coords: BoundingBox

class Panel(BaseModel):
    coords: BoundingBox

class DetectionResult(BaseModel):
    bubbles: List[Bubble]
    panels: List[Panel]
