# Ambient IoT beginner guide (single-file backup)

> **Note**: This file is a backup from before the lecture was split. Use **[content.md](./content.md)** as the entry point;
> for normal reading, open the matching chapter under `chapters/` (one `.md` per chapter, numbered 0–97 plus a Preface).

# Preface · research-fit test

Yes. More precisely, **this is not an "exam" — it is a research-fit test**.

The professor already stated the purpose very directly in the email:

> "to see if you would be a good fit for a specific topic for 499 thesis research"

In other words:

> "I will give you a small research task first, to see whether you are a good fit for this 499 thesis topic I have in mind."

So you should **not** read this as "the professor assumes I already know 3GPP / wireless / IoT, and is quizzing me on specialist knowledge." It is more likely a check of whether you can start from an unfamiliar field, read the paper, pull the model apart, write a simulation, notice problems, and then explain the results clearly.

You said this is your first time in this area. That matters a lot: **we will not teach this as if you already have a communications graduate student's default knowledge.**

I will start from the level of "I do not know any of these words yet."

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

# 1. What is IoT?

## IoT = Internet of Things

In plain English:

> **a network of everyday objects that can talk to the network.**

The ordinary Internet is:

```text
computers
phones
servers
```

talking to each other.

IoT is:

```text
temperature sensors
smart door locks
cargo tags
cameras
industrial robots
smart meters
cars
```

These "things" are also networked.

So:

$$
IoT = Internet\ of\ Things
$$

which means:

> **letting a huge number of real-world devices communicate.**

---

# 2. Then what is A-IoT?

## A-IoT = Ambient Internet of Things

Ambient here roughly means:

> IoT that lives in the environment / uses extremely low power / can run on energy around it.

The A-IoT device in this paper is very different from your phone.

Phone:

```text
large battery
CPU
Wi-Fi
5G modem
screen
a few watts of power
```

A-IoT:

```text
may have no battery
a small capacitor
an ultra-low-power chip
runs on RF energy harvesting
microwatt-level power
```

The paper is explicit: 3GPP is studying batteryless, ultra-low-power devices that work by energy harvesting and limited energy storage.

---

# 3. What does batteryless mean?

## batteryless = no conventional battery

That does not mean it needs no energy at all.

Every electronic device needs energy.

It just may not have:

> an AA cell, a lithium battery, or other long-term energy storage.

Instead it has a:

## Capacitor

In plain English:

> **a tiny energy-storage component — think of a very small cup of water.**

You can picture the capacitor as an extremely small cup.

---

Phone battery:

```text
████████████████████
a large water tank
```

Ambient IoT:

```text
█
a small cup
```

When the device works:

```text
water in the cup ↓
```

When it harvests energy from radio waves:

```text
water in the cup ↑
```

That is the core of the whole paper from here on.

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

# 5. Who is the reader?

The paper keeps saying:

## Reader

You can temporarily think of it as:

> **the "big device" that discovers and controls A-IoT devices.**

The paper says the reader can be:

* BS
* UE

---

# 6. What is a BS?

## BS = Base Station

In plain English:

> **the cell site your phone talks to — a radio station on the network side.**

When your phone connects to 4G/5G:

```text
phone ←→ base station
```

That base station is the BS.

In the paper's factory simulation:

> There are 18 base stations in the factory; one of them is chosen at a time to run inventory.

The formal paper setting is a \(120m\times60m\) indoor factory. One of the 18 BSs is responsible for inventory at a time, with transmit power 33 dBm.

---

# 7. What is a UE?

## UE = User Equipment

In plain English:

> **the end-user gadget on the network — a phone, a tablet, or another 5G terminal.**

For example:

* a phone
* a tablet
* some 5G terminals

In 3GPP language, your phone is not usually called a phone. It is often called:

> UE

So the paper says:

> Both a BS and a UE may act as an A-IoT reader.

---

# 8. What is 3GPP, really?

You will see this acronym countless times.

## 3GPP = 3rd Generation Partnership Project

Do not be fooled by "3rd Generation" in the name.

It did start out related to 3G, but today:

* 4G
* LTE
* 5G
* 5G Advanced
* later mobile generations

a large share of the standards are written by it.

A simple picture:

> **the global system for writing mobile-communication standards.**

For example, nobody can do this:

```text
Samsung ships one kind of 5G
Apple ships another kind of 5G
Qualcomm defines yet another
Ericsson defines yet another
```

Otherwise they could not talk to each other.

So you need rules:

> How are signals sent?
> How is spectrum used?
> How does a phone get onto the network?
> What is the message format?

That is standardization.

---

# 9. What are Release 18 / Release 19?

3GPP standards are not written in one shot.

They are published generation by generation.

For example:

## Release 18

Short name:

> Rel-18

That is one version stage.

Then:

## Release 19

Short name:

> Rel-19

which keeps adding new features.

This paper says:

* Release 18 did an A-IoT feasibility study
* Release 19 studies concrete solutions further

---

# 10. What is a TR?

