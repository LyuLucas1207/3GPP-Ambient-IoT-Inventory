# Ambient IoT 入门指南（单文件备份）

> **注意**：本文件是讲义拆分前的备份。请以 **[content.md](./content.md)** 为入口；
> 正式阅读请打开 `chapters/` 下对应章节（一章一个 `.md`，编号 0–97 + Preface）。

---

# 研究适配度测试（Preface）

对。更准确地说，**这不是“考试题”，而是一个 research-fit test（研究适配度测试）**。

教授在邮件里其实已经把目的说得很直接了：

> “to see if you would be a good fit for a specific topic for 499 thesis research”

意思就是：

> “我先给你一个小型研究任务，看看你是否适合做我手上的这个 499 thesis topic。”

所以你现在**不应该把它理解成“教授默认我已经懂 3GPP / wireless / IoT，然后考我专业知识”**。更可能是在看你能不能从一个陌生领域开始，自己把论文读懂、把模型拆出来、写 simulation、发现问题、最后清楚地解释结果。

而你说自己第一次进入这个领域，这一点反而非常重要：**我们接下来不能用通信专业研究生默认知识来讲。**

我下面就真的从“这些词我一个都不知道”的程度开始。

---

---

# 0. 先只记住一个故事

先完全不要管公式，不要管 3GPP。

想象一个大型仓库。

仓库里有：

> **600 个非常非常小的电子标签。**

比如每个货箱上贴一个。

这些标签类似 RFID 标签，但是是未来 5G/6G 网络体系里的超低功耗设备。

问题是：

> **它们没有正常的电池。**

它们只能从空气中的无线电波里面收集一点点能量。

然后仓库里面有一个“大机器”：

> **Reader（读写器）**

它想知道：

> “仓库里现在到底有哪 600 个标签？”

所以它喊：

> “有人吗？”

标签回答：

> “我是 #382！”

> “我是 #157！”

> “我是 #491！”

直到 reader 把大家都登记完成。

这个过程叫：

# Inventory

也就是：

> **盘点 / 设备发现 / 把附近所有设备身份找出来。**

整篇论文其实就研究一个问题：

> **怎样让这 600 个没电池的小标签，更快地全部被 reader 找到？**

论文研究的正是 indoor inventory，而设备依赖 energy harvesting，因此可能因为缺电而暂时无法通信。

你现在先把这一个故事装进脑子。

---

# 1. IoT 是什么？

## IoT = Internet of Things

中文通常翻译：

> **物联网**

普通 Internet 是：

```text
电脑
手机
服务器
```

互相联网。

IoT 则是：

```text
温度传感器
智能门锁
货物标签
摄像头
工业机器人
智能电表
汽车
```

这些“东西”也联网。

所以：

$$
IoT = Internet\ of\ Things
$$

就是：

> **让大量现实世界里的设备能够通信。**

---

# 2. 那 A-IoT 又是什么？

## A-IoT = Ambient Internet of Things

Ambient 在这里大概可以理解为：

> 环境中的 / 极低功耗的 / 可以依靠周围能量工作的 IoT。

这篇论文里的 A-IoT device 和你的手机差别非常大。

手机：

```text
大电池
CPU
Wi-Fi
5G modem
屏幕
几瓦功耗
```

A-IoT：

```text
可能没有电池
一个小电容
极低功耗芯片
靠 RF energy harvesting
微瓦级功耗
```

论文明确说，3GPP 研究的是 batteryless、ultra-low-power 的设备，它们依靠 energy harvesting 和有限的 energy storage 工作。

---

# 3. batteryless 是什么意思？

## batteryless = 没有传统电池

不是说它完全不需要能量。

任何电子设备都需要能量。

只是它可能没有：

> AA 电池、锂电池之类长期储能。

而是有一个：

## Capacitor

中文：

> **电容**

你可以把电容想成一个非常非常小的水杯。

---

手机电池：

```text
████████████████████
很大的水箱
```

Ambient IoT：

```text
█
一个小杯子
```

设备工作的时候：

```text
杯子里的水 ↓
```

从无线电波收集能量：

```text
杯子里的水 ↑
```

这就是后面整篇论文的核心。

---

# 4. Energy Harvesting 是什么？

## Energy Harvesting

直译：

> **能量采集**

就是设备从外界获得能量。

比如：

* 太阳能
* 振动
* 温差
* RF 无线电波

这篇 paper 主要讲：

# RF Energy Harvesting

---

## RF 是什么？

### RF = Radio Frequency

中文：

> **射频**

简单理解就是：

> 无线电信号。

Wi-Fi、5G、蓝牙、广播，都涉及 RF 信号。

Reader 在空气里发 RF：

```text
Reader
   )))))))))))))) RF wave
                 ↓
                Tag
```

Tag 的天线收到一点能量：

```text
RF signal
   ↓
antenna
   ↓
energy harvesting circuit
   ↓
capacitor
```

于是 capacitor 被充一点电。

---

# 5. Reader 是谁？

论文一直说：

## Reader

你可以暂时理解成：

> **负责发现、控制 A-IoT device 的“大设备”。**

论文说 reader 可以是：

* BS
* UE

---

# 6. BS 是什么？

## BS = Base Station

中文：

> **基站**

你平时手机连接 4G/5G：

```text
手机 ←→ 基站
```

那个基站就是 BS。

在论文的 factory simulation 里面：

> 工厂里有 18 个 base stations，一次选一个进行 inventory。

正式论文设定是一个 \(120m\times60m\) 的室内工厂，18 个 BS 中一次一个负责 inventory，发射功率 33 dBm。

---

# 7. UE 是什么？

## UE = User Equipment

中文：

> **用户设备**

比如：

* 手机
* 平板
* 某些 5G terminal

