> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Sleep state](./66-sleep-state.md) |
| Next | [Synchronization →](./68-synchronization.md) |

---

# 67. Why does the first paging matter so much?

Before the first one:

the tag does not know:

> whether the reader has started inventory.

So it can only:

```text
wake
listen
sleep
wake
listen
sleep
```

But after it receives the first paging:

> “Ah! Now I know inventory has started, and paging comes every 12 ms.”

Then later it can:

```text
       paging
         ↓
sleep sleep ON
         ↓
       paging
         ↓
sleep sleep ON
```

This is called:

# Synchronization

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Sleep state](./66-sleep-state.md) |
| Next | [Synchronization →](./68-synchronization.md) |
