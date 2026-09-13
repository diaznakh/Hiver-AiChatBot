import unittest

from support_agent.ui import render_page


class UITests(unittest.TestCase):
    def test_page_renders_without_interpreting_css_braces(self) -> None:
        page = render_page("hello", "<section>result</section>")
        self.assertIn("hello", page)
        self.assertIn("<section>result</section>", page)
        self.assertIn("AmazonHelp AI support agent", page)
        self.assertIn("Generate response", page)
        self.assertIn(".card {", page)


if __name__ == "__main__":
    unittest.main()