在 3GPP 语言里，你的手机不是通常叫 phone，而经常叫：

> UE

所以论文说：

> BS 和 UE 都可能充当 A-IoT reader。

---

# 8. 3GPP 到底是什么？

这个缩写你以后会看见无数次。

## 3GPP = 3rd Generation Partnership Project

不要被名字里的 “3rd Generation” 骗了。

它最开始确实跟 3G 有关，但现在：

* 4G
* LTE
* 5G
* 5G Advanced
* 后续移动通信

大量标准都由它制定。

你可以简单理解成：

> **全球移动通信标准制定组织体系。**

比如大家不能：

```text
Samsung 自己发一种 5G
Apple 自己发一种 5G
Qualcomm 自己定义另一种
Ericsson 再定义另一种
```

否则彼此没法通信。

所以需要规则：

> 信号怎么发？
> 频率怎么用？
> 手机怎样接入？
> 消息格式是什么？

这些就是 standardization。

---

# 9. Release 18 / Release 19 是什么？

3GPP 的标准不是一次写完。

它一代一代发布。

比如：

## Release 18

简称：

> Rel-18

是某一个版本阶段。

然后：

## Release 19

简称：

> Rel-19

继续加入新的功能。

这篇论文说：

* Release 18 做 A-IoT feasibility study
* Release 19 进一步研究具体 solutions

---

# 10. TR 是什么？

## TR = Technical Report

中文：

> **技术报告**

3GPP 会有很多技术文档。

这篇 paper 引用了：

> TR 38.769

也就是：

> 3GPP 的某份 Ambient IoT 技术研究报告。

因此你看到：

```text
TR [3]
```

不要怕。

就是：

> Reference 3 那份 Technical Report。

---

# 11. Device 1 和 Device 2 是什么？

论文把 A-IoT device 分成两个类型。

## Device 1

非常省电。

峰值功耗大约：

$$
1\mu W
$$

这里：

## \(\mu W\)

读作：

> microwatt，微瓦

$$
1\mu W=10^{-6}W
$$

也就是：

$$
0.000001W
$$

非常非常小。

---

Device 1：

* 没有自己的 carrier generator
* 没有正常意义上的强 transmitter
* 主要靠 backscatter

很像 RFID。

---

## Device 2

功耗更高：

> 几百 \(\mu W\)

但它能力也更强：

* amplifier
* internal CW generator
* 更好的通信性能

论文给出的目标距离大概是：

* Device 1：10–15 m
* Device 2：15–50 m

---

# 12. CW 又是什么鬼？

## CW = Continuous Wave

中文一般叫：

> **连续波**

最简单理解：

Reader 不断发一个稳定的无线载波：

```text
~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~
```

Device 1 没能力自己制造强无线信号。

所以它借用 Reader 发来的 CW。

---

# 13. Carrier 是什么？

## Carrier = 载波

无线通信最基础的概念之一。

例如：

你要传：

```text
101101001
```

不是把这些 0 和 1 凭空扔进空气。

通常需要一个高频波：

$$
\cos(2\pi f_ct)
$$

这个高频波就叫：

> carrier wave

简称：

> carrier

---

# 14. Backscatter 是什么？

这是 Ambient IoT / RFID 里非常重要的概念。

## Backscatter communication

中文：

> **反向散射通信**

普通手机：

```text
手机自己产生 RF signal
→ amplifier
→ antenna
→ 发出去
```

但是 ultra-low-power tag：

> 没电做这个。

于是它使用 Reader 已经发来的无线波。

Reader：

```text
))))))))))))))))
```

Tag 改变自己天线的电气特性：

```text
反射强
反射弱
反射强
反射弱
```

Reader 检测这个变化：

```text
1 0 1 0
```

这就是：

> backscatter。

非常像：

> 你没有手电筒，但别人拿手电照你；你用镜子改变反射方式来发送 Morse code。

---

# 15. RFID 是什么？

## RFID = Radio Frequency Identification

中文：

> **射频识别**

你应该见过：

* 门禁卡
* 物流标签
* 商场防盗标签
* 仓库货物标签

这篇论文自己就说 Device 1 类似 UHF RFID。

---

# 16. UHF 是什么？

## UHF = Ultra High Frequency

中文：

> **特高频**

这是无线频谱的一段范围。

这里你暂时不用研究具体频率。

只要知道：

> UHF RFID 是一种常见 RFID 系统。

---

# 17. 那 Ambient IoT 和 RFID 是不是一个东西？

不是完全一样。

但是你作为新人可以先这样理解：

> **A-IoT Device 1 ≈ 更加 3GPP / cellular 化的高级 RFID-like device**

传统 RFID 和 3GPP Ambient IoT：

共同点：

* ultra-low-power
* tag
* reader
* backscatter
* inventory

区别在于：

Ambient IoT 希望进入：

> 3GPP / cellular ecosystem

和：

* 5G NR
* BS
* UE
* licensed spectrum
* standardized cellular procedures

结合。

---

# 18. NR 是什么？

## NR = New Radio

这是 5G 无线接口的正式名字。

你看到：

> 5G NR

可以理解成：

> 5G 的无线通信技术体系。

不是：

> “新的 radio 随便一种”。

是专有名词。

---

# 19. R2D 和 D2R 是什么？

非常简单。

## R2D = Reader-to-Device

就是：

```text
Reader → Device
```

例如：

> Reader 发 paging 给 tag。

---

## D2R = Device-to-Reader

就是：

```text
Device → Reader
```

例如：

> tag 回复自己的 ID。

论文专门把两个方向分别讨论。

---

# 20. Paging 是什么？

这是你之后 simulation 必须非常熟悉的词。

## Paging

你可以理解成：

