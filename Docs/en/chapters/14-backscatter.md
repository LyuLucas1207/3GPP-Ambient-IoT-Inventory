> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Carrier](./13-carrier.md) |
| Next | [RFID →](./15-rfid.md) |

---

# 14. What is backscatter?

This is a very important idea in Ambient IoT / RFID.

## Backscatter communication

In plain English:

> **talking by reflecting someone else's radio wave, instead of generating your own.**

An ordinary phone:

```text
the phone generates an RF signal
→ amplifier
→ antenna
→ sends it out
```

But an ultra-low-power tag:

> does not have the energy to do that.

So it uses the radio wave the reader is already sending.

Reader:

```text
))))))))))))))))
```

The tag changes the electrical properties of its own antenna:

```text
strong reflection
weak reflection
strong reflection
weak reflection
```

The reader detects that change:

```text
1 0 1 0
```

That is:

> backscatter.

It is a lot like:

> you do not have a flashlight, but someone else shines one at you; you send Morse code by changing how a mirror reflects the light.

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Carrier](./13-carrier.md) |
| Next | [RFID →](./15-rfid.md) |
