> **导航** · [逐图目录](./README.md) · [总目录 content.md](../content.md)

| | |
|---|---|
| 上一图 | [← Figure 3：EM vs DCM](./figure-03-em-vs-dcm.md) |
| 下一图 | [Figure 5(a)：Received Power CDF →](./figure-05a-cdf.md) |

---

# Figure 4：Device Grouping

Figure 4 在画：

> 不要让所有 Device 每轮都醒着抢同一波 Paging。

## 核心画面

```text
Paging 1 → Group A
Paging 2 → Group B
Paging 3 → Group C
Paging 4 → Group D
Paging 5 → Group A
...
```

## 为什么需要它？

只有 access probability 时：

```text
醒了 → 耗电听 Paging → 随机抽签说“这轮别来” → 电白花了
```

Grouping：

- 降低同一轮 contention
- 减少无意义 listening
- 让 access probability 不必压得那么极端

## 和 Figure 5(b) 的关系

Device 1：

> 单独 DCM 改善有限；**DCM + 4 groups** 才明显把 99% completion time 大约砍半。

因为瓶颈从“没电”变成了“太挤”。

## 过关标准

能解释：

> 为什么 600 个 Device、8 个 AO 时，只靠 DCM 不够？


---

> **导航**
>
> - [↑ 逐图目录](./README.md)
> - [↑ 总目录](../content.md)
> - [← Figure 3：EM vs DCM](./figure-03-em-vs-dcm.md)
> - [Figure 5(a)：Received Power CDF →](./figure-05a-cdf.md)
