> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Congestion](./34-congestion.md) |
| 下一章 | [能量 e_es, E_es^max →](./36-energy-e-es.md) |

---

# 35. Inventory 到底什么时候算成功？

对某一个 Tag：

```text
Paging
↓
Msg1 success
↓
Msg2 success
↓
Msg3 successfully reports device ID
↓
DONE
```

之后论文假设：

> 这个 device 不再参加后续 inventory。

所以最开始：

```text
0 / 600 inventoried
```

然后：

```text
100 / 600
250 / 600
500 / 600
590 / 600
594 / 600
...
```

最终接近：

```text
600 / 600
```

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Congestion](./34-congestion.md) |
| 下一章 | [能量 e_es, E_es^max →](./36-energy-e-es.md) |