> **Reader 喊设备：“醒醒！现在轮到你们跟我通信了！”**

例如：

```text
Reader:

"HELLO ALL TAGS, INVENTORY STARTING!"
```

这条唤醒/触发消息就是：

> A-IoT paging

论文定义得很明确：

> A-IoT paging 是一个 R2D message，用来触发 random access procedure。

---

# 21. Random Access 是什么？

## Random Access

中文：

> **随机接入**

假设 600 台设备都想跟一个 Reader 讲话。

你不可能让大家同时喊：

```text
TAG1TAG27TAG384TAG503...
```

完全听不清。

所以需要某种：

> 接入机制。

其中一种方法就是：

> 每个 device 随机选一个机会说话。

这就是 random access。

---

# 22. CBRA 是什么？

## CBRA = Contention-Based Random Access

拆开：

### Contention

竞争。

### Based

基于。

### Random Access

随机接入。

所以：

> **基于竞争的随机接入。**

意思是：

设备之间没有提前分配独占资源。

大家自己随机选。

所以可能：

> 撞车。

---

# 23. CFRA 是什么？

## CFRA = Contention-Free Random Access

就是：

> **无竞争随机接入**

Reader 可以事先安排：

```text
Tag A → 位置 1
Tag B → 位置 2
Tag C → 位置 3
```

因此不会撞。

但问题是 inventory 刚开始的时候：

> Reader 甚至不知道附近有哪些设备。

所以论文说：

> 对未知数量设备的 inventory，通常使用 CBRA。

---

# 24. Contention 是什么意思？

简单理解：

> 多个人抢同一资源。

例如四个厕所：

```text
Toilet 1
Toilet 2
Toilet 3
Toilet 4
```

10 个人同时冲过去。

如果：

```text
Alice → Toilet 2
Bob → Toilet 2
```

就发生资源竞争。

通信里也是一样。

---

# 25. AO 是什么？

## AO = Access Occasion

中文你可以先理解：

> **一次可以发送 Msg1 的位置 / 机会。**

AO 可以在：

* 时间上不同
* 频率上不同

例如：

```text
             Frequency
             ↑
AO3       [     ]
AO4       [     ]

AO1       [     ]
AO2       [     ]
           → Time
```

每个 device 随机选择一个 AO。

---

# 26. 为什么既有时间又有频率？

因为无线资源是二维的：

```text
          frequency
              ↑
              │
              │
              │
              └────────→ time
```

所以两台设备可以：

### 时间不同

```text
Tag A: now
Tag B: later
```

或者：

### 频率不同

```text
Tag A: frequency 1
Tag B: frequency 2
```

都能避免互相撞。

---

# 27. FDMA 是什么？

## FDMA = Frequency-Domain Multiple Access

中文：

> **频分多址**

就是：

> 不同设备用不同频率同时通信。

比如：

```text
frequency 1 → Tag A
frequency 2 → Tag B
frequency 3 → Tag C
```

论文提到 A-IoT 可以利用 frequency-domain multiple access。

---

# 28. Msg1、Msg2、Msg3 到底是什么？

这个非常重要。

不要把它们神秘化。

## Msg = Message

所以：

* Msg1 = Message 1
* Msg2 = Message 2
* Msg3 = Message 3

---

整个流程：

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

Reader：

> “谁在这里？来接入。”

---

## Msg1

Tag：

> “我来申请接入，我临时随机 ID 是 12345。”

---

## Msg2

Reader：

> “随机 ID 12345，我听到了。”

---

## Msg3

Tag：

> “好，那我真正的 device ID 是 ABCDEFG。”

当 Msg3 成功以后：

> Reader 才正式 inventory 了这个设备。

论文就是这样描述 CBRA 的。

---

# 29. 为什么 Msg1 用 random ID？

论文给例子：

> 16-bit random ID。

因为 Reader 一开始还不知道：

> 你是谁。

Tag 先临时生成一个短 ID：

```text
101001101011...
```

用它完成初步 handshake。

之后 Msg3 再报告真正 device ID。

---

# 30. ID 是什么？

## ID = Identifier

就是：

> 身份标识符。

类似：

* 学号
* 身份证号
* MAC address
* serial number

这里就是：

> “这个 tag 到底是哪一个 tag？”

---

# 31. Collision 是什么？

## Collision = 碰撞

如果：

```text
Tag A → AO 3
Tag B → AO 3
```

两个同时发 Msg1。

Reader 很可能无法正确解码。

于是：

> Msg1 collision。

论文 Figure 1 就专门画了一个 collision AO。

你可以把它想象成两个人同时对你说话：

> “我是—我是—”

你一个都没听懂。

---

# 32. Slotted ALOHA 是什么？

这个名字你也会看到。

## ALOHA

是一个经典 random access protocol。

最简单思想：

> 谁想说就尝试说。

Slotted ALOHA 增加：

> 只能在规定的时间槽开始说。

于是：

```text
slot 1
slot 2
slot 3
slot 4
```

Tag 随机挑 slot。

论文的 Msg1 random access 就是基于 slotted-ALOHA 思路。

现在你不用学它的数学理论。

---

# 33. Slot 是什么？

## Slot = 时间槽

就是把时间切成小格子。

论文参数里：

$$
1\ slot=0.5ms
$$

arXiv 版本 Table I 就这么设置。

---

## ms 是什么？

### ms = millisecond

毫秒。

$$
1ms=0.001s
$$

所以：

$$
0.5ms=0.0005s
$$

---

# 34. Congestion 是什么？

## Congestion = 拥塞

Collision 是一次撞车。

Congestion 是：

> 整个系统人太多，导致大量撞车。

例如：

```text
600 devices
8 AOs
```

这显然很挤。

就像：

> 600 辆车抢 8 条很短的入口。

---

