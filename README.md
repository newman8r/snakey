# 🎵 Audio Streaming and Storage Solution 🎵

A simple but powerful solution for streaming audio between machines, with automatic cloud storage of audio chunks on AWS.

## 📋 Features

- 🔄 Live audio streaming between multiple machines
- ☁️ Automatic storage of audio chunks in AWS S3
- 📱 Simple command-line interface for both sender and receiver
- 🔊 Support for different audio devices, formats, and sample rates
- 🔄 Real-time and archived playback options

## 🚀 Setup

### Prerequisites

- Python 3.6+
- AWS CLI configured with the `emeraldflow` profile
- `pyaudio`, `requests`, `flask`, `flask-socketio` Python packages

### Setting up the Server

1. Clone this repository
2. Make the setup scripts executable:
   ```bash
   chmod +x setup-ec2.sh setup-server.sh
   ```
3. Run the setup-ec2.sh script to create and configure the EC2 instance:
   ```bash
   ./setup-ec2.sh
   ```
   This will:
   - Create a security group with the necessary ports open
   - Create a key pair for SSH access (if it doesn't exist)
   - Launch a t2.micro EC2 instance
   - Wait for the instance to be running
   - Save the instance information to `ec2-info.sh`

4. After the EC2 instance is running, set up the server environment:
   ```bash
   ./setup-server.sh
   ```
   This will:
   - Copy the server code to the EC2 instance
   - Install the required dependencies
   - Create an S3 bucket for audio storage (if it doesn't exist)

5. Start the server on the EC2 instance:
   ```bash
   source ./ec2-info.sh
   ssh -i audio-streamer-key.pem ec2-user@$PUBLIC_DNS "python3 ~/server.py"
   ```

### 📤 Sending Audio

On the machine that will send audio:

1. Install the required Python packages:
   ```bash
   pip install pyaudio requests python-socketio
   ```

2. List available audio input devices:
   ```bash
   python send-audio.py --list-devices
   ```

3. Start streaming audio:
   ```bash
   python send-audio.py --server http://<EC2_PUBLIC_DNS>:8000 --device <DEVICE_INDEX>
   ```

   Replace `<EC2_PUBLIC_DNS>` with your EC2 instance's public DNS name and `<DEVICE_INDEX>` with the index of the audio input device you want to use.

### 📥 Receiving Audio

On the machine that will receive audio:

1. Install the required Python packages:
   ```bash
   pip install pyaudio requests python-socketio
   ```

2. List available audio output devices:
   ```bash
   python receive-audio.py --list-devices
   ```

3. Start listening to a stream:
   ```bash
   python receive-audio.py --server http://<EC2_PUBLIC_DNS>:8000 --stream-id <STREAM_ID> --device <DEVICE_INDEX>
   ```

   Replace `<EC2_PUBLIC_DNS>` with your EC2 instance's public DNS name, `<STREAM_ID>` with the ID of the stream you want to listen to, and `<DEVICE_INDEX>` with the index of the audio output device you want to use.

## 📝 Command Line Options

### Send Audio

```
usage: send-audio.py [-h] --server SERVER [--device DEVICE] [--list-devices]
                    [--channels CHANNELS] [--rate RATE] [--format FORMAT]
                    [--chunk CHUNK]

Audio Streaming Sender

options:
  -h, --help            show this help message and exit
  --server SERVER, -s SERVER
                        Server URL (e.g., http://ec2-xx-xx-xx-xx.compute-1.amazonaws.com:8000)
  --device DEVICE, -d DEVICE
                        Input device index
  --list-devices, -l    List available audio devices and exit
  --channels CHANNELS, -c CHANNELS
                        Number of channels (1=mono, 2=stereo)
  --rate RATE, -r RATE  Sample rate in Hz
  --format FORMAT, -f FORMAT
                        Audio format
  --chunk CHUNK         Frames per buffer
```

### Receive Audio

```
usage: receive-audio.py [-h] --server SERVER --stream-id STREAM_ID
                       [--device DEVICE] [--list-devices]
                       [--channels CHANNELS] [--rate RATE] [--format FORMAT]
                       [--buffer-size BUFFER_SIZE] [--chunk CHUNK]

Audio Streaming Receiver

options:
  -h, --help            show this help message and exit
  --server SERVER, -s SERVER
                        Server URL (e.g., http://ec2-xx-xx-xx-xx.compute-1.amazonaws.com:8000)
  --stream-id STREAM_ID, -i STREAM_ID
                        Stream ID to listen to
  --device DEVICE, -d DEVICE
                        Output device index
  --list-devices, -l    List available audio devices and exit
  --channels CHANNELS, -c CHANNELS
                        Number of channels (1=mono, 2=stereo)
  --rate RATE, -r RATE  Sample rate in Hz
  --format FORMAT, -f FORMAT
                        Audio format
  --buffer-size BUFFER_SIZE, -b BUFFER_SIZE
                        Audio buffer size (number of chunks)
  --chunk CHUNK         Frames per buffer
```

## 🔄 How It Works

1. The server runs on an EC2 instance and provides API endpoints for creating streams, sending audio data, and retrieving audio chunks
2. Audio data is streamed in chunks of 5 seconds by default
3. The audio chunks are stored in an S3 bucket for persistence
4. Clients can connect to the server to send or receive audio
5. Multiple clients can listen to the same stream simultaneously
6. Clients can join a stream at any time and listen to previously recorded chunks

## 📋 API Endpoints

- `POST /api/streams`: Create a new stream
- `GET /api/streams`: List all active streams
- `POST /api/streams/<stream_id>/audio`: Send audio data to a stream
- `POST /api/streams/<stream_id>/end`: End a stream
- `GET /api/streams/<stream_id>/chunks`: Get information about a stream and its chunks
- `GET /api/chunks/<chunk_id>`: Get the audio data for a specific chunk 