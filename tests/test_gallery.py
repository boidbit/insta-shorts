"""The page's reel gallery: every reel (all release pages), shown a dozen at a time, each with a delete button.
python -m unittest"""
import os
import unittest

PAGE = os.path.join(os.path.dirname(__file__), "..", "index.html")


class Gallery(unittest.TestCase):
    def setUp(self):
        with open(PAGE, encoding="utf-8") as f:
            self.page = f.read()

    def test_all_reels_are_fetched_page_by_page(self):
        self.assertIn("function fetchAllReels", self.page)
        self.assertIn("per_page=100", self.page)
        self.assertNotIn(".gallery.short .reel:nth-child", self.page)   # no hidden cap any more

    def test_count_and_more(self):
        self.assertIn('id="galleryCount"', self.page)
        self.assertIn("function showMoreReels", self.page)

    def test_delete_removes_the_release_and_its_tag(self):
        self.assertIn("function deleteReel", self.page)
        self.assertIn("/git/refs/tags/", self.page)
        self.assertIn('method:"DELETE"', self.page.replace(" ", ""))
        self.assertIn("confirm(", self.page)


if __name__ == "__main__":
    unittest.main()
