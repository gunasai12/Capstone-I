"""
Spatial reasoning logic for advanced violation detection
Includes rider-to-bike assignment and helmet-to-person matching
"""
from typing import List, Tuple

BBox = Tuple[int, int, int, int]


def bbox_center(b: BBox) -> Tuple[float, float]:
    """Calculate center point of bounding box"""
    x1, y1, x2, y2 = b
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def point_inside(b: BBox, p: Tuple[float, float]) -> bool:
    """Check if point is inside bounding box"""
    x1, y1, x2, y2 = b
    x, y = p
    return x1 <= x <= x2 and y1 <= y <= y2


def iou(a: BBox, b: BBox) -> float:
    """Calculate Intersection over Union between two bounding boxes"""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_w = max(0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter + 1e-6
    return inter / union


def head_region(person_bbox: BBox, top_ratio: float = 0.3) -> BBox:
    """Extract head region from person bounding box (top 30%)"""
    x1, y1, x2, y2 = person_bbox
    h = y2 - y1
    return (x1, y1, x2, int(y1 + top_ratio * h))


def assign_riders_to_bike(bike_bbox: BBox, person_bboxes: List[BBox]) -> List[BBox]:
    """
    Assign riders to a bike using spatial reasoning.
    A person is considered riding the bike if their center is inside the bike bbox.
    """
    riders = []
    for pb in person_bboxes:
        if point_inside(bike_bbox, bbox_center(pb)):
            riders.append(pb)
    return riders


def has_helmet_for_person(person_bbox: BBox, helmet_bboxes: List[BBox]) -> bool:
    """
    Check if person has a helmet using head region matching.
    Returns True if any helmet bbox overlaps with the person's head region.
    """
    head = head_region(person_bbox)
    for hb in helmet_bboxes:
        if iou(head, hb) > 0:
            return True
    return False


def count_riders_on_bike(bike_bbox: BBox, person_bboxes: List[BBox]) -> int:
    """Count number of riders on a bike"""
    return len(assign_riders_to_bike(bike_bbox, person_bboxes))
