import numpy as np
from numpy.fft import fft, ifft

# Path to data (run from Firmware or substitute your own path)
BASE = "_logs/iq_data/session"
BLOCK = 7
N = 262144   # samples per channel (full block)

def load_ch_bin(path):
    raw = np.fromfile(path, dtype=np.uint8)
    # RTL: consecutive I,Q,I,Q,... -> pairs (I,Q)
    raw = raw.reshape(-1, 2)
    i = raw[:, 0].astype(np.float32) - 127.5
    q = raw[:, 1].astype(np.float32) - 127.5
    return (i + 1j * q).astype(np.complex64)

ch0 = load_ch_bin(f"{BASE}/ch0/block_{BLOCK:05d}.bin")
ch1 = load_ch_bin(f"{BASE}/ch1/block_{BLOCK:05d}.bin")

# Truncate to N samples
ch0 = ch0[:N].copy()
ch1 = ch1[:N].copy()

# As in delay_sync: x = [channel0, zeros], y = [zeros, channel1]
np_zeros = np.zeros(N, dtype=np.complex64)
x_padd = np.concatenate([ch0, np_zeros])
y_padd = np.concatenate([np_zeros, ch1])

x_fft = fft(x_padd)
y_fft = fft(y_padd)
corr = ifft(x_fft.conj() * y_fft)
corr_power = np.abs(corr) ** 2

peak_index = int(np.argmax(corr_power))
delay = N - peak_index

print("Block 7, channels 0 and 1")
print("Correlation length (number of checked shifts k):", len(corr_power))
print("Peak index (peak_index):", peak_index)
print("Channel 1 delay relative to channel 0 (samples): delays[1] = N - peak_index =", delay)
print("Max correlation value:", corr_power[peak_index])

# Several values around the peak (to see the "hill")
half = 5
for i in range(max(0, peak_index - half), min(len(corr_power), peak_index + half + 1)):
    mark = " <-- peak" if i == peak_index else ""
    print(f"  k={i}: correlation = {corr_power[i]:.2e}{mark}")