## TR = Technical Report

In plain English:

> **a technical study document (not yet a frozen standard).**

3GPP publishes many technical documents.

This paper cites:

> TR 38.769

which means:

> a 3GPP Ambient IoT technical study report.

So when you see:

```text
TR [3]
```

do not panic.

It just means:

> Technical Report number 3 in the reference list.

---

# 11. What are Device 1 and Device 2?

The paper splits A-IoT devices into two types.

## Device 1

Extremely power-thrifty.

Peak power is about:

$$
1\mu W
$$

Here:

## \(\mu W\)

Read it as:

> microwatt — one millionth of a watt

$$
1\mu W=10^{-6}W
$$

which is:

$$
0.000001W
$$

Extremely small.

---

Device 1:

* has no carrier generator of its own
* has no strong transmitter in the usual sense
* mainly uses backscatter

Very much like RFID.

---

## Device 2

Higher power:

> a few hundred \(\mu W\)

But it is also more capable:

* amplifier
* internal CW generator
* better communication performance

The paper's target ranges are roughly:

* Device 1: 10–15 m
* Device 2: 15–50 m

---

# 12. So what on earth is CW?

## CW = Continuous Wave

In plain English:

> **a steady radio wave that is left on, without being turned into a message of its own.**

The simplest picture:

The reader keeps sending a stable wireless carrier:

```text
~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~
```

Device 1 cannot manufacture a strong radio signal by itself.

So it borrows the CW that the reader is already sending.

---

# 13. What is a carrier?

## Carrier

In plain English:

> **the high-frequency radio wave that actually travels through the air, carrying your bits.**

One of the most basic ideas in wireless communication.

For example:

You want to send:

```text
101101001
```

You do not throw those 0s and 1s into the air by themselves.

Usually you need a high-frequency wave:

$$
\cos(2\pi f_ct)
$$

That high-frequency wave is called a:

> carrier wave

or just:

> carrier

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

# 15. What is RFID?

## RFID = Radio Frequency Identification

In plain English:

> **identifying an object with a radio tag, instead of looking at it or scanning a barcode by hand.**

You have probably seen:

* access cards
* logistics labels
* store anti-theft tags
* warehouse cargo tags

The paper itself says Device 1 is similar to UHF RFID.

---

# 16. What is UHF?

## UHF = Ultra High Frequency

In plain English:

> **a slice of the radio spectrum often used by RFID tags.**

This is a range of wireless frequencies.

You do not need the exact frequencies for now.

Just remember:

> UHF RFID is a common kind of RFID system.

---

# 17. Are Ambient IoT and RFID the same thing?

Not exactly the same.

But as a beginner you can start with this picture:

> **A-IoT Device 1 ≈ a more 3GPP / cellular-flavored, RFID-like device**

Traditional RFID and 3GPP Ambient IoT:

What they share:

* ultra-low-power
* tag
* reader
* backscatter
* inventory

The difference is that Ambient IoT wants to enter the:

> 3GPP / cellular ecosystem

and combine with:

* 5G NR
* BS
* UE
* licensed spectrum
* standardized cellular procedures

---

# 18. What is NR?

## NR = New Radio

This is the official name of the 5G radio interface.

When you see:

> 5G NR

you can read it as:

> the 5G wireless-communication technology family.

It is not:

> "some new radio, any kind."

It is a proper name.

---

# 19. What are R2D and D2R?

Very simple.

## R2D = Reader-to-Device

That is:

```text
Reader → Device
```

For example:

> The reader sends paging to the tag.

---

## D2R = Device-to-Reader

That is:

```text
Device → Reader
```

For example:

> The tag replies with its own ID.

The paper discusses the two directions separately.

---

# 20. What is paging?

This is a word you must know well later in the simulation.

## Paging

You can picture it as:

> **the reader shouting at the devices: "Wake up! It is your turn to talk to me!"**

For example:

```text
Reader:

"HELLO ALL TAGS, INVENTORY STARTING!"
```

That wake-up / trigger message is:

> A-IoT paging

The paper defines it clearly:

> A-IoT paging is an R2D message used to trigger the random access procedure.

---

# 21. What is random access?

## Random Access

In plain English:

> **devices pick a chance to speak, instead of all shouting at once.**

Suppose 600 devices all want to talk to one reader.

You cannot let everyone shout at the same time:

```text
TAG1TAG27TAG384TAG503...
```

You would hear nothing.

So you need some kind of:

> access mechanism.

One method is:

> each device randomly picks an opportunity to speak.

That is random access.

---

# 22. What is CBRA?

## CBRA = Contention-Based Random Access

Break it apart:

### Contention

Several devices competing for the same resource.

### Based

Built on that idea.

### Random Access

Random access.

So:

> **random access where devices compete, instead of being given a private slot in advance.**

Meaning:

Devices are not assigned exclusive resources ahead of time.

Everyone picks at random.

So they may:

> collide.

---

# 23. What is CFRA?

## CFRA = Contention-Free Random Access

