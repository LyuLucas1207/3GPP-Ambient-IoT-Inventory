> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Congestion](./34-congestion.md) |
| Next | [Energy \(e_{es}\), \(E_{es}^{\max}\) →](./36-energy-e-es.md) |

---

# 35. When does inventory actually count as success?

For a given tag:

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

After that the paper assumes:

> This device no longer takes part in later inventory.

So at the start:

```text
0 / 600 inventoried
```

Then:

```text
100 / 600
250 / 600
500 / 600
590 / 600
594 / 600
...
```

Eventually approaching:

```text
600 / 600
```

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Congestion](./34-congestion.md) |
| Next | [Energy \(e_{es}\), \(E_{es}^{\max}\) →](./36-energy-e-es.md) |