# 35. Inventory 到底什么时候算成功？

对某一个 Tag：

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

之后论文假设：

> 这个 device 不再参加后续 inventory。

所以最开始：

```text
0 / 600 inventoried
```

然后：

```text
100 / 600
250 / 600
500 / 600
590 / 600
594 / 600
...
```

最终接近：

```text
600 / 600
```

---

# 36. 现在进入论文真正的核心：Energy

每个 device 有能量：

$$
e_{es}
$$

你现在不要怕这个符号。

---

## \(e_{es}\)

意思：

> **当前 energy storage 里面还有多少 energy。**

就是：

> “杯子现在有多少水。”

---

## \(E_{es}^{max}\)

意思：

> 最大容量。

例如 Device 1：

$$
E_{es}^{max}=500nJ
$$

---

# 37. nJ 是什么？

## nJ = nanojoule

J = Joule：

> 能量单位。

nano：

$$
10^{-9}
$$

所以：

$$
1nJ=10^{-9}J
$$

Device 1：

$$
500nJ
$$

真的非常小。

---

# 38. Power 和 Energy 有什么区别？

这个基础一定要搞明白。

## Energy

是：

> “一共有多少能量。”

单位：

$$
J
$$

---

## Power

是：

> “每秒使用多少能量。”

单位：

$$
W
$$

关系是：

$$
Energy=Power\times Time
$$

也就是：

$$
E=P\cdot t
$$

因此：

$$
t=\frac{E}{P}
$$

这个公式后面非常重要。

---

比如：

$$
E=500nJ
$$

设备消耗：

$$
P=1\mu W
$$

那么理论上：

$$
t=\frac{500\times10^{-9}}
{1\times10^{-6}}
=0.5s
$$

---

# 39. \(P_{rx}\) 是什么？

## Rx = Receive

所以：

$$
P_{rx}
$$

就是：

> **device 接收信号时的功耗。**

Device 1：

$$
P_{rx}=1\mu W
$$

Device 2：

$$
P_{rx}=50\mu W
$$

---

# 40. \(P_{tx}\) 是什么？

## Tx = Transmit

所以：

$$
P_{tx}
$$

是：

> device 发信号时的功耗。

Device 1：

$$
1\mu W
$$

Device 2：

$$
200\mu W
$$

以后看到：

* Rx = receive
* Tx = transmit

直接条件反射。

---

# 41. \(P_{eh}\) 是什么？

## EH = Energy Harvesting

所以：

$$
P_{eh}
$$

就是：

> **设备收集能量的功率。**

论文定义：

$$
P_{eh}=p_{in}\xi(p_{in})
$$

我们一个一个拆。

---

# 42. \(p_{in}\) 是什么？

## in = input / incident

$$
p_{in}
$$

就是：

> **真正到达 tag 的 RF power。**

Reader 虽然发：

> 很强的 signal

但是信号在空气里传播会衰减。

所以：

```text
离 Reader 很近
→ pin 较高

离 Reader 很远
→ pin 较低
```

---

# 43. dBm 是什么？

论文里会出现：

$$
-36dBm
$$

## dBm

是无线通信里非常常见的 power 表示方法。

它是 logarithmic scale。

你现在不需要掌握完整公式，但需要有感觉：

```text
0 dBm  = 1 mW
-10 dBm = 0.1 mW
-20 dBm = 0.01 mW
-30 dBm = 0.001 mW
```

所以：

$$
-36dBm
$$

已经是非常微弱的信号。

注意：

> 越负，一般越弱。

例如：

$$
-10dBm
$$

比：

$$
-36dBm
$$

强很多。

---

# 44. Receiver sensitivity 是什么？

## Receiver sensitivity

中文：

> **接收机灵敏度**

意思：

> 信号至少要强到什么程度，receiver 才有能力工作。

论文设：

$$
-36dBm
$$

作为 receiver chain sensitivity。

低于这个值的 devices 不计入 evaluation。

意思：

```text
pin < -36 dBm
→ 太弱
→ 不算了
```

---

# 45. \(\xi(p_{in})\) 又是什么？

希腊字母：

$$
\xi
$$

读：

> xi，近似“克赛”。

这里表示：

## Power Conversion Efficiency

> RF 能量转成可用电能的效率。

例如：

$$
\xi=5\%
$$

意思：

你收到：

```text
100 units RF energy
```

最后真正存进去：

```text
5 units
```

其余损失了。

---

# 46. 为什么不同 Tag 的充电速度不同？

因为：

$$
P_{eh}=p_{in}\xi(p_{in})
$$

如果你离 Reader 很远：

$$
p_{in}\downarrow
$$

通常：

$$
P_{eh}\downarrow
$$

所以：

> 远处设备充电很慢。

近处：

> 充得快。

这就是为什么最后几个设备可能把 inventory 时间拖得特别长。

---

# 47. ON state 是什么？

## ON state

意思：

> 设备打开，可以通信。

它可以：

* receive paging
* transmit Msg1
* receive Msg2
* transmit Msg3

但：

> 会耗电。

论文定义 ON state 为可用于 reception/transmission 的状态。

---

# 48. OFF state 是什么？

## OFF state

意思：

> 主电路关闭。

设备：

* 不能 receive
* 不能 transmit
* 可以 harvest energy

所以：

```text
OFF
→ 充电

ON
→ 工作 / 耗电
```

---

# 49. IC 是什么？

## IC = Integrated Circuit

中文：

> **集成电路 / 芯片**

论文说 OFF state 时：

> IC turned off

你就理解成：

> 主芯片关闭，不进行正常通信。

---

# 50. Turn-on threshold 是什么？

论文记：

$$
E_{es}^{up}
$$

就是：

> **开机门槛。**

例如 Device 1：

