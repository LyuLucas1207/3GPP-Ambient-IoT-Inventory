> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Why reproduce 5(b), not Fig. 1](./93-why-reproduce-5b.md) |
| Next | [Learning stages 1–7 (do not skip to code) →](./95-learning-stages.md) |

---

# 94. Which skills is he actually testing?

I think there are roughly six layers.

### Layer 1: can you read an unfamiliar paper?

You do not understand it yet:

> that is completely normal.

The real question is:

> can you figure it out bit by bit.

---

### Layer 2: can you turn text into a model?

The paper writes:

> device enters off state when energy falls below threshold.

You need to turn that into:

```python
if energy <= E_low:
    state = OFF
```

---

### Layer 3: can you write the protocol as an algorithm?

For example:

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

### Layer 4: can you handle randomness?

Because:

* device received power differs
* AO is chosen at random
* access probability is random
* device grouping
* collisions

So this is not a deterministic homework problem.

---

### Layer 5: can you debug?

Your first result will likely:

> look nothing like Figure 5(b).

Then you need to ask:

> how is initial energy set?

> is the DCM transition correct?

> does a device leave after a successful inventory?

> is the dBm-to-watt conversion correct?

That is research.

---

### Layer 6: can you explain?

In the end the professor may not really ask:

> "How many lines of Python did you write?"

but:

> "Why does DCM alone not improve device-1 performance?"

You need to say:

> Because heavy contention leads to a low access probability; grouping reduces the number of devices monitoring/contending for a given paging opportunity.

That ability to **explain the result** matters. The published paper explains Device 1 this way.

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Why reproduce 5(b), not Fig. 1](./93-why-reproduce-5b.md) |
| Next | [Learning stages 1–7 (do not skip to code) →](./95-learning-stages.md) |