That is:

> **random access with no competition — the reader has already assigned who speaks where.**

The reader can schedule in advance:

```text
Tag A → position 1
Tag B → position 2
Tag C → position 3
```

So they will not collide.

The problem is that when inventory has just started:

> the reader does not even know which devices are nearby.

So the paper says:

> for inventory of an unknown number of devices, CBRA is typically used.

---

# 24. What does contention mean?

A simple picture:

> several people grabbing the same resource.

For example, four bathroom stalls:

```text
Stall 1
Stall 2
Stall 3
Stall 4
```

Ten people rush over at once.

If:

```text
Alice → Stall 2
Bob → Stall 2
```

then you have resource contention.

Wireless communication works the same way.

---

# 25. What is an AO?

## AO = Access Occasion

You can first think of it as:

> **A location / opportunity where a device can send Msg1.**

AOs can differ in:

* time
* frequency

For example:

```text
             Frequency
             ↑
AO3       [     ]
AO4       [     ]

AO1       [     ]
AO2       [     ]
           → Time
```

Each device randomly chooses an AO.

---

# 26. Why both time and frequency?

Because wireless resources are two-dimensional:

```text
          frequency
              ↑
              │
              │
              │
              └────────→ time
```

So two devices can:

### Differ in time

```text
Tag A: now
Tag B: later
```

or:

### Differ in frequency

```text
Tag A: frequency 1
Tag B: frequency 2
```

Either way they can avoid colliding with each other.

---

# 27. What is FDMA?

## FDMA = Frequency-Domain Multiple Access

In plain English:

> **Several devices share the medium by using different frequencies at the same time.**

That is:

> Different devices communicate at the same time on different frequencies.

For example:

```text
frequency 1 → Tag A
frequency 2 → Tag B
frequency 3 → Tag C
```

The paper notes that A-IoT can use frequency-domain multiple access.

---

# 28. What are Msg1, Msg2, and Msg3, really?

This is very important.

Do not treat them as mysterious jargon.

## Msg = Message

So:

* Msg1 = Message 1
* Msg2 = Message 2
* Msg3 = Message 3

---

The whole procedure:

```text
Reader
  |
  | Paging
  v
Tag
  |
  | Msg1
  v
Reader
  |
  | Msg2
  v
Tag
  |
  | Msg3
  v
Reader
```

---

## Paging

Reader:

> “Who is here? Come access.”

---

## Msg1

Tag:

> “I am requesting access. My temporary random ID is 12345.”

---

## Msg2

Reader:

> “Random ID 12345, I heard you.”

---

## Msg3

Tag:

> “Good. Then my real device ID is ABCDEFG.”

Once Msg3 succeeds:

> The reader has officially inventoried this device.

That is how the paper describes CBRA.

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

# 30. What is an ID?

## ID = Identifier

That is:

> An identity label.

Similar to:

* a student number
* a national ID number
* a MAC address
* a serial number

Here it means:

> “Which tag is this tag, exactly?”

---

# 31. What is a collision?

## Collision

If:

```text
Tag A → AO 3
Tag B → AO 3
```

both send Msg1 at the same time.

The reader likely cannot decode correctly.

Then you get:

> Msg1 collision.

Paper Figure 1 even draws a collision AO on purpose.

You can picture two people talking to you at once:

> “I am—I am—”

You understood neither of them.

---

# 32. What is slotted ALOHA?

You will see this name too.

## ALOHA

is a classic random access protocol.

The simplest idea:

> Whoever wants to speak tries to speak.

Slotted ALOHA adds:

> You may only start speaking at the beginning of a prescribed time slot.

So you get:

```text
slot 1
slot 2
slot 3
slot 4
```

A tag randomly picks a slot.

The paper’s Msg1 random access is based on the slotted-ALOHA idea.

You do not need its mathematical theory yet.

---

# 33. What is a slot?

## Slot = time slot

It means chopping time into small boxes.

In the paper’s parameters:

$$
1\ slot=0.5ms
$$

arXiv Table I sets it this way.

---

## What is ms?

### ms = millisecond

A millisecond.

$$
1ms=0.001s
$$

So:

$$
0.5ms=0.0005s
$$

---

# 34. What is congestion?

## Congestion

A collision is one crash.

Congestion is:

> The whole system has too many people, so there are lots of crashes.

For example:

```text
600 devices
8 AOs
```

That is clearly crowded.

Like:

> 600 cars fighting over 8 very short on-ramps.

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

# 36. Now we enter the paper’s real core: energy

Each device has energy:

$$
e_{es}
$$

Do not be afraid of this symbol.

---

## \(e_{es}\)

Meaning:

> **How much energy is still in energy storage.**

That is:

> “How much water is in the cup right now.”

---

## \(E_{es}^{max}\)

Meaning:

> Maximum capacity.

For Device 1, for example:

$$
E_{es}^{max}=500nJ
$$

---

# 37. What is an nJ?

## nJ = nanojoule

J = joule:

> The unit of energy.