$$
E_{es}^{max}=500nJ
$$

论文设：

$$
E_{es}^{up}=E_{es}^{max}
$$

所以：

> 必须充到满附近才打开。

---

# 51. Turn-off threshold 是什么？

论文记：

$$
E_{es}^{low}
$$

就是：

> **关机门槛。**

论文设：

$$
E_{es}^{low}=0.5E_{es}^{max}
$$

Device 1：

$$
E_{es}^{max}=500nJ
$$

所以：

$$
E_{es}^{low}=250nJ
$$

---

因此：

```text
500 nJ
↑
Turn ON

工作
工作
工作
↓
250 nJ
Turn OFF

充电
充电
充电
↑
500 nJ
Turn ON
```

---

# 52. EM 是什么？

## EM = Energy-Based Monitoring

中文可以理解成：

> **基于能量的监听机制**

这是论文里的 baseline。

Baseline 意思：

> **拿来比较的旧方案 / 基准方案。**

EM 的规则特别简单：

> 有足够电 → ON
> 电掉太低 → OFF

所以：

```text
E reaches E_up
↓
ON
↓
一直监听
↓
E reaches E_low
↓
OFF
↓
一直充电
↓
E reaches E_up
↓
ON
```

---

# 53. Monitoring 是什么意思？

## Monitoring

这里就是：

> **设备保持 receiver 打开，等 Reader 的 paging。**

不是说：

> 它正在持续传数据。

而是：

> 耗着电、睁着耳朵听。

这恰恰很耗能。

---

# 54. 论文为什么认为 EM 不够好？

论文列了：

* P1
* P2
* P3

这里 P 就是：

> Problem。

---

# 55. P1：设备可能要充太久

假设 inventory 开始的时候：

Tag 正好：

$$
e_{es}\approx E_{es}^{low}
$$

也就是：

> 快没电了。

同时又离 Reader 很远：

$$
p_{in}\approx-36dBm
$$

所以充电特别慢。

论文举例：

> 从低阈值充到高阈值需要 250 nJ，在 \(p_{in}=-36dBm\)、效率 5% 的情况下，大约要 20 秒。

这 20 秒 Tag：

```text
Reader: PAGING!
Tag: ...
Reader: PAGING!
Tag: ...
Reader: PAGING!
Tag: ...
```

全错过。

---

# 56. P2：虽然醒着，但没电完成整个过程

这更像：

> 手机还有 1% 电。

它能亮屏。

但是你刚打开大型游戏：

> 关机了。

Tag 也是：

```text
收到 Paging ✓

发 Msg1 ✓

收 Msg2 ...

没电
```

结果：

> CBRA 没完成。

论文把这定义为 P2。

---

# 57. P3：一直撞车，重试，把电耗光

假设设备有电。

但是：

```text
Attempt 1 → collision
Attempt 2 → collision
Attempt 3 → collision
Attempt 4 → collision
```

它每一次都需要：

* 醒来
* receive
* transmit
* wait

于是一直耗电。

最后：

```text
没成功
+
没电了
```

这就是 P3。

---

# 58. 于是论文提出 DCM

## DCM = Duty Cycled Monitoring

这个名字很重要。

### Duty Cycle

意思：

> 一个设备不是一直 ON，而是周期性 ON / OFF。

比如：

```text
ON   OFF OFF OFF   ON   OFF OFF OFF   ON
```

而不是：

```text
ON ON ON ON ON ON ON ON ON
```

所以：

## Duty Cycled Monitoring

就是：

> **间歇式监听。**

---

# 59. DCM 的核心思想到底是什么？

一句话：

> **不要把电一直耗到最低再去充电。**

传统 EM：

```text
500 nJ
↓
一直监听
↓
一直监听
↓
一直监听
↓
250 nJ
↓
OFF
↓
需要补 250 nJ
```

DCM：

```text
500 nJ
↓
只监听一小段
↓
比如还有 470 nJ
↓
主动睡觉
↓
只需要补 30 nJ
```

所以恢复得快。

---

# 60. 为什么主动睡觉反而会变快？

这点第一次看很反直觉。

你可能觉得：

> “我要尽快接收 paging，不是应该一直醒着吗？”

问题是：

一直醒：

> 会把电耗光。

一旦耗光：

> 可能需要十几秒才能恢复。

所以 DCM 的思想像：

> 不要连续熬夜到昏迷，再睡 20 小时。

而是：

> 每次工作一小段就休息，始终保持状态。

---

# 61. On timer 是什么？

## Timer = 计时器

DCM 加了：

> on timer。

例如：

> “我最多醒 18 ms。”

18 ms 到了，如果还没收到 paging：

> 我自己去睡。

这个时长论文记成：

$$
T_{on}^{timer}
$$

正式版本 Device 1 使用：

$$
18ms
$$

Device 2：

$$
26ms
$$

---

# 62. \(T_{pg}\) 是什么？

## pg = paging

$$
T_{pg}
$$

就是：

> 两次 periodic paging 之间的周期。

Device 1：

$$
T_{pg}=12ms
$$

Device 2：

$$
14ms
$$

---

# 63. Periodic 是什么意思？

## Periodic = 周期性的

比如：

```text
0 ms   Paging
12 ms  Paging
24 ms  Paging
36 ms  Paging
48 ms  Paging
```

就是：

> 每 12 ms 一次。

---

# 64. Aperiodic 又是什么？

## Aperiodic

就是：

> 非周期性的。

例如：

```text
0ms
11ms
25ms
41ms
...
```

时间不固定。

论文比较里主要关注 periodic paging。

---

# 65. 为什么 \(T_{on}^{timer}\ge T_{pg}\)？

因为设备醒来以后：

> 至少应该保持醒着足够久，有机会碰到一次 paging。

