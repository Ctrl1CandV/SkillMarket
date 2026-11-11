# Python 中 list 和 tuple 的区别

| 特性 | list | tuple |
|------|------|-------|
| 可变性 | 可变（mutable），可以增删改 | 不可变（immutable） |
| 语法 | `[1, 2, 3]` | `(1, 2, 3)` |
| 内存/性能 | 较大、较慢 | 较小、较快（更省内存） |
| 哈希性 | 不可哈希，不能做 dict 的 key / set 元素 | 若元素都可哈希，则可哈希 |
| 用途 | 同类数据集合，需频繁修改 | 异构数据记录、固定常量、函数返回多值 |
| 方法 | 有 append/insert/remove/sort 等 | 只有 count/index |

## 常见示例

```python
lst = [1, 2, 3]
lst[0] = 100        # OK
lst.append(4)       # OK

tup = (1, 2, 3)
# tup[0] = 100      # TypeError
# tup.append(4)     # AttributeError

# 元组可作 dict key
d = {(1, 2): "point"}     # OK
# d[[1, 2]] = "x"         # TypeError: unhashable type: 'list'

# 单元素元组要加逗号
one = (1,)   # 元组
not_tuple = (1)  # 其实是 int
```

## 需要注意的坑
- `tuple` 的"不可变"是**浅层**的：如果里面装着 list，list 的内容仍可修改。
  ```python
  t = (1, [2, 3])
  t[1].append(4)   # 合法 → (1, [2, 3, 4])
  ```
- 解包、函数返回多值、`namedtuple` 都是 tuple 的典型场景。

简单记：**要改就用 list，不改就用 tuple**（更省内存、更安全、可作 key）。
