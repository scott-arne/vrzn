import unittest


class TestVersion(unittest.TestCase):
    def test_version(self):
        """
        Example test
        """
        from vrzn import __version__
        self.assertIsNotNone(__version__)
