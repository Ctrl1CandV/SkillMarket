"""AA 分账：把一笔账按人数均分到分，余下的分从第一个人开始逐个多付一分。"""


def split(total: float, n: int) -> list[float]:
    if n <= 0:
        raise ValueError("人数必须大于 0")
    cents = int(total * 100)
    base, rem = divmod(cents, n)
    return [(base + (1 if i < rem else 0)) / 100 for i in range(n)]
