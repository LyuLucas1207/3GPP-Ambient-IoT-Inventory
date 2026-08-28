> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Low-power wake-up receiver (doorbell)](./79-wakeup-receiver.md) |
| Next | [OOK + modulation →](./81-ook-modulation.md) |

---

# 80. What is a preamble?

The paper says paging carries a:

> preamble.

## Preamble = a known lead-in sequence

Before the real message, send a known pattern first:

```text
101010101...
```

The device knows:

> "If I detect this pattern, paging is about to arrive."

A lot like knocking on a door:

```text
knock-knock—knock-knock-knock
```

People inside hear that special rhythm:

> "Ah, it's one of us."

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Low-power wake-up receiver (doorbell)](./79-wakeup-receiver.md) |
| Next | [OOK + modulation →](./81-ook-modulation.md) |