nano:

$$
10^{-9}
$$

So:

$$
1nJ=10^{-9}J
$$

Device 1:

$$
500nJ
$$

That is truly very small.

---

# 38. What is the difference between power and energy?

You really need this foundation.

## Energy

is:

> “How much energy there is in total.”

Unit:

$$
J
$$

---

## Power

is:

> “How much energy is used per second.”

Unit:

$$
W
$$

The relation is:

$$
Energy=Power\times Time
$$

That is:

$$
E=P\cdot t
$$

Therefore:

$$
t=\frac{E}{P}
$$

This formula will matter a lot later.

---

For example:

$$
E=500nJ
$$

The device consumes:

$$
P=1\mu W
$$

Then in theory:

$$
t=\frac{500\times10^{-9}}
{1\times10^{-6}}
=0.5s
$$

---

# 39. What is \(P_{rx}\)?

## Rx = Receive

So:

$$
P_{rx}
$$

is:

> **The device’s power consumption while receiving a signal.**

Device 1:

$$
P_{rx}=1\mu W
$$

Device 2:

$$
P_{rx}=50\mu W
$$

---

# 40. What is \(P_{tx}\)?

## Tx = Transmit

So:

$$
P_{tx}
$$

is:

> The device’s power consumption while sending a signal.

Device 1:

$$
1\mu W
$$

Device 2:

$$
200\mu W
$$

From now on, when you see:

* Rx = receive
* Tx = transmit

let it be a reflex.

---

# 41. What is \(P_{eh}\)?

## EH = Energy Harvesting

So:

$$
P_{eh}
$$

is:

> **The power at which the device collects energy.**

The paper defines:

$$
P_{eh}=p_{in}\xi(p_{in})
$$

We will unpack this one piece at a time.

---

# 42. What is \(p_{in}\)?

## in = input / incident

$$
p_{in}
$$

is:

> **The RF power that actually arrives at the tag.**

The reader may send:

> a strong signal

but the signal fades as it travels through the air.

So:

```text
close to the reader
→ pin is higher

far from the reader
→ pin is lower
```

---

# 43. What is dBm?

In the paper you will see:

$$
-36dBm
$$

## dBm

is a very common way to write power in wireless communications.

It is a logarithmic scale.

You do not need the full formula yet, but you need a feel for it:

```text
0 dBm  = 1 mW
-10 dBm = 0.1 mW
-20 dBm = 0.01 mW
-30 dBm = 0.001 mW
```

So:

$$
-36dBm
$$

is already a very weak signal.

Note:

> More negative usually means weaker.

For example:

$$
-10dBm
$$

is much stronger than:

$$
-36dBm
$$

---

# 44. What is receiver sensitivity?

## Receiver sensitivity

In plain English:

> **How strong the signal must be at least, before the receiver can work.**

Meaning:

> The signal has to reach a certain strength before the receiver is able to operate.

The paper sets:

$$
-36dBm
$$

as receiver chain sensitivity.

Devices below this value are not included in the evaluation.

Meaning:

```text
pin < -36 dBm
→ too weak
→ do not count them
```

---

# 45. What is \(\xi(p_{in})\)?

The Greek letter:

$$
\xi
$$

is pronounced:

> xi (roughly “ksai” or “zai”).

Here it means:

## Power Conversion Efficiency

> The efficiency of turning RF energy into usable electrical energy.

For example:

$$
\xi=5\%
$$

Meaning:

You receive:

```text
100 units RF energy
```

and what actually gets stored is:

```text
5 units
```

The rest is lost.

---

# 46. Why do different tags charge at different rates?

Because:

$$
P_{eh}=p_{in}\xi(p_{in})
$$

If you are far from the reader:

$$
p_{in}\downarrow
$$

Usually:

$$
P_{eh}\downarrow
$$

So:

> Far devices charge very slowly.

Nearby:

> They charge fast.

That is why the last few devices can drag inventory time out for so long.

---

# 47. What is the ON state?

## ON state

Meaning:

> The device is on and can communicate.

It can:

* receive paging
* transmit Msg1
* receive Msg2
* transmit Msg3

But:

> It consumes energy.

The paper defines the ON state as a state that can be used for reception/transmission.

---

# 48. What is the OFF state?

## OFF state

Meaning:

> The main circuit is off.

The device:

* cannot receive
* cannot transmit
* can harvest energy

So:

```text
OFF
→ charge

ON
→ work / consume energy
```

---

# 49. What is an IC?

## IC = Integrated Circuit

In plain English:

> **The chip.**

The paper says that in the OFF state:

> IC turned off

You can read that as:

> The main chip is off and is not doing normal communication.

---

# 50. What is the turn-on threshold?

The paper writes:

$$
E_{es}^{\mathrm{up}}
$$

That is:

> **the turn-on threshold.**

For Device 1, for example:

$$
E_{es}^{\max}=500nJ
$$

The paper sets:

$$
E_{es}^{\mathrm{up}}=E_{es}^{\max}
$$

