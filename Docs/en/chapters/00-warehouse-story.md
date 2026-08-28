> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Preface · research-fit test](./00-research-fit.md) |
| Next | [IoT →](./01-iot.md) |

---

# 0. First, remember just one story

For now, ignore formulas. Ignore 3GPP.

Imagine a large warehouse.

Inside the warehouse there are:

> **600 extremely small electronic tags.**

For example, one sticker on each crate.

These tags are similar to RFID tags, but they are ultra-low-power devices inside a future 5G/6G network.

The catch:

> **They do not have a normal battery.**

They can only collect a tiny amount of energy from radio waves in the air.

Then there is a "big machine" in the warehouse:

> **Reader**

It wants to know:

> "Which 600 tags are in the warehouse right now?"

So it calls out:

> "Is anyone there?"

The tags answer:

> "I am #382!"

> "I am #157!"

> "I am #491!"

until the reader has registered everyone.

That process is called:

# Inventory

In plain English:

> **stock-taking / device discovery / finding the identity of every nearby device.**

The whole paper studies one question:

> **How can these 600 batteryless little tags all be found by the reader, faster?**

The paper studies indoor inventory. Devices depend on energy harvesting, so they may temporarily be unable to communicate because they are short of energy.

Put this one story in your head first.

---

> **Nav** · [TOC content.md](../content.md) · [Docs home](../README.md)

| | |
|---|---|
| Previous | [← Preface · research-fit test](./00-research-fit.md) |
| Next | [IoT →](./01-iot.md) |
