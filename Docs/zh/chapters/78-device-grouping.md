> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Access Probability 的缺点](./77-access-probability-drawback.md) |
| 下一章 | [Low-Power Wake-Up Receiver（门铃） →](./79-wakeup-receiver.md) |

---

# 78. Device Grouping 是什么？

## Grouping = 分组

例如 600 个设备分四组：

```text
Group A
Group B
Group C
Group D
```

然后：

```text
Paging 1 → Group A
Paging 2 → Group B
Paging 3 → Group C
Paging 4 → Group D
Paging 5 → Group A
```

那么 Group A 不需要每轮都醒。

---

例如：

```text
A:      ON            ON
B:           ON            ON
C:                ON
D:                     ON
```

于是：

* collision 减少
* 无意义 listening 减少
* energy 消耗降低

Figure 4 就是在画这个思想。

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← Access Probability 的缺点](./77-access-probability-drawback.md) |
| 下一章 | [Low-Power Wake-Up Receiver（门铃） →](./79-wakeup-receiver.md) |