So:

> it must charge up near full before it turns on.

---

# 51. What is the turn-off threshold?

The paper writes:

$$
E_{es}^{\mathrm{low}}
$$

That is:

> **the turn-off threshold.**

The paper sets:

$$
E_{es}^{\mathrm{low}}=0.5E_{es}^{\max}
$$

Device 1:

$$
E_{es}^{\max}=500nJ
$$

So:

$$
E_{es}^{\mathrm{low}}=250nJ
$$

---

Therefore:

```text
500 nJ
↑
Turn ON

work
work
work
↓
250 nJ
Turn OFF

charge
charge
charge
↑
500 nJ
Turn ON
```

---

# 52. What is EM?

## EM = Energy-Based Monitoring

In plain English:

> **a scheme that listens for paging according to stored energy**

This is the baseline in the paper.

Baseline means:

> **the old / reference scheme you compare against.**

The EM rule is very simple:

> enough energy → ON
> energy drops too low → OFF

So:

```text
E reaches E_up
↓
ON
↓
keep monitoring
↓
E reaches E_low
↓
OFF
↓
keep charging
↓
E reaches E_up
↓
ON
```

---

# 53. What does monitoring mean?

## Monitoring

Here it means:

> **the device keeps its receiver on, waiting for the reader's paging.**

It does **not** mean:

> it is continuously transmitting data.

It means:

> burning energy, with its ears open, listening.

That is exactly what costs a lot of energy.

---

# 54. Why does the paper say EM is not good enough?

The paper lists:

* P1
* P2
* P3

Here P means:

> Problem.

---

# 55. P1: the device may need too long to charge

Suppose that when inventory starts:

the tag happens to have:

$$
e_{es}\approx E_{es}^{\mathrm{low}}
$$

that is:

> almost out of energy.

And it is also far from the reader:

$$
p_{in}\approx-36dBm
$$

so charging is extremely slow.

The paper gives an example:

> charging from the low threshold to the high threshold needs 250 nJ; at \(p_{in}=-36dBm\) and 5% efficiency, that takes about 20 seconds.

During those 20 seconds the tag:

```text
Reader: PAGING!
Tag: ...
Reader: PAGING!
Tag: ...
Reader: PAGING!
Tag: ...
```

misses everything.

---

# 56. P2: awake, but not enough energy to finish the procedure

This is more like:

> a phone with 1% battery.

It can still light up the screen.

But the moment you open a heavy game:

> it shuts off.

The tag is the same:

```text
received paging ✓

send Msg1 ✓

receive Msg2 ...

out of energy
```

Result:

> CBRA is not completed.

The paper defines this as P2.

---

# 57. P3: keep colliding, retrying, and draining the energy

Suppose the device has energy.

But:

```text
Attempt 1 → collision
Attempt 2 → collision
Attempt 3 → collision
Attempt 4 → collision
```

Each attempt still needs:

* wake up
* receive
* transmit
* wait

so it keeps burning energy.

In the end:

```text
not successful
+
out of energy
```

That is P3.

---

# 58. So the paper proposes DCM

## DCM = Duty-Cycled Monitoring

This name matters.

### Duty Cycle

Meaning:

> a device is not always ON; it periodically goes ON / OFF.

For example:

```text
ON   OFF OFF OFF   ON   OFF OFF OFF   ON
```

instead of:

```text
ON ON ON ON ON ON ON ON ON
```

So:

## Duty-Cycled Monitoring

means:

> **listening on and off, instead of staying awake the whole time.**

---

# 59. What is the core idea of DCM?

In one sentence:

> **do not drain the energy all the way to the bottom before you recharge.**

Traditional EM:

```text
500 nJ
↓
keep monitoring
↓
keep monitoring
↓
keep monitoring
↓
250 nJ
↓
OFF
↓
need to top up 250 nJ
```

DCM:

```text
500 nJ
↓
monitor only a short while
↓
still has ~470 nJ, for example
↓
sleep on purpose
↓
only need to top up 30 nJ
```

So it recovers faster.

---

# 60. Why can sleeping on purpose make things faster?

This looks counterintuitive at first.

You might think:

> “If I want to catch paging as soon as possible, shouldn’t I stay awake the whole time?”

The problem is:

staying awake:

> drains the energy.

Once it is drained:

> recovery may take more than ten seconds.

So DCM is like:

> do not pull an all-nighter until you collapse, then sleep 20 hours.

Instead:

> work a short stretch, then rest, and stay in a usable state.

---

# 61. What is the on timer?

## Timer

A timer is a countdown clock.

DCM adds:

> an on timer.

For example:

> “I stay awake at most 18 ms.”

When 18 ms is up, if paging has not arrived yet:

> I go to sleep on my own.

The paper writes this duration as:

$$
T_{\mathrm{on}}^{\mathrm{timer}}
$$

In the published version, Device 1 uses:

$$
18ms
$$

Device 2:

$$
26ms
$$

---

# 62. What is \(T_{pg}\)?

