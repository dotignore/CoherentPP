# IQ Data Web Viewer

Web-based viewer for RTL-SDR IQ data from KrakenSDR/CoherentPP.

## Directory Structure

The viewer expects the following structure:

```
_logs/iq_data/session/
├── index.csv           (optional - if exists, will be used for indexing)
├── ch0/
│   ├── block_00000.bin
│   ├── block_00001.bin
│   ├── block_00007.bin
│   └── ...
├── ch1/
│   ├── block_00000.bin
│   ├── block_00001.bin
│   └── ...
├── ch2/
│   └── ...
└── ch3/
    └── ...
```

## Index CSV Format (Optional)

If an `index.csv` file exists in the session directory, it will be used instead of scanning directories.

### Format 1: Without Header (Auto-detected)

```csv
1770822898414,0,0,700000000,0,0,ch0/block_00000.bin
1770822898414,0,1,700000000,0,0,ch1/block_00000.bin
1770822898414,0,2,700000000,0,0,ch2/block_00000.bin
1770822898414,0,3,700000000,0,0,ch3/block_00000.bin
1770822898523,1,0,700000000,0,0,ch0/block_00001.bin
1770822898523,1,1,700000000,0,0,ch1/block_00001.bin
```

**Columns (auto-detected):**
1. `Timestamp` - timestamp in milliseconds
2. `Block` - block number (0, 1, 2, ...)
3. `Channel` - channel number (0, 1, 2, 3)
4. `Frequency` - center frequency in Hz
5. `Field1` - additional field
6. `Field2` - additional field  
7. `FilePath` - relative path to .bin file

The viewer will automatically group by block number and detect available channels.

### Format 2: With Header (Custom)

```csv
BlockIndex,ChannelList,Channels
0,"[0, 1, 2, 3]",4
1,"[0, 1, 2, 3]",4
7,"[0, 1, 2, 3]",4
42,"[0, 1]",2
```

**Columns:**
- `BlockIndex` - block number (matches `block_XXXXX.bin` filename)
- `ChannelList` - JSON array of available channels: `"[0, 1, 2, 3]"` or `"[0, 1]"`
- `Channels` - number of channels (optional)

## Running the Viewer

### Quick Start

```bash
cd /Users/dotignore/Documents/GitHub/CoherentPP
./web_run_iq_analyzer.sh
```

The script will:
1. Create virtual environment `.venv_iq` (first run only)
2. Install dependencies: pandas, numpy, plotly, dash
3. Load IQ data from `_logs/iq_data/session/`
4. Start web server at `http://0.0.0.0:8050`

### Manual Run

```bash
python3 -m venv .venv_iq
source .venv_iq/bin/activate
pip install pandas numpy plotly dash
python3 iq_web.py
```

## Accessing the Viewer

Open your browser and go to:
- `http://localhost:8050` (local machine)
- `http://YOUR_IP:8050` (from other devices on network)

## Features

### Visualization Modes

- **IQ** - I and Q components over time
- **FFT** - Frequency spectrum (power vs frequency)
- **CONST** - Constellation diagram (I vs Q)
- **AMP** - Amplitude over time

### Controls

- **Slider** - Navigate through blocks
- **Play/Pause** - Auto-advance through blocks
- **Speed** - Playback speed (ms between frames)
- **Samples** - Number of samples to display
- **Refresh** - Reload data from disk

### Display

- 4 channels displayed vertically
- Synchronized zoom across all channels
- Hover to see values
- Pan and zoom with mouse

## File Format

Binary files contain RTL-SDR IQ samples:
- Format: Unsigned 8-bit bytes
- Interleaved: I,Q,I,Q,I,Q...
- Conversion: `(byte - 127.5) / 127.5` → range [-1.0, +1.0]
- Typical block size: 262144 samples (524288 bytes)

## Troubleshooting

### "No data available"

1. Check that `_logs/iq_data/session/` exists
2. Check that `ch0/` directory exists with `.bin` files
3. Click "Load/Refresh Data" button

### "No sessions found"

The viewer expects data in `_logs/iq_data/session/` (not `session_*`).
Update `BASE_PATHS` in `iq_web.py` if your structure is different:

```python
BASE_PATHS = [
    '_logs/iq_data/session/',
    'path/to/your/data/',
]
```

### Empty plots

Check that block files exist:
```bash
ls -lh _logs/iq_data/session/ch0/
```

Files should be ~524KB each (262144 samples × 2 bytes).

## Architecture

- **iq_web.py** - Main application (Dash/Plotly web app)
- **web_run_iq_analyzer.sh** - Launcher script with venv management
- **correction.py** - Cross-correlation analysis for single block
- **compute_corr_block7_README.md** - Documentation on correlation/PPM correction

## Related Tools

- `correction.py` - Analyze single block correlation (channels 0 & 1)
- `compute_corr_block7.py` - Full analysis with PPM/PPT calculations

See `compute_corr_block7_README.md` for details on frequency correction algorithm.
