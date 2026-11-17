import sqlite3
import unittest

import store


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, amount REAL)")
        self.conn.executemany("INSERT INTO orders VALUES (?, ?, ?)", [(1, "ann", 10.0), (2, "bob", 5.5)])

    def test_get_order(self):
        self.assertEqual(store.get_order(self.conn, 1), (1, "ann", 10.0))


if __name__ == "__main__":
    unittest.main()
