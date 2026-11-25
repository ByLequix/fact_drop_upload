import numpy as np, wave, sys
SR = 48000
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 26.0
BPM = 88
beat = 60 / BPM
N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)

def note_hz(m): return 440 * 2 ** ((m - 69) / 12)

def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= N: return
    j = min(N, i + len(sig))
    buf[i:j] += sig[: j - i] * gain

def epiano(freq, length):
    t = np.arange(int(length * SR)) / SR
    env = np.exp(-t * 1.6) * np.minimum(1, t / 0.01)
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    s = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 4)
         + 0.12 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t * 7))
    rel = np.minimum(1, (length - t) / 0.15)
    return s * env * trem * rel

def pad(freq, length):
    t = np.arange(int(length * SR)) / SR
    s = sum(np.sin(2 * np.pi * freq * (1 + d) * t + p) for d, p in ((-0.004, 0), (0, 1.3), (0.005, 2.1)))
    env = np.minimum(1, t / 1.2) * np.minimum(1, (length - t) / 1.2)
    return s / 3 * env

def bass(freq, length):
    t = np.arange(int(length * SR)) / SR
    env = np.minimum(1, t / 0.02) * np.exp(-t * 0.9) * np.minimum(1, (length - t) / 0.08)
    return np.sin(2 * np.pi * freq * t) * env

def kick():
    t = np.arange(int(0.35 * SR)) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)

def hat():
    t = np.arange(int(0.06 * SR)) / SR
    n = rng.standard_normal(len(t)); n = np.diff(n, prepend=0)
    return n * np.exp(-t * 70)

def snap():
    t = np.arange(int(0.2 * SR)) / SR
    n = rng.standard_normal(len(t))
    n = np.convolve(n, np.ones(6) / 6, "same")
    return n * np.exp(-t * 22) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)

# Am9 - Fmaj7 - Cmaj7 - Em7 (2 bars each = 8 beats)
CHORDS = [(57, [60, 64, 67, 71]), (53, [57, 60, 64, 69]), (48, [55, 59, 64, 67]), (52, [55, 59, 62, 67])]
bar = 4 * beat
t = 0.0; ci = 0
while t < DUR:
    root, notes = CHORDS[ci % 4]
    seg = 2 * bar
    for k, m in enumerate(notes):
        add(L, t, pad(note_hz(m), seg + 0.4), 0.05 * (1.0 if k % 2 else 0.8))
        add(R, t, pad(note_hz(m), seg + 0.4), 0.05 * (0.8 if k % 2 else 1.0))
    # e-piano: rhythmic chord stabs, gently strummed
    for b in (0, 1.5, 3, 4, 5.5, 7):
        for k, m in enumerate(notes):
            st = t + b * beat + k * 0.018
            g = 0.06 * (0.75 + 0.25 * rng.random())
            sig = epiano(note_hz(m), beat * 1.6)
            add(L, st, sig, g * (1.1 - k * 0.08)); add(R, st, sig, g * (0.8 + k * 0.08))
    # bass
    for b, mult in ((0, 1), (2.5, 1), (4, 1), (6.5, 1.5)):
        sig = bass(note_hz(root - 12) * mult, beat * 1.4)
        add(L, t + b * beat, sig, 0.22); add(R, t + b * beat, sig, 0.22)
    t += seg; ci += 1

# drums start after intro bar
nb = int(DUR / beat) + 1
for i in range(nb):
    st = i * beat
    if st < bar: continue
    if i % 4 in (0,) or (i % 8 == 6): add(L, st, kick(), 0.35); add(R, st, kick(), 0.35)
    if i % 4 in (1, 3): add(L, st, snap(), 0.10); add(R, st, snap(), 0.12)
    for h in (0, 0.5):
        sw = 0.04 if h else 0
        g = 0.035 if h else 0.05
        add(L, st + h * beat + sw, hat(), g * 0.8); add(R, st + h * beat + sw, hat(), g)

# simple lo-fi warmth: gentle lowpass + soft saturation
def lowpass(x, a=0.25):
    y = np.empty_like(x); acc = 0.0
    # vectorized one-pole via lfilter-like cumulative approach
    from math import exp
    return x  # placeholder replaced below
try:
    from scipy.signal import butter, lfilter
    b, a = butter(2, 6500 / (SR / 2))
    L = lfilter(b, a, L); R = lfilter(b, a, R)
except Exception:
    pass
L = np.tanh(L * 1.3); R = np.tanh(R * 1.3)
# fades
fi = int(1.0 * SR); fo = int(2.0 * SR)
for ch in (L, R):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.abs(L).max(), np.abs(R).max())
st = np.stack([L, R], 1) / peak * 0.8
pcm = (st * 32767).astype(np.int16)
with wave.open("music.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("ok", DUR)
