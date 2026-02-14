#!/usr/bin/env python3
"""
IQ Data Web Viewer - view IQ data through web browser
Updated version for new file structure
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State, callback_context
import os
from datetime import datetime
import io

# Initialize Dash application
app = dash.Dash(__name__)

# PATH CONFIGURATION - for _logs/iq_data/session/ structure
BASE_PATHS = [
    '_logs/iq_data/session/',
    os.path.expanduser('_logs/iq_data/session/'),
    '_logs/iq_data/session/',
]

def find_data_path():
    """Find existing data path"""
    for path in BASE_PATHS:
        if os.path.exists(path):
            # Check for ch0 or index.csv
            ch0_path = os.path.join(path, 'ch0')
            index_path = os.path.join(path, 'index.csv')
            if os.path.exists(ch0_path) or os.path.exists(index_path):
                print(f"✓ Data path found: {path}")
                if os.path.exists(index_path):
                    print(f"✓ Found index.csv")
                if os.path.exists(ch0_path):
                    print(f"✓ Found ch0 directory")
                return path
    
    print("⚠ WARNING: Data path not found!")
    print(f"Looking for directories in: {BASE_PATHS}")
    return BASE_PATHS[0]

# Find correct path on startup
DATA_PATH = find_data_path()

def load_sessions_index():
    """Load sessions and blocks index"""
    if not os.path.exists(DATA_PATH):
        print(f"Data path {DATA_PATH} not found")
        return None
    
    # Check for index.csv
    index_path = os.path.join(DATA_PATH, 'index.csv')
    
    if os.path.exists(index_path):
        print(f"Loading index from {index_path}")
        try:
            # Check if CSV has header
            with open(index_path, 'r') as f:
                first_line = f.readline().strip()
            
            # If first line contains letters, it's a header
            has_header = any(c.isalpha() for c in first_line.split(',')[0])
            
            if has_header:
                # Read with header
                df_raw = pd.read_csv(index_path)
            else:
                # Read without header, assign column names
                # Format: timestamp,block,channel,frequency,field1,field2,filepath
                df_raw = pd.read_csv(index_path, header=None, 
                                     names=['Timestamp', 'Block', 'Channel', 'Frequency', 'Field1', 'Field2', 'FilePath'])
            
            print(f"✓ Loaded {len(df_raw)} records from index.csv")
            print(f"  Columns: {list(df_raw.columns)}")
            
            # Convert to required format (group by blocks)
            if 'Block' in df_raw.columns:
                # Group by blocks and collect channel list
                blocks_data = []
                for block_num in sorted(df_raw['Block'].unique()):
                    block_rows = df_raw[df_raw['Block'] == block_num]
                    channels = sorted(block_rows['Channel'].unique())
                    blocks_data.append({
                        'Session': 'session',
                        'BlockIndex': int(block_num),
                        'Channels': len(channels),
                        'ChannelList': channels,
                        'Path': DATA_PATH
                    })
                
                df = pd.DataFrame(blocks_data)
                print(f"✓ Processed into {len(df)} unique blocks")
                return df
            
            # If format is different, try to adapt
            if 'BlockIndex' not in df_raw.columns and 'block' in df_raw.columns:
                df_raw['BlockIndex'] = df_raw['block']
            
            # Add Session and Path columns if missing
            if 'Session' not in df_raw.columns:
                df_raw['Session'] = 'session'
            if 'Path' not in df_raw.columns:
                df_raw['Path'] = DATA_PATH
            
            if 'ChannelList' not in df_raw.columns:
                # Assume all 4 channels are present
                df_raw['ChannelList'] = [[0, 1, 2, 3]] * len(df_raw)
                df_raw['Channels'] = 4
            
            return df_raw
        except Exception as e:
            print(f"Error reading index.csv: {e}")
            import traceback
            traceback.print_exc()
    
    # If no index.csv, scan directories
    print("No index.csv found, scanning directories...")
    try:
        # Look for ch0 to determine blocks
        ch0_path = os.path.join(DATA_PATH, 'ch0')
        if not os.path.exists(ch0_path):
            print(f"ch0 directory not found in {DATA_PATH}")
            return None
        
        # Get list of blocks
        blocks = [f for f in os.listdir(ch0_path) if f.startswith('block_') and f.endswith('.bin')]
        
        records = []
        for block_file in sorted(blocks):
            block_num = int(block_file.replace('block_', '').replace('.bin', ''))
            
            # Check for all 4 channels
            channels_exist = []
            for ch in range(4):
                ch_file = os.path.join(DATA_PATH, f'ch{ch}', block_file)
                if os.path.exists(ch_file):
                    channels_exist.append(ch)
            
            if channels_exist:
                records.append({
                    'Session': 'session',
                    'BlockIndex': block_num,
                    'Channels': len(channels_exist),
                    'ChannelList': channels_exist,
                    'Path': DATA_PATH
                })
        
        df = pd.DataFrame(records)
        print(f"✓ Loaded {len(records)} blocks from directory scan")
        print(f"  Blocks: {len(df)} found")
        
        return df
    except Exception as e:
        print(f"Error scanning directories: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_iq_block(block_index, session, df):
    """Load IQ data for specific block"""
    # Filter by BlockIndex and Session
    block_data = df[(df['BlockIndex'] == block_index) & (df['Session'] == session)]
    
    if block_data.empty:
        print(f"  Block {block_index} not found in session {session}")
        return {}
    
    print(f"  Loading block {block_index} from session {session}")
    
    row = block_data.iloc[0]
    session_path = row['Path']
    channels_raw = row['ChannelList']
    
    # Convert ChannelList to list if it's a string
    if isinstance(channels_raw, str):
        # Parse string like "[0, 1, 2, 3]" or "0,1,2,3"
        import json
        try:
            channels = json.loads(channels_raw)
        except:
            channels = [int(x.strip()) for x in channels_raw.strip('[]').split(',') if x.strip().isdigit()]
    elif isinstance(channels_raw, list):
        channels = channels_raw
    else:
        # Default: try all 4 channels
        channels = [0, 1, 2, 3]
    
    print(f"  Channels to load: {channels}")
    
    iq_data = {}
    
    for ch in channels:
        filepath = os.path.join(session_path, f'ch{ch}', f'block_{block_index:05d}.bin')
        
        print(f"    Channel {ch}: {filepath}")
        
        if os.path.exists(filepath):
            try:
                file_size = os.path.getsize(filepath)
                print(f"      File exists, size: {file_size} bytes")
                
                # Read IQ data (RTL-SDR format: unsigned 8-bit)
                iq_raw = np.fromfile(filepath, dtype=np.uint8)
                
                if len(iq_raw) > 0:
                    # RTL-SDR format: unsigned 8-bit (0-255)
                    # Convert to range -1.0 to +1.0
                    I = (iq_raw[0::2].astype(np.float32) - 127.5) / 127.5
                    Q = (iq_raw[1::2].astype(np.float32) - 127.5) / 127.5
                    
                    iq_data[ch] = {'I': I, 'Q': Q, 'type': 'DATA'}
                    print(f"      Loaded {len(I)} I/Q samples")
                else:
                    print(f"      Empty file")
                    
            except Exception as e:
                print(f"      Error loading file: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"      File NOT found")
    
    print(f"  Total channels loaded: {len(iq_data)}")
    return iq_data

def create_iq_plots(iq_data, mode='IQ', n_samples=1000, sample_rate=2.4e6):
    """Create IQ data plots - vertical layout with synchronized zoom"""
    # 4 rows for 4 channels (channel 0-3), 1 column
    num_channels = 4
    fig = make_subplots(
        rows=num_channels, cols=1,
        subplot_titles=[f'Channel {i}' for i in range(num_channels)],
        shared_xaxes=True,  # Synchronized zoom
        vertical_spacing=0.05
    )
    
    colors = ['blue', 'red', 'green', 'orange']
    
    # Calculate time parameters
    time_per_sample = 1.0 / sample_rate  # seconds per sample
    time_array = np.arange(n_samples) * time_per_sample * 1000  # in milliseconds
    
    for channel in range(num_channels):
        row = channel + 1
        col = 1
        
        if channel in iq_data and len(iq_data[channel]['I']) > 0:
            I = iq_data[channel]['I'][:n_samples]
            Q = iq_data[channel]['Q'][:n_samples]
            frame_type = iq_data[channel].get('type', 'DATA')
            
            # Add frame type to title
            fig.layout.annotations[channel].text = f'Channel {channel} ({frame_type})'
            
            if mode == 'IQ':
                fig.add_trace(
                    go.Scatter(x=time_array[:len(I)], y=I, mode='lines', name='I', 
                              line=dict(color='blue', width=1)),
                    row=row, col=col
                )
                fig.add_trace(
                    go.Scatter(x=time_array[:len(Q)], y=Q, mode='lines', name='Q',
                              line=dict(color='red', width=1)),
                    row=row, col=col
                )
                if row == num_channels:
                    fig.update_xaxes(title_text="Time (ms)", row=row, col=col)
                
            elif mode == 'FFT':
                if len(I) > 0:
                    complex_signal = I + 1j * Q
                    fft_data = np.fft.fftshift(np.fft.fft(complex_signal))
                    fft_mag = 20 * np.log10(np.abs(fft_data) + 1e-10)
                    freqs = np.linspace(-sample_rate/2, sample_rate/2, len(fft_data)) / 1e6
                    
                    fig.add_trace(
                        go.Scatter(x=freqs, y=fft_mag, mode='lines',
                                  line=dict(color=colors[channel], width=1)),
                        row=row, col=col
                    )
                if row == num_channels:
                    fig.update_xaxes(title_text="Frequency (MHz)", row=row, col=col)
                fig.update_yaxes(title_text="Power (dB)", row=row, col=col)
                
            elif mode == 'CONST':
                if len(I) > 10:
                    fig.add_trace(
                        go.Scatter(x=I[::10], y=Q[::10], mode='markers',
                                  marker=dict(size=2, color=colors[channel])),
                        row=row, col=col
                    )
                fig.update_xaxes(title_text="I", row=row, col=col)
                fig.update_yaxes(title_text="Q", row=row, col=col)
                
            elif mode == 'AMP':
                if len(I) > 0:
                    amplitude = np.sqrt(I**2 + Q**2)
                    fig.add_trace(
                        go.Scatter(x=time_array[:len(amplitude)], y=amplitude, mode='lines',
                                  line=dict(color=colors[channel], width=1)),
                        row=row, col=col
                    )
                if row == num_channels:
                    fig.update_xaxes(title_text="Time (ms)", row=row, col=col)
                fig.update_yaxes(title_text="Amplitude", row=row, col=col)
        else:
            # Add empty plot if no data
            fig.add_trace(
                go.Scatter(x=[0], y=[0], mode='lines', showlegend=False),
                row=row, col=col
            )
            fig.layout.annotations[channel].text = f'Channel {channel} (No data)'
    
    # Calculate parameters for title
    duration_ms = n_samples / sample_rate * 1000
    bandwidth_mhz = sample_rate / 1e6
    
    fig.update_layout(
        height=1000,
        showlegend=False,
        title_text=f"Mode: {mode} | Duration: {duration_ms:.2f} ms | Bandwidth: {bandwidth_mhz:.1f} MHz | Sample Rate: {sample_rate/1e6:.1f} MS/s",
        hovermode='x unified'
    )
    
    return fig

# Application layout
app.layout = html.Div([
    html.H1("KrakenSDR IQ Frame Analyzer", style={'text-align': 'center'}),
    
    html.Div([
        html.Div([
            html.Button('Load/Refresh Data', id='refresh-button', n_clicks=0),
        ], style={'display': 'inline-block', 'margin': '10px'}),
        
        html.Div([
            html.Label("Display Mode:"),
            dcc.RadioItems(
                id='mode-selector',
                options=[
                    {'label': 'I/Q', 'value': 'IQ'},
                    {'label': 'FFT', 'value': 'FFT'},
                    {'label': 'Constellation', 'value': 'CONST'},
                    {'label': 'Amplitude', 'value': 'AMP'}
                ],
                value='IQ',
                inline=True
            ),
        ], style={'display': 'inline-block', 'margin': '10px'}),
        
        html.Div([
            html.Label("Samples:"),
            dcc.Input(id='samples-input', type='number', value=1000, min=100, max=100000),
        ], style={'display': 'inline-block', 'margin': '10px'}),
        
        html.Div([
            html.Label("Frame Type Filter:"),
            dcc.Dropdown(
                id='frame-type-filter',
                options=[
                    {'label': 'All', 'value': 'all'},
                    {'label': 'DATA (0)', 'value': 0},
                    {'label': 'DUMMY (1)', 'value': 1},
                    {'label': 'RAMP (2)', 'value': 2},
                    {'label': 'CAL (3)', 'value': 3},
                    {'label': 'TRIGW (4)', 'value': 4}
                ],
                value='all',
                style={'width': '150px'}
            ),
        ], style={'display': 'inline-block', 'margin': '10px'}),
    ], style={'text-align': 'center'}),
    
    html.Div([
        html.Label("DAQ Block:"),
        dcc.Slider(
            id='block-slider',
            min=0,
            max=100,
            value=0,
            marks={},
            tooltip={"placement": "bottom", "always_visible": True}
        ),
    ], style={'margin': '20px'}),
    
    html.Div(id='info-div', style={'text-align': 'center', 'margin': '10px'}),
    
    dcc.Graph(id='iq-plot'),
    
    dcc.Interval(
        id='interval-component',
        interval=500,
        n_intervals=0,
        disabled=True
    ),
    
    html.Div([
        html.Button('▶ Play', id='play-button', n_clicks=0),
        html.Label("Speed (ms):", style={'margin-left': '20px'}),
        dcc.Input(id='speed-input', type='number', value=500, min=100, max=5000, style={'width': '80px'}),
    ], style={'text-align': 'center', 'margin': '10px'}),
    
    html.Div(id='path-info', style={'text-align': 'center', 'margin': '10px', 'color': 'gray', 'font-size': '12px'}),
    
    # Hidden state
    dcc.Store(id='frames-data-store'),
    dcc.Store(id='play-state', data={'playing': False}),
    dcc.Store(id='current-block', data={'block': 0}),
])

# Callback for path
@app.callback(
    Output('path-info', 'children'),
    Input('refresh-button', 'n_clicks')
)
def show_data_path(n_clicks):
    return f"Data path: {DATA_PATH}"

# Callback for data loading
@app.callback(
    Output('frames-data-store', 'data'),
    Output('block-slider', 'min'),
    Output('block-slider', 'max'),
    Output('block-slider', 'marks'),
    Output('current-block', 'data'),
    Input('refresh-button', 'n_clicks'),
    State('frame-type-filter', 'value')
)
def load_data(n_clicks, frame_type_filter):
    df = load_sessions_index()
    if df is None:
        return {}, 0, 100, {}, {'block': 0, 'session': ''}
    
    # Use all data (frame type filter no longer used)
    df_filtered = df
    
    if df_filtered.empty:
        return {}, 0, 100, {}, {'block': 0, 'session': ''}
    
    # Get unique blocks (across all sessions)
    blocks = sorted(df_filtered['BlockIndex'].unique())
    if not blocks:
        return {}, 0, 100, {}, {'block': 0, 'session': ''}
    
    # Create mapping
    block_mapping = {i: block for i, block in enumerate(blocks)}
    
    # Marks for slider
    step = max(1, len(blocks) // 10)
    marks = {}
    for i, block in enumerate(blocks):
        if i % step == 0 or i == 0 or i == len(blocks) - 1:
            marks[i] = str(block)
    
    # Save data
    frames_data = {
        'df_json': df_filtered.to_json(orient='records', date_format='iso'),
        'block_mapping': block_mapping,
        'blocks': blocks
    }
    
    return frames_data, 0, len(blocks) - 1, marks, {'block': 0}

# Callback for slider and play
@app.callback(
    Output('block-slider', 'value'),
    Output('play-state', 'data'),
    Output('interval-component', 'disabled'),
    Output('play-button', 'children'),
    Input('block-slider', 'value'),
    Input('play-button', 'n_clicks'),
    Input('interval-component', 'n_intervals'),
    State('play-state', 'data'),
    State('current-block', 'data'),
    State('block-slider', 'max'),
    State('block-slider', 'min')
)
def handle_block_changes(slider_value, play_clicks, n_intervals, play_state, current_block, max_val, min_val):
    ctx = callback_context
    
    if not ctx.triggered:
        return slider_value, play_state, True, '▶ Play'
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'play-button':
        new_playing = not play_state['playing']
        button_text = '⏸ Pause' if new_playing else '▶ Play'
        return slider_value, {'playing': new_playing}, not new_playing, button_text
    
    elif trigger_id == 'interval-component' and play_state['playing']:
        if slider_value < max_val:
            new_value = slider_value + 1
        else:
            new_value = min_val
        button_text = '⏸ Pause' if play_state['playing'] else '▶ Play'
        return new_value, play_state, not play_state['playing'], button_text
    
    elif trigger_id == 'block-slider':
        button_text = '⏸ Pause' if play_state['playing'] else '▶ Play'
        return slider_value, play_state, not play_state['playing'], button_text
    
    button_text = '⏸ Pause' if play_state['playing'] else '▶ Play'
    return slider_value, play_state, not play_state['playing'], button_text

# Callback for plots
@app.callback(
    Output('iq-plot', 'figure'),
    Output('info-div', 'children'),
    Input('block-slider', 'value'),
    Input('mode-selector', 'value'),
    Input('samples-input', 'value'),
    State('frames-data-store', 'data')
)
def update_plot(slider_position, mode, n_samples, frames_data):
    print(f"\n=== update_plot ===")
    print(f"Slider position: {slider_position}, Mode: {mode}, Samples: {n_samples}")
    
    if not frames_data:
        print("No frames data")
        empty_fig = go.Figure()
        empty_fig.update_layout(height=1000)
        return empty_fig, "No data available. Please click 'Load/Refresh Data'."
    
    # Extract data
    try:
        df = pd.read_json(io.StringIO(frames_data['df_json']), orient='records')
        
        block_mapping = frames_data.get('block_mapping', {})
        
        # Get real block number
        if block_mapping:
            block_mapping = {int(k): v for k, v in block_mapping.items()}
            block_index = block_mapping.get(slider_position, 0)
            print(f"Mapped position {slider_position} to block {block_index}")
        else:
            blocks = sorted(df['BlockIndex'].unique())
            if slider_position < len(blocks):
                block_index = blocks[slider_position]
            else:
                block_index = blocks[0]
            print(f"Using fallback: position {slider_position} -> block {block_index}")
    except Exception as e:
        print(f"Error parsing data: {e}")
        import traceback
        traceback.print_exc()
        empty_fig = go.Figure()
        empty_fig.update_layout(height=1000)
        return empty_fig, "Error parsing data"
    
    # Find session for this block
    block_data = df[df['BlockIndex'] == block_index]
    if block_data.empty:
        print(f"Block {block_index} not found")
        empty_fig = go.Figure()
        empty_fig.update_layout(height=1000)
        return empty_fig, f"Block {block_index} not found"
    
    session = block_data.iloc[0]['Session']
    
    print(f"Loading IQ data for block {block_index} from session {session}")
    iq_data = load_iq_block(block_index, session, df)
    
    if not iq_data:
        print("No IQ data loaded")
        empty_fig = go.Figure()
        empty_fig.update_layout(height=1000)
        return empty_fig, f"No IQ data for block {block_index}"
    
    print(f"Loaded IQ data for channels: {list(iq_data.keys())}")
    
    # Sample rate fixed for RTLSDR
    sample_rate = 2.4e6
    
    # Create plot
    try:
        fig = create_iq_plots(iq_data, mode, n_samples, sample_rate)
        print("Figure created successfully")
    except Exception as e:
        print(f"Error creating figure: {e}")
        empty_fig = go.Figure()
        empty_fig.update_layout(height=1000)
        return empty_fig, f"Error creating plot: {str(e)}"
    
    # Block information
    if not block_data.empty:
        block_info = block_data.iloc[0]
        
        info = (f"Position: {slider_position + 1}/{len(block_mapping) if block_mapping else 1} | "
                f"Session: {session} | "
                f"Block: #{block_index} | "
                f"Channels: {len(iq_data)} | "
                f"Samples: {n_samples}")
    else:
        info = f"Block: {block_index}"
    
    print(f"Returning figure with info: {info}")
    return fig, info

# Callback for speed
@app.callback(
    Output('interval-component', 'interval'),
    Input('speed-input', 'value')
)
def update_interval_speed(speed):
    return speed if speed else 500

if __name__ == '__main__':
    print("="*60)
    print(" "*15 + "KrakenSDR IQ Frame Viewer")
    print("="*60)
    print(f"Data path: {DATA_PATH}")
    
    # Check data availability
    df = load_sessions_index()
    if df is not None and len(df) > 0:
        print(f"\nDataFrame info:")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        
        if 'BlockIndex' in df.columns:
            unique_blocks = df['BlockIndex'].nunique()
            min_block = df['BlockIndex'].min()
            max_block = df['BlockIndex'].max()
            print(f"✓ Found {unique_blocks} unique blocks (range: {min_block} to {max_block})")
        
        if 'Session' in df.columns:
            unique_sessions = df['Session'].nunique()
            print(f"✓ Found {unique_sessions} session(s)")
            
            # Session statistics
            session_stats = df.groupby('Session').size()
            print("\nSession statistics:")
            for session, count in session_stats.items():
                print(f"  {session}: {count} blocks")
        
        if 'Channels' in df.columns:
            print(f"\nChannel statistics:")
            channel_stats = df['Channels'].value_counts()
            for num_ch, count in channel_stats.items():
                print(f"  {num_ch} channels: {count} blocks")
    
    print("-"*60)
    print("Starting server at http://localhost:8050")
    print("="*60)
    
    app.run(debug=False, host='0.0.0.0', port=8050)