假设 paging 每：

$$
12ms
$$

一次。

而你只醒：

$$
2ms
$$

很可能：

```text
wake
sleep

        paging
```

完全错过。

所以论文说最好：

$$
T_{on}^{timer}\ge T_{pg}
$$

---

# 66. Sleep state 又是什么？

DCM 里面增加一个：

## Sleep state

区别于完全 OFF。

Sleep：

* 不能正常 Rx/Tx
* 可以 harvest energy
* 还保持一个低功耗 timer
* 知道什么时候该醒

论文说 sleep state 中 device 可以维持 sleep timer，同时 harvesting，但不能 transmit/receive。

---

# 67. 为什么第一次 Paging 特别重要？

第一次之前：

Tag 不知道：

> Reader 有没有开始 inventory。

所以它只能：

```text
醒
听
睡
醒
听
睡
```

但是第一次收到 paging 后：

> “哦！我现在知道 inventory 已经开始，而且 paging 每 12 ms 一次。”

于是以后可以：

```text
       paging
         ↓
sleep sleep ON
         ↓
       paging
         ↓
sleep sleep ON
```

这叫：

# Synchronization

---

# 68. Synchronization 是什么？

## Synchronization = 同步

就是：

> 两边时间对齐。

Reader 知道：

```text
Paging at t=12,24,36...
```

Tag 也知道。

所以 Tag 可以：

> 只在 paging 快来时醒。

这是非常经典的通信思想。

---

# 69. \(T_{sl}^{DCM}\) 是什么？

## sl = sleep

所以：

$$
T_{sl}^{DCM}
$$

就是：

> DCM 的 sleep duration。

---

# 70. \(T_{on}^{DCM}\) 是什么？

就是：

> 每个 paging 周期里面 ON 多久。

论文要求：

$$
T_{sl}^{DCM}+T_{on}^{DCM}=T_{pg}
$$

也就是：

```text
一个 paging 周期
=
sleep 时间
+
醒着时间
```

---

# 71. \(P_{sl}\) 是什么？

## sl = sleep

$$
P_{sl}
$$

就是：

> sleep state 功耗。

论文：

$$
P_{sl}=0.1\mu W
$$

而：

$$
P_{sl}<P_{rx}
$$

所以睡觉比一直开 receiver 省很多电。

---

# 72. DCM 到这里解决了什么？

大概：

### P1

不会把 energy 降得太低。

所以 recharge 快。

### P2

收到 paging 时，通常剩余 energy 比较高。

所以更有机会完成 CBRA。

### P3

不用一直 ON。

所以即使多次 retry，也不容易把电很快耗光。

---

# 73. 但是还有一个巨大问题：600 台设备

想象：

```text
Reader:
"PAGING!"

600 devices:
"ME!"
```

就爆炸了。

所以还需要：

# Congestion Control

---

# 74. Congestion Control 是什么？

就是：

> **控制拥塞。**

不能让所有设备同时 access。

这篇论文主要讲两个方法：

1. access probability
2. device grouping

---

# 75. Access Probability 是什么？

## Probability = 概率

Reader 可以告诉设备：

> “虽然你收到 paging，但这一轮只有一定概率参加。”

例如：

$$
p=0.1
$$

600 个设备中，大概只有：

$$
600\times0.1=60
$$

个参加。

---

每个 Tag：

```text
random number
↓
0.073 < 0.1
→ access

0.51 > 0.1
→ don't access
```

这样就不会 600 个全冲进 AO。

论文明确说 reader 可以根据先前 CBRA 的 congestion/occupancy 来决定 access probability。

---

# 76. Occupancy 是什么？

## Occupancy

就是：

> AO 有多满。

例如 8 个 AO：

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

Reader 可以从这些情况估计：

> 现在是不是太挤了。

---

# 77. 为什么 Access Probability 也有缺点？

假设：

Tag 为了听 paging：

> 醒来了。

消耗了 energy。

但是 paging 告诉它通过随机概率判断：

> “这轮不参加。”

那么：

```text
wake up
↓
burn energy
↓
do nothing
```

很浪费。

论文正是因此提出 device grouping。

---

# 78. Device Grouping 是什么？

## Grouping = 分组

例如 600 个设备分四组：

```text
Group A
Group B
Group C
Group D
```

然后：

```text
Paging 1 → Group A
Paging 2 → Group B
Paging 3 → Group C
Paging 4 → Group D
Paging 5 → Group A
```

那么 Group A 不需要每轮都醒。

---

例如：

```text
A:      ON            ON
B:           ON            ON
C:                ON
D:                     ON
```

于是：

* collision 减少
* 无意义 listening 减少
* energy 消耗降低

Figure 4 就是在画这个思想。

---

# 79. Low-Power Wake-Up Receiver 又是什么？

名字拆开：

## Receiver

接收机。

## Wake-up

唤醒。

## Low-power

低功耗。

所以：

> **一个专门负责“有没有人在叫我”的超低功耗小接收机。**

---

你可以把正常 receiver 想成：

> 一台大电脑。

Wake-up receiver：

> 一个非常简单的小门铃。

平时不用把大电脑全部开着。

只让：

> 门铃监听。

一旦听到：

> “PING！”

再把主系统唤醒。

---

论文特别说这个对 Device 2 有帮助，因为 Device 2 正常 receiver：

$$
P_{rx}=50\mu W
$$

而 low-power wake-up receiver：

$$
1\mu W
$$

差很多。

---

# 80. Preamble 是什么？

论文说 paging 带：

> preamble。

## Preamble = 前导序列

就是正式消息之前先发一个已知 pattern：

```text
101010101...
```

设备知道：

> “只要我检测到这个 pattern，就说明 paging 要来了。”

很像你敲门：