## pg = paging

$$
T_{pg}
$$

is:

> the period between two periodic pagings.

Device 1:

$$
T_{pg}=12ms
$$

Device 2:

$$
14ms
$$

---

# 63. What does periodic mean?

## Periodic

Periodic means:

> repeating on a fixed schedule.

For example:

```text
0 ms   Paging
12 ms  Paging
24 ms  Paging
36 ms  Paging
48 ms  Paging
```

that is:

> once every 12 ms.

---

# 64. What is aperiodic?

## Aperiodic

Aperiodic means:

> not on a fixed schedule.

For example:

```text
0ms
11ms
25ms
41ms
...
```

The times are not fixed.

The paper’s comparison mainly looks at periodic paging.

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

# 66. What is the sleep state?

DCM adds one more state:

## Sleep state

It is different from fully OFF.

SLEEP:

* cannot do normal Rx/Tx
* can harvest energy
* still keeps a low-power timer
* knows when it should wake

The paper says that in the sleep state the device can keep a sleep timer and harvest energy, but cannot transmit/receive.

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

# 68. What is synchronization?

## Synchronization

Synchronization means:

> lining up the clocks on both sides.

The reader knows:

```text
Paging at t=12,24,36...
```

The tag knows too.

So the tag can:

> wake only when paging is about to arrive.

This is a classic idea in communications.

---

# 69. What is \(T_{\mathrm{sl}}^{\mathrm{DCM}}\)?

## sl = sleep

So:

$$
T_{\mathrm{sl}}^{\mathrm{DCM}}
$$

is:

> the sleep duration of DCM.

---

# 70. What is \(T_{\mathrm{on}}^{\mathrm{DCM}}\)?

It is:

> how long the device stays ON inside each paging period.

The paper requires:

$$
T_{\mathrm{sl}}^{\mathrm{DCM}}+T_{\mathrm{on}}^{\mathrm{DCM}}=T_{pg}
$$

that is:

```text
one paging period
=
sleep duration
+
on duration
```

---

# 71. What is \(P_{sl}\)?

## sl = sleep

$$
P_{sl}
$$

is:

> the sleep-state power consumption.

The paper:

$$
P_{sl}=0.1\mu W
$$

and:

$$
P_{sl}<P_{rx}
$$

so sleeping uses far less energy than keeping the receiver on.

---

# 72. What has DCM solved so far?

Roughly:

### P1

It does not let energy drop too low.

So recharge is fast.

### P2

When paging arrives, remaining energy is usually still fairly high.

So there is a better chance to finish CBRA.

### P3

It does not stay ON the whole time.

So even with many retries, it is less likely to drain the energy quickly.

---

# 73. But there is still a huge problem: 600 devices

Imagine:

```text
Reader:
"PAGING!"

600 devices:
"ME!"
```

then it blows up.

So you still need:

# Congestion Control

---

# 74. What is congestion control?

It means:

> **controlling congestion.**

You cannot let every device access at the same time.

This paper mainly discusses two methods:

1. access probability
2. device grouping

---

# 75. What is access probability?

## Probability = chance of happening

The reader can tell devices:

> "You received paging, but this round you only join with a certain probability."

For example:

$$
p_{\mathrm{access}}=0.1
$$

Out of \(N=600\) devices, roughly only:

$$
N\times p_{\mathrm{access}}=600\times0.1=60
$$

join.

---

Each tag:

```text
random number
↓
0.073 < 0.1
→ access

0.51 > 0.1
→ don't access
```

Then all 600 devices will not rush into the AOs at once.

The paper states clearly that the reader can set the access probability from the congestion/occupancy of prior CBRA.

---

# 76. What is occupancy?

## Occupancy

It means:

> how full the AOs are.

For example, 8 AOs:

```text
AO1 occupied
AO2 collision
AO3 occupied
AO4 collision
AO5 occupied
AO6 empty
AO7 collision
AO8 occupied
```

From these outcomes the reader can estimate:

> whether things are too crowded right now.

---

# 77. Why does access probability also have a drawback?

Suppose:

To hear paging, a tag:

> wakes up.

That burns energy.

But paging tells it, after the random draw:

> "Do not join this round."

Then:

```text
wake up
↓
burn energy
↓
do nothing
```

That is wasteful.

That is exactly why the paper proposes device grouping.

---

# 78. What is device grouping?

## Grouping = splitting devices into groups

For example, \(N=600\) devices in \(N_g=4\) groups:

```text
Group A
Group B
Group C
Group D
```

Then:

```text
Paging 1 → Group A
Paging 2 → Group B
Paging 3 → Group C
Paging 4 → Group D
Paging 5 → Group A
```

So Group A does not need to wake up every round.

---

For example:

```text
A:      ON            ON
B:           ON            ON
C:                ON
D:                     ON
```

Then:

* collisions drop
* pointless listening drops
* energy consumption drops

Figure 4 is drawing this idea.

---

# 79. What is a low-power wake-up receiver?

Split the name:

