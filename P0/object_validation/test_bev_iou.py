"""Geometric checks for the DMSTrack camera-frame bird's-eye-view IoU."""
from __future__ import annotations

import math
import unittest

from bev_iou import assign_one_to_one, bev_corners, bev_iou, polygon_area, roty


def _close(actual: float, expected: float, places: int = 6) -> None:
    if abs(actual - expected) > 10 ** (-places):
        raise AssertionError(f"{actual} != {expected}")


class BevIouTests(unittest.TestCase):
    def test_yaw_zero_puts_length_on_x_and_width_on_z(self) -> None:
        corners = bev_corners(0.0, 0.0, 4.0, 2.0, 0.0)
        xs = [point[0] for point in corners]
        zs = [point[1] for point in corners]
        _close(max(xs) - min(xs), 4.0)
        _close(max(zs) - min(zs), 2.0)
        _close(polygon_area(corners), 8.0)

    def test_roty_matches_upstream_matrix(self) -> None:
        yaw = math.pi / 2
        matrix = roty(yaw)
        self.assertAlmostEqual(matrix[0][0], 0.0, places=9)
        self.assertAlmostEqual(matrix[0][2], 1.0, places=9)
        self.assertAlmostEqual(matrix[2][0], -1.0, places=9)
        self.assertAlmostEqual(matrix[2][2], 0.0, places=9)

    def test_identical_and_half_turn_boxes_match(self) -> None:
        first = bev_corners(3.0, -2.0, 4.5, 1.8, 0.4)
        self.assertAlmostEqual(bev_iou(first, first), 1.0, places=6)
        turned = bev_corners(3.0, -2.0, 4.5, 1.8, 0.4 + math.pi)
        self.assertAlmostEqual(bev_iou(first, turned), 1.0, places=6)

    def test_disjoint_boxes_have_zero_overlap(self) -> None:
        first = bev_corners(0.0, 0.0, 4.0, 2.0, 0.0)
        second = bev_corners(10.0, 0.0, 4.0, 2.0, 0.0)
        self.assertAlmostEqual(bev_iou(first, second), 0.0, places=6)

    def test_axis_aligned_half_shift_is_one_third(self) -> None:
        # Length 4 and width 2. A center shift of 2 m overlaps half the length.
        # Intersection area 4, each box area 8, union 12.
        first = bev_corners(0.0, 0.0, 4.0, 2.0, 0.0)
        second = bev_corners(2.0, 0.0, 4.0, 2.0, 0.0)
        self.assertAlmostEqual(bev_iou(first, second), 1.0 / 3.0, places=6)

    def test_contained_box_uses_the_smaller_area(self) -> None:
        outer = bev_corners(0.0, 0.0, 4.0, 4.0, 0.0)
        inner = bev_corners(0.0, 0.0, 2.0, 2.0, 0.3)
        self.assertAlmostEqual(bev_iou(outer, inner), 4.0 / 16.0, places=6)

    def test_quarter_turn_overlap_is_one_third(self) -> None:
        # Yaw pi/2 swaps the 4 m length onto Z. The overlap is the 2 m by 2 m center square.
        flat = bev_corners(0.0, 0.0, 4.0, 2.0, 0.0)
        turned = bev_corners(0.0, 0.0, 4.0, 2.0, math.pi / 2)
        self.assertAlmostEqual(bev_iou(flat, turned), 1.0 / 3.0, places=6)

    def test_quarter_turn_swaps_the_ground_extents(self) -> None:
        corners = bev_corners(0.0, 0.0, 4.0, 2.0, math.pi / 2)
        xs = [point[0] for point in corners]
        zs = [point[1] for point in corners]
        _close(max(xs) - min(xs), 2.0)
        _close(max(zs) - min(zs), 4.0)


class MatchingTests(unittest.TestCase):
    def test_higher_score_takes_the_only_ground_truth(self) -> None:
        gt = [bev_corners(0.0, 0.0, 4.0, 2.0, 0.0)]
        near = bev_corners(0.2, 0.0, 4.0, 2.0, 0.0)
        far = bev_corners(1.0, 0.0, 4.0, 2.0, 0.0)
        # The lower-scoring box overlaps more, but it is considered second.
        assignment = assign_one_to_one([0.4, 0.9], [near, far], gt, 0.5)
        self.assertEqual(set(assignment), {0})
        self.assertEqual(assignment[0][0], 1)

    def test_one_detection_keeps_the_larger_overlap(self) -> None:
        close = bev_corners(0.0, 0.0, 4.0, 2.0, 0.0)
        other = bev_corners(1.5, 0.0, 4.0, 2.0, 0.0)
        detection = bev_corners(0.5, 0.0, 4.0, 2.0, 0.0)
        assignment = assign_one_to_one([0.8], [detection], [close, other], 0.5)
        self.assertEqual(list(assignment), [0])
        self.assertGreater(assignment[0][1], bev_iou(detection, other))

    def test_overlap_below_the_threshold_is_unmatched(self) -> None:
        gt = [bev_corners(0.0, 0.0, 4.0, 2.0, 0.0)]
        shifted = bev_corners(2.0, 0.0, 4.0, 2.0, 0.0)
        self.assertAlmostEqual(bev_iou(gt[0], shifted), 1.0 / 3.0, places=6)
        assignment = assign_one_to_one([0.9], [shifted], gt, 0.5)
        self.assertEqual(assignment, {})


if __name__ == "__main__":
    unittest.main()
