import sys

import store

conn = store.connect(sys.argv[1])
for customer, total in conn.execute("SELECT customer, SUM(amount) FROM orders GROUP BY customer"):
    print(customer, round(total, 2))
