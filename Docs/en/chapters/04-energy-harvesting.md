> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Batteryless + capacitor cup analogy](./03-batteryless.md) |
| Next | [Reader (BS / UE) →](./05-reader.md) |

---

# 4. What is energy harvesting?

## Energy Harvesting

In plain English:

> **collecting energy from the outside world.**

The device obtains energy from its surroundings.

For example:

* sunlight
* vibration
* temperature difference
* RF radio waves

This paper is mainly about:

# RF Energy Harvesting

---

## What is RF?

### RF = Radio Frequency

In plain English:

> **radio waves.**

A simple picture:

> wireless signals.

Wi-Fi, 5G, Bluetooth, and broadcast radio all involve RF signals.

The reader sends RF into the air:

```text
Reader
   )))))))))))))) RF wave
                 ↓
                Tag
```

The tag's antenna receives a little energy:

```text
RF signal
   ↓
antenna
   ↓
energy harvesting circuit
   ↓
capacitor
```

So the capacitor is charged a little.

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Batteryless + capacitor cup analogy](./03-batteryless.md) |
| Next | [Reader (BS / UE) →](./05-reader.md) |