## Receiver

A receiver.

## Wake-up

Wake up.

## Low-power

Uses very little power.

So:

> **a tiny ultra-low-power receiver whose only job is "is anyone calling me?"**

---

Think of the normal receiver as:

> a big computer.

The wake-up receiver:

> a very simple little doorbell.

You do not keep the big computer fully on all the time.

You only let:

> the doorbell listen.

Once it hears:

> "PING!"

then wake the main system.

---

The paper especially says this helps Device 2, because Device 2's normal receiver is:

$$
P_{rx}=50\mu W
$$

while a low-power wake-up receiver is:

$$
1\mu W
$$

A big difference.

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

# 81. What is OOK?

## OOK = On-Off Keying

This is a very simple modulation.

---

## What is modulation?

### Modulation = putting bits onto a wave

It means:

> how you put 0s and 1s onto a radio wave.

---

OOK is especially simple:

```text
carrier ON  → 1
carrier OFF → 0
```

So:

```text
1 0 1 1 0

ON OFF ON ON OFF
```

This is a very good fit for low-complexity devices.

The paper says R2D uses OOK.

---

# 82. What is BPSK?

## BPSK = Binary Phase Shift Keying

Also a modulation.

The difference:

> it does not use "wave present / wave absent"; it uses two phases to represent 0 and 1.

For example:

$$
0^\circ\rightarrow0
$$

$$
180^\circ\rightarrow1
$$

Knowing the name is enough for now.

Reproducing Figure 5(b) does not require you to become a BPSK expert first.

---

# 83. What is OFDM?

## OFDM = Orthogonal Frequency-Division Multiplexing

This is a very important technique in modern communications.

4G / 5G / Wi-Fi all use it heavily.

The crudest picture:

> split one high-speed signal onto many small frequency subcarriers.

Like:

```text
frequency →
|_|_|_|_|_|_|_|_|
```

The paper mentions that the reader can use an NR OFDM transmitter to generate an OOK waveform.

But for reproducing Figure 5(b):

> OFDM is not the first priority.

---

# 84. What is FDD?

## FDD = Frequency Division Duplex

The two directions of communication use different frequencies.

For example:

```text
frequency A:
BS → UE

frequency B:
UE → BS
```

Called:

> splitting uplink/downlink by frequency.

The paper mentions FDD spectrum when introducing the A-IoT spectrum.

Again:

> this is not the core of your stage-1 simulation.

---

# 85. What are uplink / downlink?

## Downlink

```text
BS → device
```

Coming down from the base station.

---

## Uplink

```text
device → BS
```

Going up from the user device.

In this paper they are close to:

* R2D
* D2R

but they are not exactly the same in every situation.

---

# 86. What is a link budget?

## Link Budget

This is an important idea in wireless communications.

In plain terms:

> how much power the transmitter sent, minus gains and losses along the way, and how much is left at the receiver.

For example:

```text
Tx power
+ antenna gain
- path loss
- obstacles
= received power
```

If the leftover is too weak:

> reception fails.

The paper uses it to discuss how far Device 1 / Device 2 coverage can reach.

---

# 87. What is a CDF?

This is a very important math idea inside Figure 5.

## CDF = Cumulative Distribution Function

Do not let the name scare you.

Suppose 100 students' scores.

You ask:

> what fraction scored ≤ 60?

Then:

> ≤70?

> ≤80?

> ≤90?

Plot that fraction:

> that is a CDF.

---

Figure 5(a) is the CDF of received power.

Roughly:

> what fraction of devices have \(p_{in}\) below a given value.

---

# 88. What does Figure 5(b) actually plot?

This is finally the thing the professor asked you to do.

Figure 5(b) is:

> **as time goes on, what fraction of Device 1 devices have already been successfully inventoried.**

Vertical axis:

```text
Successfully inventoried A-IoT device ratio (%)
```

Horizontal axis:

```text
Time (ms)
```

---

At the start:

$$
t=0
$$

maybe:

$$
0\%
$$

Then:

```text
1 second → 40%
2 seconds → 60%
5 seconds → 90%
...
```

Finally:

$$
99\%
$$

---

# 89. Why talk about 99%, not necessarily 100%?

In a communications system, at the end:

> the worst few devices

can be especially slow.

So people often use:

* 90%
* 95%
* 99%

as a completion metric.

The paper mainly compares:

> how long it takes to reach 99% inventory.

That time is the **99% inventory completion time (T99)**.

---

# 90. What do the Figure 5(b) curves mean?

The published version is more complete than the arXiv one.

The Device 1 figure includes:

* EM, aperiodic paging
* DCM, periodic paging, 1 group
* DCM, periodic paging, 4 groups

In plain English:

### EM

The old scheme. EM = Energy-Based Monitoring.

### DCM + 1 group

Duty-Cycled Monitoring, but essentially no real group separation.

### DCM + 4 groups

Duty-Cycled Monitoring, and devices are split into four groups.

---

# 91. What are the key experimental results?

Device 1:

