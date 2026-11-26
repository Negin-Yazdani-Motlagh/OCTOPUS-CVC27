"""Bird's-eye-view IoU in the DMSTrack KITTI camera frame.

Corner order and yaw follow AB3DMOT ``Box3D.box2corners3d_camcoord`` and
``iou3d`` at commit d3b9949499c8e68ea33060873bd1cb95b6d4d323. The ground
rectangle is the bottom face projected onto X and Z. Y is not used.
"""
from __future__ import annotations

import math


def roty(yaw: float) -> tuple[tuple[float, float, float], ...]:
    """Rotation about the camera Y axis, matching ``kitti_oxts.roty``."""
    cosine, sine = math.cos(yaw), math.sin(yaw)
    return ((cosine, 0.0, sine), (0.0, 1.0, 0.0), (-sine, 0.0, cosine))


def bev_corners(x: float, z: float, length: float, width: float, yaw: float) -> list[tuple[float, float]]:
    """Four X-Z corners, counter-clockwise, length along X before yaw."""
    cosine, sine = math.cos(yaw), math.sin(yaw)
    raw = []
    for along, across in (
        (length / 2, width / 2),
        (length / 2, -width / 2),
        (-length / 2, -width / 2),
        (-length / 2, width / 2),
    ):
        raw.append((x + cosine * along + sine * across, z - sine * along + cosine * across))
    # ``iou3d`` reads bottom corners 3, 2, 1, 0 so the clipper sees a
    # counter-clockwise rectangle.
    return _ensure_ccw([raw[3], raw[2], raw[1], raw[0]])


def polygon_area(polygon: list[tuple[float, float]]) -> float:
    if len(polygon) < 3:
        return 0.0
    total = 0.0
    for index, (x_coord, z_coord) in enumerate(polygon):
        next_x, next_z = polygon[(index + 1) % len(polygon)]
        total += x_coord * next_z - next_x * z_coord
    return abs(total) * 0.5


def assign_one_to_one(scores: list[float], detection_corners: list[list[tuple[float, float]]],
                      ground_truth_corners: list[list[tuple[float, float]]],
                      threshold: float) -> dict[int, tuple[int, float]]:
    """Assign each detection to at most one ground-truth box in one frame.

    Detections are considered from highest score to lowest, matching
    OpenCOOD ``caluclate_tp_fp``. A detection takes the still-unmatched
    ground-truth box with the largest bird's-eye-view IoU when that IoU
    is at least ``threshold``.
    """
    order = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    taken: set[int] = set()
    assignment: dict[int, tuple[int, float]] = {}
    for detection_index in order:
        best_gt = None
        best_iou = -1.0
        for gt_index, gt_corners in enumerate(ground_truth_corners):
            if gt_index in taken:
                continue
            overlap = bev_iou(detection_corners[detection_index], gt_corners)
            if overlap > best_iou:
                best_gt = gt_index
                best_iou = overlap
        if best_gt is not None and best_iou >= threshold:
            taken.add(best_gt)
            assignment[best_gt] = (detection_index, best_iou)
    return assignment


def bev_iou(first: list[tuple[float, float]], second: list[tuple[float, float]]) -> float:
    area_first = polygon_area(first)
    area_second = polygon_area(second)
    intersection = polygon_area(_clip(_ensure_ccw(first), _ensure_ccw(second)))
    union = area_first + area_second - intersection
    if union <= 0.0:
        return 0.0
    return intersection / union


def _signed_area(polygon: list[tuple[float, float]]) -> float:
    total = 0.0
    for index, (x_coord, z_coord) in enumerate(polygon):
        next_x, next_z = polygon[(index + 1) % len(polygon)]
        total += x_coord * next_z - next_x * z_coord
    return total * 0.5


def _ensure_ccw(polygon: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if _signed_area(polygon) < 0.0:
        return list(reversed(polygon))
    return list(polygon)


def _clip(subject: list[tuple[float, float]], clipper: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Sutherland-Hodgman clip. The clipper must be convex and counter-clockwise.

    A shared or parallel edge is kept as a boundary. Dividing by that edge's
    crossing would invent points far outside both rectangles.
    """
    output = subject
    previous = clipper[-1]
    for current in clipper:
        if not output:
            return []
        incoming = output
        output = []
        start = incoming[-1]
        start_inside = _inside(start, previous, current)
        for end in incoming:
            end_inside = _inside(end, previous, current)
            if start_inside != end_inside:
                crossing = _intersection(start, end, previous, current)
                if crossing is not None:
                    output.append(crossing)
            if end_inside:
                output.append(end)
            start, start_inside = end, end_inside
        previous = current
    return _dedupe(output)


def _inside(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> bool:
    return _cross(start, end, point) >= -1e-9


def _cross(start: tuple[float, float], end: tuple[float, float], point: tuple[float, float]) -> float:
    return (end[0] - start[0]) * (point[1] - start[1]) - (end[1] - start[1]) * (point[0] - start[0])


def _intersection(start: tuple[float, float], end: tuple[float, float],
                  clip_start: tuple[float, float], clip_end: tuple[float, float]) -> tuple[float, float] | None:
    delta_clip = (clip_start[0] - clip_end[0], clip_start[1] - clip_end[1])
    delta_edge = (start[0] - end[0], start[1] - end[1])
    denominator = delta_clip[0] * delta_edge[1] - delta_clip[1] * delta_edge[0]
    if abs(denominator) <= 1e-12:
        return None
    cross_clip = clip_start[0] * clip_end[1] - clip_start[1] * clip_end[0]
    cross_edge = start[0] * end[1] - start[1] * end[0]
    scale = 1.0 / denominator
    return (
        (cross_clip * delta_edge[0] - cross_edge * delta_clip[0]) * scale,
        (cross_clip * delta_edge[1] - cross_edge * delta_clip[1]) * scale,
    )


def _dedupe(polygon: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not polygon:
        return []
    cleaned = [polygon[0]]
    for point in polygon[1:]:
        if abs(point[0] - cleaned[-1][0]) > 1e-9 or abs(point[1] - cleaned[-1][1]) > 1e-9:
            cleaned.append(point)
    if len(cleaned) > 1 and abs(cleaned[0][0] - cleaned[-1][0]) <= 1e-9 and abs(cleaned[0][1] - cleaned[-1][1]) <= 1e-9:
        cleaned.pop()
    return cleaned