```text
咚咚—咚咚咚
```

里面的人听到这个特殊节奏：

> “哦，是自己人。”

---

# 81. OOK 是什么？

## OOK = On-Off Keying

这是一种非常简单的 modulation。

---

## Modulation 是什么？

### Modulation = 调制

意思：

> 怎样把 0 和 1 放到无线波上。

---

OOK 特别简单：

```text
carrier ON  → 1
carrier OFF → 0
```

所以：

```text
1 0 1 1 0

ON OFF ON ON OFF
```

这非常适合低复杂度设备。

论文说 R2D 使用 OOK。

---

# 82. BPSK 是什么？

## BPSK = Binary Phase Shift Keying

也是 modulation。

不同之处：

> 不用“有波 / 没波”，而是用两个相位表示 0 和 1。

例如：

$$
0^\circ\rightarrow0
$$

$$
180^\circ\rightarrow1
$$

你现在知道名字就够了。

Figure 5(b) reproduction 不需要你先成为 BPSK 专家。

---

# 83. OFDM 是什么？

## OFDM = Orthogonal Frequency-Division Multiplexing

这是现代通信非常重要的技术。

4G/5G/Wi-Fi 都大量使用。

最粗暴的理解：

> 把一个高速信号拆到很多小的 frequency subcarriers 上。

像：

```text
frequency →
|_|_|_|_|_|_|_|_|
```

论文提到 Reader 可以利用 NR OFDM transmitter 产生 OOK waveform。

但是对你复现 Figure 5(b)：

> OFDM 不是第一优先级。

---

# 84. FDD 是什么？

## FDD = Frequency Division Duplex

通信双方两个方向用不同 frequency。

比如：

```text
frequency A:
BS → UE

frequency B:
UE → BS
```

叫：

> uplink/downlink 分频。

论文介绍 A-IoT spectrum 时提到 FDD spectrum。

同样：

> 不是你第一阶段 simulation 的核心。

---

# 85. Uplink / Downlink 是什么？

## Downlink

```text
BS → device
```

从基站下来。

---

## Uplink

```text
device → BS
```

从用户设备上传。

在本论文里和：

* R2D
* D2R

概念相近，但不是任何情况下完全等价。

---

# 86. Link Budget 是什么？

## Link Budget

这是无线通信很重要的概念。

简单理解：

> 发射端发了多少功率，经过各种增益和损耗，到接收端最后还剩多少。

例如：

```text
Tx power
+ antenna gain
- path loss
- obstacles
= received power
```

如果最后太弱：

> 接收失败。

论文用它讨论 Device 1 / Device 2 可能覆盖多远。

---

# 87. CDF 是什么？

这个是 Figure 5 里面非常重要的数学概念。

## CDF = Cumulative Distribution Function

中文：

> **累积分布函数**

别被名字吓到。

例如 100 个学生成绩。

你问：

> 分数 ≤ 60 的有多少比例？

然后：

> ≤70？

> ≤80？

> ≤90？

把这个比例画出来：

> 就是 CDF。

---

Figure 5(a) 是 received power 的 CDF。

意思大致是：

> 有多少比例的设备 \(p_{in}\) 小于某个值。

---

# 88. Figure 5(b) 到底是什么？

终于到了教授让你做的东西。

Figure 5(b) 是：

> **Device 1 在时间推移过程中，有多少比例已经成功被 inventory。**

纵轴：

```text
Successfully inventoried A-IoT device ratio (%)
```

横轴：

```text
Time (ms)
```

---

开始：

$$
t=0
$$

可能：

$$
0\%
$$

然后：

```text
1 second → 40%
2 seconds → 60%
5 seconds → 90%
...
```

最终：

$$
99\%
$$

---

# 89. 为什么只说 99%，不一定说 100%？

通信系统里最后：

> 最差的那几个 device

可能特别慢。

所以常用：

* 90%
* 95%
* 99%

作为完成指标。

论文主要比较：

> 达到 99% inventory 需要多久。

---

# 90. Figure 5(b) 有哪几条线？

正式版本比 arXiv 更完整。

Device 1 图包括：

* EM, aperiodic paging
* DCM, periodic paging, 1 group
* DCM, periodic paging, 4 groups

你把它翻译成人话：

### EM

旧方案。

### DCM + 1 group

使用节能监听，但是基本不做真正的 group separation。

### DCM + 4 groups

使用节能监听，而且把 devices 分四组。

---

# 91. 最关键的实验结论是什么？

Device 1：

> 单独 DCM 并没有明显改善。

为什么？

因为：

> 600 个 devices 太拥塞，access probability 会压得很低。

但：

> DCM + device grouping

可以把 99% inventory completion time 大约减少 50%。

正式论文明确这样解释。

---

Device 2：

DCM 单独已经很有效。

论文报告大约：

> 66% reduction。

再加 low-power wake-up receiver：

> 最多约 83% reduction。

---

# 92. 所以整篇论文真正的逻辑是一条链

你现在一定要先建立这个脑图：

```text
A-IoT device 没电池
        ↓
必须 energy harvesting
        ↓
有时候没电
        ↓
没电就收不到 paging
        ↓
inventory 变慢
        ↓
传统 EM 会把能量消耗太低
        ↓
需要很久 recharge
        ↓
提出 DCM
        ↓
不要一直醒着
        ↓
保留更多 energy
        ↓
更容易参与 inventory
```

但是：

```text
600 devices
   ↓
同时 access
   ↓
congestion / collision
   ↓
需要 access probability
```

但是：

```text
access probability
   ↓
很多 device 醒了却不能发
   ↓
浪费 energy
   ↓
device grouping
```

最后：

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

这就是整篇 paper。

---

# 93. 那教授为什么让你复现 Figure 5(b)，而不是 Figure 1？

