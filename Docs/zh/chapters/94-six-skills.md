> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← 为什么复现 5(b) 不是 Fig.1](./93-why-reproduce-5b.md) |
| 下一章 | [学习阶段 1–7（别跳代码） →](./95-learning-stages.md) |

---

# 94. 他实际上在测试你哪些能力？

我认为大概有六层。

### 第一层：能不能读陌生论文

你现在不懂：

> 完全正常。

关键是：

> 能不能一点一点搞懂。

---

### 第二层：能不能把文字变成模型

论文写：

> device enters off state when energy falls below threshold。

你需要转换成：

```python
if energy <= E_low:
    state = OFF
```

---

### 第三层：能不能把 protocol 写成 algorithm

例如：

```text
Paging
↓
which devices are awake?
↓
which devices may access?
↓
choose AO
↓
detect collision
↓
Msg2
↓
Msg3
↓
success
```

---

### 第四层：能不能处理 randomness

因为：

* device received power 不同
* AO 随机选择
* access probability 随机
* device grouping
* collisions

所以这不是 deterministic homework。

---

### 第五层：能不能 debug

你第一次结果很可能：

> 完全不像 Figure 5(b)。

然后需要问：

> initial energy 怎么设？

> DCM transition 对吗？

> device after successful inventory 是否退出？

> power 的 dBm 转 watt 对吗？

这才是 research。

---

### 第六层：能不能解释

最后教授可能真正问你的不是：

> “你的 Python 有多少行？”

而是：

> “Why does DCM alone not improve device-1 performance?”

你需要说：

> Because heavy contention leads to a low access probability; grouping reduces the number of devices monitoring/contending for a given paging opportunity.

这个“解释结果”的能力很重要。正式论文就是这么解释 Device 1 的。

---

> **导航** · [目录 content.md](../content.md) · [Docs 首页](../README.md)

| | |
|---|---|
| 上一章 | [← 为什么复现 5(b) 不是 Fig.1](./93-why-reproduce-5b.md) |
| 下一章 | [学习阶段 1–7（别跳代码） →](./95-learning-stages.md) |
