> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Aperiodic](./64-aperiodic.md) |
| Next | [Sleep state →](./66-sleep-state.md) |

---

# 65. Why \(T_{\mathrm{on}}^{\mathrm{timer}}\ge T_{pg}\)?

Because after the device wakes up:

> it should stay awake long enough to have a chance to meet one paging.

Suppose paging comes every:

$$
12ms
$$

and you only stay awake:

$$
2ms
$$

then very likely:

```text
wake
sleep

        paging
```

you miss it completely.

So the paper says it is best to have:

$$
T_{\mathrm{on}}^{\mathrm{timer}}\ge T_{pg}
$$

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Aperiodic](./64-aperiodic.md) |
| Next | [Sleep state →](./66-sleep-state.md) |
