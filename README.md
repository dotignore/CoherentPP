# CoherentPP - Channel Synchronization for KrakenSDR

## What is this project about?

This project helps synchronize multiple radio receivers (channels) in a **KrakenSDR** device. Think of it like tuning multiple radios to play the same song at exactly the same time - if one radio is slightly off, you'll hear an echo. This program fixes that "echo" by measuring and correcting the timing differences.

### Key Terms (Simple Explanations)

- **KrakenSDR**: A device with 4-5 radio receivers that work together to find the direction of radio signals
- **IQ Samples**: Digital representation of radio signals (like taking photos of sound waves)
- **Channel**: One of the radio receivers in the device
- **PPM** (Parts Per Million): A very precise way to measure frequency error (like measuring 1 millimeter error in 1 kilometer)
- **PPT** (Parts Per Thousand): Same as PPM but 1000 times larger (1 PPT = 1000 PPM)
- **Cross-correlation**: A mathematical method to find how much one signal is delayed compared to another

### Example: What is 1 PPM?
If your radio frequency is **2.4 MHz** (2,400,000 Hz):
- **1 PPM** = 2.4 Hz error (very small!)
- **10 PPM** = 24 Hz error
- **0.000001 PPM** = 0.0024 Hz error (incredibly precise!)

---

## What does `correction.py` do?

My program `correction.py` is a post-processor that:
1. Takes saved IQ data from 2 channels (Channel 0 and Channel 1)
2. Compares them to find timing differences
3. Calculates correction values (in PPM) to synchronize the channels

### Example Data
The program analyzes blocks of **262,144 IQ sample pairs** saved as `.bin` files:
```
/_logs/iq_data/session/ch0/block_00007.bin  (Channel 0 - reference)
/_logs/iq_data/session/ch1/block_00007.bin  (Channel 1 - needs correction)
```

Configuration from KrakenSDR:
```
daq_buffer_size = 262144
```
Source: https://github.com/krakenrf/heimdall_daq_fw/blob/main/Firmware/daq_chain_config.ini

---

## How it works (Step by Step)

### Step 1: Enable Noise Generator
After enabling the **NG (noise generator)** on the device, both channels receive the same signal. We can then measure any timing differences.

### Step 2: Compare Channels
- **Channel 0** = Reference (like a master clock)
- **Channel 1** = Measured against Channel 0

### Step 3: Find the Delay
Using **cross-correlation**, the program finds:
- **Block 7 example**: Delay of **-23,489 IQ samples** between channels
- This means Channel 1 is "behind" Channel 0 by 23,489 samples

### Step 4: Convert to PPM
The delay is converted to a **PPM correction value** that can be sent to the RTL2832U chip to adjust its frequency.

**Why corrections are limited to ±0.010000 (±10 PPM)?**

The firmware has a safety limit:
```python
self.MAX_FS_PPM_OFFSET = 0.01  # Maximum 10 PPM per step
```
Source: https://github.com/krakenrf/heimdall_daq_fw/blob/main/Firmware/_daq_core/delay_sync.py

This means:
- Large delays (e.g., 9,418 samples) → maximum correction of -10 PPM
- Small delays (e.g., 1,934 samples) → smaller correction of -9.67 PPM

---

## Visual Guide: IQ Sampling

![IQ Sampling Diagram](pic/IQ_sample.png)

