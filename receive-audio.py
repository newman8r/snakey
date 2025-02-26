#!/usr/bin/env python3
import sys
import time
import argparse
import requests
import pyaudio
import threading
import queue
from socketio import Client
import json

def parse_args():
    parser = argparse.ArgumentParser(description='Audio Streaming Receiver')
    parser.add_argument('--server', '-s', required=True, help='Server URL (e.g., http://ec2-xx-xx-xx-xx.compute-1.amazonaws.com:8000)')
    parser.add_argument('--stream-id', '-i', required=True, help='Stream ID to listen to')
    parser.add_argument('--device', '-d', type=int, default=None, help='Output device index')
    parser.add_argument('--list-devices', '-l', action='store_true', help='List available audio devices and exit')
    parser.add_argument('--channels', '-c', type=int, default=1, help='Number of channels (1=mono, 2=stereo)')
    parser.add_argument('--rate', '-r', type=int, default=44100, help='Sample rate in Hz')
    parser.add_argument('--format', '-f', type=int, default=pyaudio.paInt16, help='Audio format')
    parser.add_argument('--buffer-size', '-b', type=int, default=10, help='Audio buffer size (number of chunks)')
    parser.add_argument('--chunk', type=int, default=1024, help='Frames per buffer')
    
    return parser.parse_args()

def list_audio_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    print("Available audio output devices:")
    for i in range(numdevices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        if device_info.get('maxOutputChannels') > 0:
            print(f"Device {i}: {device_info.get('name')}")
    
    p.terminate()

def get_stream_info(server_url, stream_id):
    try:
        response = requests.get(f"{server_url}/api/streams/{stream_id}/chunks")
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return None
        
        return response.json()
    except Exception as e:
        print(f"Error getting stream info: {e}")
        return None

def play_chunk(server_url, chunk_id, audio_queue):
    try:
        response = requests.get(f"{server_url}/api/chunks/{chunk_id}")
        if response.status_code == 200:
            audio_queue.put(response.content)
    except Exception as e:
        print(f"Error fetching chunk {chunk_id}: {e}")

def connect_to_socket_io(server_url, stream_id, audio_queue):
    sio = Client()
    
    @sio.event
    def connect():
        print(f"🔌 Connected to server! Joining stream {stream_id}")
        sio.emit('join_stream', {'stream_id': stream_id})
    
    @sio.event
    def disconnect():
        print("Disconnected from server")
    
    @sio.on('joined')
    def on_joined(data):
        print(f"Joined stream. Live: {data['is_live']}, Chunks: {len(data['chunks'])}")
        
        # Queue up existing chunks for playback
        for chunk_id in data['chunks']:
            threading.Thread(target=play_chunk, args=(server_url, chunk_id, audio_queue)).start()
    
    @sio.on('audio_data')
    def on_audio_data(data):
        if data['stream_id'] == stream_id:
            audio_queue.put(data['data'])
    
    @sio.on('new_chunk')
    def on_new_chunk(data):
        threading.Thread(target=play_chunk, args=(server_url, data['chunk_id'], audio_queue)).start()
    
    @sio.on('error')
    def on_error(data):
        print(f"Error: {data['message']}")
    
    try:
        sio.connect(server_url)
        return sio
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None

def play_audio(args, audio_queue):
    p = pyaudio.PyAudio()
    
    # Open audio stream
    stream = p.open(
        format=args.format,
        channels=args.channels,
        rate=args.rate,
        output=True,
        output_device_index=args.device,
        frames_per_buffer=args.chunk
    )
    
    print("🔊 Audio playback started")
    
    try:
        while True:
            try:
                data = audio_queue.get(timeout=1)
                stream.write(data)
            except queue.Empty:
                # No data available, just continue
                pass
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("Audio playback stopped")

def main():
    args = parse_args()
    
    if args.list_devices:
        list_audio_devices()
        return
    
    server_url = args.server
    stream_id = args.stream_id
    
    # Check if stream exists
    stream_info = get_stream_info(server_url, stream_id)
    if not stream_info:
        print(f"Stream {stream_id} not found")
        return
    
    print(f"Found stream {stream_id}")
    print(f"Live: {stream_info['is_live']}")
    print(f"Chunks: {len(stream_info['chunks'])}")
    
    # Create audio queue for communication between threads
    audio_queue = queue.Queue(maxsize=args.buffer_size)
    
    # Connect to socket.io server
    sio = connect_to_socket_io(server_url, stream_id, audio_queue)
    if not sio:
        return
    
    # Start audio playback in a separate thread
    playback_thread = threading.Thread(target=play_audio, args=(args, audio_queue))
    playback_thread.daemon = True
    playback_thread.start()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        sio.disconnect()

if __name__ == "__main__":
    main() 