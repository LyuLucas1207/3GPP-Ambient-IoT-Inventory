> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Drawback of access probability](./77-access-probability-drawback.md) |
| Next | [Low-power wake-up receiver (doorbell) →](./79-wakeup-receiver.md) |

---

# 78. What is device grouping?

## Grouping = splitting devices into groups

For example, \(N=600\) devices in \(N_g=4\) groups:

```text
Group A
Group B
Group C
Group D
```

Then:

```text
Paging 1 → Group A
Paging 2 → Group B
Paging 3 → Group C
Paging 4 → Group D
Paging 5 → Group A
```

So Group A does not need to wake up every round.

---

For example:

```text
A:      ON            ON
B:           ON            ON
C:                ON
D:                     ON
```

Then:

* collisions drop
* pointless listening drops
* energy consumption drops

Figure 4 is drawing this idea.

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Drawback of access probability](./77-access-probability-drawback.md) |
| Next | [Low-power wake-up receiver (doorbell) →](./79-wakeup-receiver.md) |