因为 Figure 1 是：

> protocol illustration。

你看懂就行。

Figure 5(b) 是：

> simulation result。

要复现它，你必须真的理解：

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

所以这是一个非常好的 research-fit test。

---

# 94. 他实际上在测试你哪些能力？

我认为大概有六层。

### 第一层：能不能读陌生论文

你现在不懂：

> 完全正常。

关键是：

> 能不能一点一点搞懂。

---

### 第二层：能不能把文字变成模型

论文写：

> device enters off state when energy falls below threshold。

你需要转换成：

```python
if energy <= E_low:
    state = OFF
```

---

### 第三层：能不能把 protocol 写成 algorithm

例如：

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

### 第四层：能不能处理 randomness

因为：

* device received power 不同
* AO 随机选择
* access probability 随机
* device grouping
* collisions

所以这不是 deterministic homework。

---

### 第五层：能不能 debug

你第一次结果很可能：

> 完全不像 Figure 5(b)。

然后需要问：

> initial energy 怎么设？

> DCM transition 对吗？

> device after successful inventory 是否退出？

> power 的 dBm 转 watt 对吗？

这才是 research。

---

### 第六层：能不能解释

最后教授可能真正问你的不是：

> “你的 Python 有多少行？”

而是：

> “Why does DCM alone not improve device-1 performance?”

你需要说：

> Because heavy contention leads to a low access probability; grouping reduces the number of devices monitoring/contending for a given paging opportunity.

这个“解释结果”的能力很重要。正式论文就是这么解释 Device 1 的。

---

# 95. 所以你现在不要焦虑“我什么都不会”

你现在更适合把整个任务看成：

```text
阶段 1
学会语言

阶段 2
看懂系统

阶段 3
看懂公式

阶段 4
把系统画成 state machine

阶段 5
把 state machine 写成 simulation

阶段 6
复现 Figure 5(b)

阶段 7
解释为什么结果这样
```

**不要直接跳阶段 5。**

如果你现在直接让我给你代码，我反而认为不是最好的做法。

因为教授如果之后问你：

> Why did you model it this way?

你很容易答不上来。

---

# 96. 你目前最需要背下来的缩写，我给你做个“第一张词汇表”

不用今天一次全背完，但之后看到要认识：

| 缩写    | 全称                                         | 你先怎么理解          |
| ----- | ------------------------------------------ | --------------- |
| IoT   | Internet of Things                         | 物联网             |
| A-IoT | Ambient IoT                                | 超低功耗/无电池物联网设备   |
| 3GPP  | 3rd Generation Partnership Project         | 移动通信标准体系        |
| BS    | Base Station                               | 基站              |
| UE    | User Equipment                             | 手机/终端           |
| RF    | Radio Frequency                            | 无线射频            |
| RFID  | Radio Frequency Identification             | 射频标签            |
| UHF   | Ultra High Frequency                       | 特高频             |
| CW    | Continuous Wave                            | 连续载波            |
| NR    | New Radio                                  | 5G 无线接口         |
| R2D   | Reader-to-Device                           | Reader → Device |
| D2R   | Device-to-Reader                           | Device → Reader |
| CBRA  | Contention-Based Random Access             | 竞争式随机接入         |
| CFRA  | Contention-Free Random Access              | 无竞争随机接入         |
| AO    | Access Occasion                            | 一次 Msg1 发送机会    |
| ID    | Identifier                                 | 身份编号            |
| EM    | Energy-Based Monitoring                    | 旧的能量监听机制        |
| DCM   | Duty Cycled Monitoring                     | 间歇监听            |
| Rx    | Receive                                    | 接收              |
| Tx    | Transmit                                   | 发送              |
| EH    | Energy Harvesting                          | 能量采集            |
| IC    | Integrated Circuit                         | 芯片              |
| CDF   | Cumulative Distribution Function           | 累积分布函数          |
| OOK   | On-Off Keying                              | 开/关调制           |
| BPSK  | Binary Phase Shift Keying                  | 二进制相移键控         |
| OFDM  | Orthogonal Frequency-Division Multiplexing | 正交频分复用          |
| FDMA  | Frequency-Domain Multiple Access           | 频分多址            |
| FDD   | Frequency Division Duplex                  | 频分双工            |
| TR    | Technical Report                           | 技术报告            |

这 30 个左右已经覆盖了 paper 绝大多数“看起来很吓人”的术语。

---

# 97. 你现在应该达到什么程度？

现在**完全不要求**你会：

$$
OFDM
$$

推导。

也不要求你会：

$$
BPSK
$$

误码率。

甚至暂时不要求你会：

> 3GPP NR protocol stack。

你第一阶段只需要能不看论文回答下面这句话：

> “这篇论文是研究几百个依靠 RF energy harvesting 的 batteryless A-IoT tags 如何被 reader 快速 inventory。传统 EM 会导致 device 把能量消耗过低，从而长时间 unavailable；DCM 通过 duty cycling 保持较高 energy level，同时结合 access probability 和 device grouping 控制 congestion，从而降低 inventory completion time。”

如果这句话你能真正理解，而不是背下来：

> **第一阶段已经过关了。**

---

接下来我建议我们就按照“课程”的方式学，而不是继续一次性塞更多东西。

**下一步最合适的是我带你逐图读这篇论文：先从 Figure 1 开始，我把图上的每一个方框、每一条横轴纵轴、Paging、Msg1、AO、collision、Msg2、Msg3 全部拆开；然后 Figure 2、Figure 3、Figure 4，最后才进入教授要求的 Figure 5(b)。**

这样等读到 Figure 5(b) 的时候，你会知道**曲线里的每一个点到底是怎么产生的**，而不是只知道“橙色比紫色快”。


---

