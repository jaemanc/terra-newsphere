import unittest

from shapely.geometry import MultiPolygon, Point, box

from scripts.build_geo import adm1_parent, label_metadata


class GeographyHierarchy(unittest.TestCase):
    def test_only_parent_with_sufficient_overlap_is_accepted(self):
        parents = [("left", box(0, 0, 1, 1)), ("right", box(1, 0, 2, 1))]
        self.assertEqual(adm1_parent(box(0.1, 0.1, 0.9, 0.9), parents), "left")
        self.assertIsNone(adm1_parent(box(0.5, 0, 1.5, 1), parents))
        self.assertIsNone(adm1_parent(box(3, 3, 4, 4), parents))

    def test_map_label_is_inside_the_region_even_when_centroid_is_outside(self):
        geometry = MultiPolygon([box(0, 0, 1, 1), box(4, 0, 5, 1)])
        self.assertFalse(geometry.contains(geometry.centroid))
        label = label_metadata(geometry)
        self.assertTrue(geometry.contains(Point(label["label_longitude"], label["label_latitude"])))