**Learn more:**
- [IQ Sampling Wiki](https://pysdr.org/content/sampling.html)
- [What is 4096QAM? (Wi-Fi 7 technology)](https://internet.watch.impress.co.jp/docs/column/shimizu/2008501.html)

---

## Example Output from `correction.py`

Running the program for **Block 7**:

```
user@LenovoMACVentura CoherentPP % python3 correction.py
Block 7, channels 0 and 1
Correlation length (number of checked shifts k): 524288
Peak index (peak_index): 285633
Channel 1 delay relative to channel 0 (samples): delays[1] = N - peak_index = -23489
Max correlation value: 573311500.0
  k=285628: correlation = 1.44e+08
  k=285629: correlation = 4.46e+06
  k=285630: correlation = 1.24e+08
  k=285631: correlation = 2.78e+07
  k=285632: correlation = 1.55e+07
  k=285633: correlation = 5.73e+08 <-- peak (best match!)
  k=285634: correlation = 1.54e+08
  k=285635: correlation = 3.17e+07
  k=285636: correlation = 1.01e+08
  k=285637: correlation = 1.55e+08
  k=285638: correlation = 1.18e+08
user@LenovoMACVentura CoherentPP %
```

### What this means:
- The program checked **524,288 different time shifts** (k values)
- Found the **best match** at k=285633 (highest correlation)
- This corresponds to a **delay of -23,489 samples**
- Requires a **+10 PPM correction** to fix

---

## Full Synchronization Process

Session: `/krakensdr_doa/heimdall_daq_fw/Firmware/_logs/iq_data/session_CPP`
- **Total blocks analyzed**: 124 (range: 0 to 263)
- **Goal**: Synchronize Channel 1 to Channel 0

### Understanding the Corrections

**Initial Setup:**
- Unknown starting frequency: **2.502154 MHz** (hypothetical for demonstration)
- After base correction of **-0.040860** (≈ 4%): **2.400000 MHz** ✓

Each block then applies small PPM corrections to fine-tune synchronization.

---

## Understanding the Table

### Column Explanations

| Column | What it means | Example |
|--------|---------------|---------|
| **Block** | Block number (measurement session) | 7 |
| **IQ Samples** | Timing delay in samples | -23,489 |
| **PPM** | Correction applied THIS block | +0.010000 |
| **PPM correction (cumulative)** | Sum of ALL corrections so far | -0.050860 |
| **Freq correction** | Frequency for THIS block | 2.400024000 MHz |
| **PPT** | Same as PPM but ×1000 | 10.0000 |
| **Formula** | Calculation showing how frequency is corrected | 2.502154 × (1 - 0.040860) × (1 + 10/1000000) |

### Why "Freq correction" doesn't always change?

**Answer**: The "Freq correction" column shows the frequency **for that specific block's PPM value**, not the accumulated frequency!

Example:
```
Block 49: PPM = -0.010000 → Freq = 2.399976000 MHz
Block 55: PPM = -0.010000 → Freq = 2.399976000 MHz (same PPM = same freq!)
Block 61: PPM = -0.010000 → Freq = 2.399976000 MHz
```

Even though **PPM cumulative** is changing (-0.003000 → -0.013000 → -0.023000), the **current block's PPM** stays at -0.010000, so the frequency stays the same.

---

## Synchronization Data Table

```

Block   IQ Samples       PPM          PPM correction   Freq correction      PPT      	 RTLSDR 1 Frequency (MHz)
                     (-0.040860)      (cumulative)        (2.502154 MHz)
-----	--------	------------	--------------	-----------------	-----------	----------------------------------------------------------
  0  	  9418  	 -0.010000  	  -0.050860  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
  1  	   617  	 -0.003085  	  -0.053945  	   2.399992596  	  -3.0850  	 2.502154 × (1 - 0.040860) × (1 - 3.085/1000000) = 2.399992596
  2  	  3472  	 -0.010000  	  -0.063945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
  3  	 -21101 	  0.010000  	  -0.053945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
  4  	 -22432 	  0.010000  	  -0.043945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
  5  	  17434 	 -0.010000  	  -0.053945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
  6  	  37607 	 -0.010000  	  -0.063945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
  7  	 -23489 	  0.010000  	  -0.053945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
  8  	   3535 	 -0.010000  	  -0.063945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
  9  	  -5207 	  0.010000  	  -0.053945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 10  	   6370 	 -0.010000  	  -0.063945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 11  	  -3508 	  0.010000  	  -0.053945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 12  	 -19481 	  0.010000  	  -0.043945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 13  	   2164 	 -0.010000  	  -0.053945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 14  	 -67961 	  0.010000  	  -0.043945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 15  	 -48074 	  0.010000  	  -0.033945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 16  	  21311 	 -0.010000  	  -0.043945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 17  	 -19968 	  0.010000  	  -0.033945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 18  	  10319 	 -0.010000  	  -0.043945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 19  	 -14147 	  0.010000  	  -0.033945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 20  	  -7284 	  0.010000  	  -0.023945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 21  	 -45346 	  0.010000  	  -0.013945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 22  	 -19036 	  0.010000  	  -0.003945  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 23  	   6975 	 -0.010000  	  -0.013945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 24  	   2327 	 -0.010000  	  -0.023945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 25  	  15408 	 -0.010000  	  -0.033945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 26  	   5735 	 -0.010000  	  -0.043945  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 27  	   -195 	  0.000975  	  -0.042970  	   2.400002340  	   0.9750  	 2.502154 × (1 - 0.040860) × (1 + 0.975/1000000) = 2.400002340
 28  	  44214 	 -0.010000  	  -0.052970  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 29  	 -13460 	  0.010000  	  -0.042970  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 30  	 -11435 	  0.010000  	  -0.032970  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 31  	  -3399 	  0.010000  	  -0.022970  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 32  	 -20022 	  0.010000  	  -0.012970  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 33  	 -30586 	  0.010000  	  -0.002970  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 34  	  15035 	 -0.010000  	  -0.012970  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 35  	  -6197 	  0.010000  	  -0.002970  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 36  	  -4125 	  0.010000  	   0.007030  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 37  	  -9417 	  0.010000  	   0.017030  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 38  	  36255 	 -0.010000  	   0.007030  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 39  	   2424 	 -0.010000  	  -0.002970  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 40  	 -22213 	  0.010000  	   0.007030  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 41  	 -14308 	  0.010000  	   0.017030  	   2.400024000  	  10.0000  	 2.502154 × (1 - 0.040860) × (1 + 10/1000000)    = 2.400024000
 42  	     12 	 -0.000030  	   0.017000  	   2.399999928  	  -0.0300  	 2.502154 × (1 - 0.040860) × (1 - 0.03/1000000)  = 2.399999928
 48  	   5473 	 -0.010000  	   0.007000  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 49  	   5473 	 -0.010000  	  -0.003000  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 55  	   4873 	 -0.010000  	  -0.013000  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 61  	   4210 	 -0.010000  	  -0.023000  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 67  	   3522 	 -0.010000  	  -0.033000  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 68  	   3429 	 -0.010000  	  -0.043000  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 74  	   2691 	 -0.010000  	  -0.053000  	   2.399976000  	 -10.0000  	 2.502154 × (1 - 0.040860) × (1 - 10/1000000)    = 2.399976000
 80  	   1934 	 -0.009670  	  -0.062670  	   2.399976792  	  -9.6700  	 2.502154 × (1 - 0.040860) × (1 - 9.67/1000000)  = 2.399976792
 86  	   1138 	 -0.005690  	  -0.068360  	   2.399986344  	  -5.6900  	 2.502154 × (1 - 0.040860) × (1 - 5.69/1000000)  = 2.399986344
 92  	    790 	 -0.003950  	  -0.072310  	   2.399990520  	  -3.9500  	 2.502154 × (1 - 0.040860) × (1 - 3.95/1000000)  = 2.399990520
 98  	    662 	 -0.003310  	  -0.075620  	   2.399992056  	  -3.3100  	 2.502154 × (1 - 0.040860) × (1 - 3.31/1000000)  = 2.399992056
104  	    533 	 -0.002665  	  -0.078285  	   2.399993604  	  -2.6650  	 2.502154 × (1 - 0.040860) × (1 - 2.665/1000000) = 2.399993604
110  	    407 	 -0.002035  	  -0.080320  	   2.399995116  	  -2.0350  	 2.502154 × (1 - 0.040860) × (1 - 2.035/1000000) = 2.399995116
116  	    280 	 -0.001400  	  -0.081720  	   2.399996640  	  -1.4000  	 2.502154 × (1 - 0.040860) × (1 - 1.4/1000000)   = 2.399996640
122  	    153 	 -0.000765  	  -0.082485  	   2.399998164  	  -0.7650  	 2.502154 × (1 - 0.040860) × (1 - 0.765/1000000) = 2.399998164
128  	    118 	 -0.000590  	  -0.083075  	   2.399998584  	  -0.5900  	 2.502154 × (1 - 0.040860) × (1 - 0.59/1000000)  = 2.399998584
134  	     -9 	  0.000022  	  -0.083053  	   2.400000053  	   0.0225  	 2.502154 × (1 - 0.040860) × (1 + 0.022/1000000) = 2.400000053
140  	     -3 	  0.000007  	  -0.083046  	   2.400000018  	   0.0075  	 2.502154 × (1 - 0.040860) × (1 + 0.007/1000000) = 2.400000018
146  	     -1 	  0.000002  	  -0.083044  	   2.400000005  	   0.0015  	 2.502154 × (1 - 0.040860) × (1 + 0.002/1000000) = 2.400000005
152  	     -1 	  0.000002  	  -0.083042  	   2.400000005  	   0.0015  	 2.502154 × (1 - 0.040860) × (1 + 0.002/1000000) = 2.400000005
158  	     -1 	  0.000002  	  -0.083040  	   2.400000005  	   0.0015  	 2.502154 × (1 - 0.040860) × (1 + 0.002/1000000) = 2.400000005
164  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
165  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
171  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
177  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
183  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
189  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
195  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
201  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
207  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
208  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
209  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓
210  	      0 	  0.000000  	  -0.083040  	   2.400000000  	   0.0000  	 2.502154 × (1 - 0.040860) × (1 + 0/1000000)     = 2.400000000 ✓ Correction is DONE 

```

---

## Synchronization Progress (Visual Guide)

### Phase 1: Initial Corrections (Blocks 0-42)
**Status**: Large timing errors detected
- **Delays**: ±67,000 samples (very large!)
- **Corrections**: Maximum ±10 PPM per block
- **What's happening**: System detects major desynchronization and makes big corrections

### Phase 2: Convergence (Blocks 48-158)
**Status**: Gradually getting closer
- **Delays**: Shrinking from 5,473 → -1 samples
- **Corrections**: Getting smaller (9.67 PPM → 0.002 PPM)
- **What's happening**: Fine-tuning, like focusing a camera

### Phase 3: Perfect Sync (Blocks 164-210)
**Status**: ✓ SYNCHRONIZED
- **Delays**: Zero samples (perfect alignment!)
- **Corrections**: 0 PPM (no adjustment needed)
- **What's happening**: Both channels are perfectly in sync

### Visual Comparison

**Block 140** - Still converging (close but not perfect):

![Block 140 - Almost Synchronized](pic/01.png)

**Block 210** - Perfect synchronization achieved:

![Block 210 - Correction Complete](pic/02.png)

![Additional View](pic/03.png)

![Final Result](pic/04.png)

---

## How to Use This Project

### 1. Run the Correction Analysis

```bash
python3 correction.py
```

**What it does:**
- Analyzes IQ data from saved `.bin` files
- Calculates PPM corrections for each block
- Shows synchronization progress

### 2. Visualize IQ Data in Web Browser

Run the web viewer script:

```bash
./web_run_iq_analyzer.sh
```

**What happens:**
1. Creates Python virtual environment (first time only)
2. Installs required libraries (pandas, numpy, plotly, dash)
3. Launches web server
4. Opens visualization at `http://127.0.0.1:8050`

**Example output:**
```
user@LenovoMACVentura CoherentPP % ./web_run_iq_analyzer.sh
Data dir: /Users/user/Documents/GitHub/CoherentPP/_logs/iq_data
✓ Data path found: /Users/user/Documents/GitHub/CoherentPP/_logs/iq_data/
============================================================
             RTL-SDR IQ Data Web Viewer
============================================================
Data path: .../_logs/iq_data/
✓ Data path found: _logs/iq_data/session/
✓ Found index.csv
✓ Found ch0 directory
============================================================
               KrakenSDR IQ Frame Viewer
============================================================
Data path: _logs/iq_data/session/
Loading index from _logs/iq_data/session/index.csv
✓ Loaded 496 records from index.csv
  Columns: ['Timestamp', 'Block', 'Channel', 'Frequency', 'Field1', 'Field2', 'FilePath']
✓ Processed into 124 unique blocks

DataFrame info:
  Shape: (124, 5)
  Columns: ['Session', 'BlockIndex', 'Channels', 'ChannelList', 'Path']
✓ Found 124 unique blocks (range: 0 to 263)
✓ Found 1 session(s)

Session statistics:
  session: 124 blocks

Channel statistics:
  4 channels: 124 blocks
------------------------------------------------------------
Starting server at http://localhost:8050
============================================================
Dash is running on http://0.0.0.0:8050/

 * Serving Flask app 'iq_web'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8050
 * Running on http://XX.XX.XX.XX:8050
Press CTRL+C to quit
```
![](pic/04.png)
---

## Technical Details (for Advanced Users)

### Algorithm: Cross-Correlation with FFT

The program uses **FFT-based cross-correlation** to efficiently compare signals:

1. **Zero-pad** signals to length 2N
2. Compute **FFT** of both channels
3. Multiply: `correlation = IFFT(conj(FFT_ch0) × FFT_ch1)`
4. Find peak in correlation → gives delay in samples
5. Convert delay to PPM using firmware's scaling factors

### PPM Calculation Formula

```python
# Firmware parameters
MIN_FS_PPM_OFFSET = 1e-7
MAX_FS_PPM_OFFSET = 0.01  # ±10 PPM limit

# Calculate PPM from sample delay
ppm_raw = -delay × gain × MIN_FS_PPM_OFFSET
ppm = clip(ppm_raw, -MAX_FS_PPM_OFFSET, MAX_FS_PPM_OFFSET)
```

### Frequency Correction Formula

For each block, the corrected frequency is:

```
Freq = Initial_Freq × (1 + Base_Correction) × (1 + PPM_Current / 1,000,000)
     = 2.502154 MHz × (1 - 0.040860) × (1 + PPM / 1,000,000)
```

**Example (Block 7):**
```
Freq = 2.502154 × (1 - 0.040860) × (1 + 10 / 1,000,000)
     = 2.502154 × 0.959140 × 1.00001
     = 2.400024000 MHz
```

---

## FAQ (Frequently Asked Questions)

### Q: Why does "Freq correction" stay the same for multiple blocks?

**A:** The "Freq correction" column shows the frequency **for that block's current PPM value**, not the accumulated frequency. If multiple blocks have the same PPM (e.g., -0.010000), they'll show the same frequency (2.399976000 MHz), even though the cumulative correction is changing.

### Q: What does "Correction is DONE" mean?

**A:** It means both channels are now perfectly synchronized (0 delay, 0 PPM correction needed). The system has reached stable synchronization!

### Q: Why is there a base correction of -0.040860?

**A:** This is the total accumulated correction needed to bring the hypothetical starting frequency (2.502154 MHz) to the target frequency (2.400000 MHz). It's approximately 4% correction.

### Q: What's the difference between PPM and PPT?

**A:**
- **PPM** (Parts Per Million): 1 PPM = 0.000001 (one millionth)
- **PPT** (Parts Per Thousand): 1 PPT = 0.001 (one thousandth)
- **Conversion**: 1 PPT = 1000 PPM

### Q: How precise is 1 PPM at 2.4 MHz?

**A:** At 2.4 MHz:
- **1 PPM** = 2.4 Hz frequency shift
- **0.000001 PPM** = 0.0024 Hz (2.4 millihertz!) - incredibly precise!

---

## Project Files

- `correction.py` - Main analysis script
- `iq_web.py` - Web visualization tool
- `web_run_iq_analyzer.sh` - Launcher script for web viewer
- `_logs/iq_data/session/` - IQ data storage directory
  - `ch0/block_XXXXX.bin` - Channel 0 data files
  - `ch1/block_XXXXX.bin` - Channel 1 data files
  - `index.csv` - Metadata for all blocks

---

## References

- [KrakenSDR Heimdall DAQ Firmware](https://github.com/krakenrf/heimdall_daq_fw)
- [IQ Sampling Tutorial](https://pysdr.org/content/sampling.html)
- [delay_sync.py source code](https://github.com/krakenrf/heimdall_daq_fw/blob/main/Firmware/_daq_core/delay_sync.py)

---

This project demonstrates the synchronization algorithm used in KrakenSDR direction finding systems.