> DCM alone does not help much.

Why?

Because:

> \(N=600\) devices are too congested, so the access probability \(p_{\mathrm{access}}\) is pushed very low.

But:

> DCM + device grouping

can cut the 99% inventory completion time (T99) by about 50%.

The published IEEE paper explains it this way.

---

Device 2:

DCM alone is already very effective.

The paper reports about:

> a 66% reduction.

Add a low-power wake-up receiver:

> up to about an 83% reduction.

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

# 93. Why did the professor ask you to reproduce Figure 5(b), not Figure 1?

Because Figure 1 is:

> a protocol illustration.

Understanding it is enough.

Figure 5(b) is:

> a simulation result.

To reproduce it, you must really understand:

* device state
* energy
* paging
* random access
* AO
* collision
* retry
* DCM
* grouping
* timing
* statistics

So this is a very good research-fit test.

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

# 95. So do not panic that "I know nothing yet"

It is better to treat the whole task as:

```text
Stage 1
learn the language

Stage 2
understand the system

Stage 3
understand the formulas

Stage 4
draw the system as a state machine

Stage 5
turn the state machine into a simulation

Stage 6
reproduce Figure 5(b)

Stage 7
explain why the result looks that way
```

**Do not skip straight to stage 5.**

If you ask me for the code right now, I would actually think that is not the best move.

Because if the professor later asks:

> Why did you model it this way?

you can easily have nothing to say.

---

# 96. A first vocabulary table of the acronyms you most need

You do not have to memorize them all today, but you should recognize them when they show up:

| Acronym | Full name | Gloss |
| --- | --- | --- |
| IoT | Internet of Things | networked everyday objects |
| A-IoT | Ambient IoT | ultra-low-power / batteryless IoT devices |
| 3GPP | 3rd Generation Partnership Project | the mobile-communications standards body |
| BS | Base Station | cell tower / reader side |
| UE | User Equipment | phone / terminal |
| RF | Radio Frequency | wireless radio |
| RFID | Radio Frequency Identification | radio tags |
| UHF | Ultra High Frequency | a high radio-frequency band |
| CW | Continuous Wave | a continuous carrier |
| NR | New Radio | 5G radio interface |
| R2D | Reader-to-Device | Reader → Device |
| D2R | Device-to-Reader | Device → Reader |
| CBRA | Contention-Based Random Access | devices compete to send |
| CFRA | Contention-Free Random Access | reserved, no competition |
| AO | Access Occasion | one Msg1 transmit opportunity |
| ID | Identifier | identity number |
| EM | Energy-Based Monitoring | baseline: listen whenever energy is high |
| DCM | Duty-Cycled Monitoring | intermittent listening (sleep to save energy) |
| Rx | Receive | receive |
| Tx | Transmit | transmit |
| EH | Energy Harvesting | collecting energy from RF |
| IC | Integrated Circuit | the chip |
| CDF | Cumulative Distribution Function | "what fraction is ≤ this value?" |
| OOK | On-Off Keying | carrier on = 1, off = 0 |
| BPSK | Binary Phase Shift Keying | two phases encode 0 and 1 |
| OFDM | Orthogonal Frequency-Division Multiplexing | many small frequency subcarriers |
| FDMA | Frequency-Domain Multiple Access | split users by frequency |
| FDD | Frequency Division Duplex | uplink and downlink on different frequencies |
| TR | Technical Report | a 3GPP technical report |

These ~30 already cover most of the paper's "scary-looking" terms.

---

# 97. What level should you be at now?

Right now you are **not** required to know:

$$
OFDM
$$

derivations.

You are also not required to know:

$$
BPSK
$$

error rates.

You are not even required, for now, to know:

> the 3GPP NR protocol stack.

Stage 1 only needs you to answer this, without looking at the paper:

> "This paper studies how a reader can quickly inventory hundreds of batteryless A-IoT tags that rely on RF energy harvesting. Traditional EM (Energy-Based Monitoring) lets a device drain its energy too low, so it stays unavailable for a long time; DCM (Duty-Cycled Monitoring) uses duty cycling to keep a higher energy level, and together with access probability and device grouping it controls congestion, which reduces inventory completion time."

If you truly understand that sentence, rather than reciting it:

> **you have passed stage 1.**

---

From here, learn it as a course, instead of stuffing in still more at once.

**The next best step is to close-read this paper figure by figure:**

1. Start with [Figure 1](./figures/figure-01-cbra.md): take paging, Msg1, AO, collision, Msg2, and Msg3 apart;
2. Then [Figure 2](./figures/figure-02-em-energy.md), [Figure 3](./figures/figure-03-em-vs-dcm.md), [Figure 4](./figures/figure-04-grouping.md);
3. Only then enter the professor's required [Figure 5(b)](./figures/figure-05b-inventory.md).

That way, when you reach Figure 5(b), you will know **how every point on the curve is produced**, not only that "orange is faster than purple."

→ **[Open the figure close-reading TOC](./figures/README.md)**

---
