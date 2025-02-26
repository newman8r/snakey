#!/usr/bin/env python3
import sys
import time
import requests
import argparse
import pyaudio
import threading
from socketio import Client
import json

def parse_args():
    parser = argparse.ArgumentParser(description='Audio Streaming Sender')
    parser.add_argument('--server', '-s', required=True, help='Server URL (e.g., http://192.168.1.100:8000)')
    parser.add_argument('--device', '-d', type=int, default=None, help='Input device index')
    parser.add_argument('--list-devices', '-l', action='store_true', help='List available audio devices and exit')
    parser.add_argument('--channels', '-c', type=int, default=1, help='Number of channels (1=mono, 2=stereo)')
    parser.add_argument('--rate', '-r', type=int, default=44100, help='Sample rate in Hz')
    parser.add_argument('--format', '-f', type=int, default=pyaudio.paInt16, help='Audio format')
    parser.add_argument('--chunk', type=int, default=1024, help='Frames per buffer')
    
    return parser.parse_args()

def list_audio_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    print("Available audio input devices:")
    for i in range(numdevices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        if device_info.get('maxInputChannels') > 0:
            print(f"Device {i}: {device_info.get('name')}")
    
    p.terminate()

def create_stream(server_url):
    response = requests.post(f"{server_url}/api/streams")
    if response.status_code != 200:
        raise Exception(f"Failed to create stream: {response.text}")
    
    data = response.json()
    return data["stream_id"]

def stream_audio(server_url, stream_id, args):
    p = pyaudio.PyAudio()
    
    def callback(in_data, frame_count, time_info, status):
        try:
            requests.post(
                f"{server_url}/api/streams/{stream_id}/audio",
                data=in_data,
                headers={"Content-Type": "application/octet-stream"}
            )
        except Exception as e:
            print(f"Error sending audio: {e}")
        return (in_data, pyaudio.paContinue)
    
    stream = p.open(
        format=args.format,
        channels=args.channels,
        rate=args.rate,
        input=True,
        input_device_index=args.device,
        frames_per_buffer=args.chunk,
        stream_callback=callback
    )
    
    print(f"🎙️ Started streaming audio from device to {server_url}")
    print(f"Stream ID: {stream_id}")
    print("Press Ctrl+C to stop streaming")
    
    try:
        while stream.is_active():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        try:
            requests.post(f"{server_url}/api/streams/{stream_id}/end")
            print("Stream ended")
        except Exception as e:
            print(f"Error ending stream: {e}")

def main():
    args = parse_args()
    
    if args.list_devices:
        list_audio_devices()
        return
    
    server_url = args.server
    
    # Create a new stream
    stream_id = create_stream(server_url)
    print(f"Created new stream with ID: {stream_id}")
    
    # Start streaming audio
    stream_audio(server_url, stream_id, args)

if __name__ == "__main__":
    main() 