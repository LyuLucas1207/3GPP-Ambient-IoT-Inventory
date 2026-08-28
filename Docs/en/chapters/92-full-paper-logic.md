> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Key results: 50% / 66% / 83%](./91-key-conclusions.md) |
| Next | [Why reproduce 5(b), not Fig. 1 →](./93-why-reproduce-5b.md) |

---

# 92. So the whole paper is really one logic chain

You should build this mental picture first:

```text
A-IoT device has no battery
        ↓
must use energy harvesting
        ↓
sometimes has no energy
        ↓
no energy → cannot receive paging
        ↓
inventory gets slower
        ↓
traditional EM drains energy too low
        ↓
needs a long recharge
        ↓
propose DCM
        ↓
do not stay awake all the time
        ↓
keep more energy
        ↓
easier to join inventory
```

But:

```text
600 devices
   ↓
access at the same time
   ↓
congestion / collision
   ↓
need access probability
```

But:

```text
access probability
   ↓
many devices wake up but cannot transmit
   ↓
waste energy
   ↓
device grouping
```

Finally:

```text
DCM
+
access probability
+
device grouping
+
optional low-power wake-up receiver
        ↓
faster inventory
```

That is the whole paper.

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Key results: 50% / 66% / 83%](./91-key-conclusions.md) |
| Next | [Why reproduce 5(b), not Fig. 1 →](./93-why-reproduce-5b.md) |
