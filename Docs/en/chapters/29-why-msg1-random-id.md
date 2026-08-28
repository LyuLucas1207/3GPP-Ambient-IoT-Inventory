> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Msg1 / Msg2 / Msg3 procedure](./28-msg1-2-3.md) |
| Next | [ID →](./30-id.md) |

---

# 29. Why does Msg1 use a random ID?

The paper gives an example:

> 16-bit random ID.

Because at the start the reader still does not know:

> who you are.

The tag first generates a short temporary ID:

```text
101001101011...
```

It uses that to finish the initial handshake.

Then Msg3 reports the real device ID.

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Msg1 / Msg2 / Msg3 procedure](./28-msg1-2-3.md) |
| Next | [ID →](./30-id.md) |
