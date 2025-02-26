#!/usr/bin/env python3
import os
import time
import json
import threading
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import tempfile
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'audio-streamer-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
CHUNK_DURATION = 5  # seconds
STORAGE_DIR = "audio_chunks"
ACTIVE_STREAMS = {}
LISTENERS = {}

# Create storage directory if it doesn't exist
os.makedirs(STORAGE_DIR, exist_ok=True)

class AudioStream:
    def __init__(self, stream_id):
        self.stream_id = stream_id
        self.chunks = []
        self.current_chunk = None
        self.current_chunk_start = 0
        self.is_live = True
        self.lock = threading.Lock()
        
        # Create directory for this stream
        self.stream_dir = os.path.join(STORAGE_DIR, stream_id)
        os.makedirs(self.stream_dir, exist_ok=True)
        
    def start_new_chunk(self):
        if self.current_chunk:
            self._save_chunk()
            
        self.current_chunk = tempfile.NamedTemporaryFile(delete=False, suffix='.raw')
        self.current_chunk_start = time.time()
        return self.current_chunk
    
    def _save_chunk(self):
        chunk_size = os.path.getsize(self.current_chunk.name)
        if chunk_size == 0:
            os.unlink(self.current_chunk.name)
            return
            
        chunk_filename = f"{int(self.current_chunk_start)}.raw"
        chunk_path = os.path.join(self.stream_dir, chunk_filename)
        
        # Copy to permanent storage
        with open(self.current_chunk.name, 'rb') as src, open(chunk_path, 'wb') as dest:
            dest.write(src.read())
        
        self.chunks.append(chunk_filename)
        
        # Notify all listeners
        for listener_id in LISTENERS.get(self.stream_id, []):
            socketio.emit('new_chunk', {'chunk_id': f"{self.stream_id}/{chunk_filename}"}, room=listener_id)
            
        # Cleanup temp file
        os.unlink(self.current_chunk.name)
        logger.info(f"Saved chunk: {chunk_path}")
        
    def add_audio_data(self, data):
        with self.lock:
            if self.current_chunk is None:
                self.start_new_chunk()
                
            # Check if we need to start a new chunk
            if time.time() - self.current_chunk_start > CHUNK_DURATION:
                self.start_new_chunk()
                
            self.current_chunk.write(data)
            self.current_chunk.flush()
            
            # Forward to live listeners
            for listener_id in LISTENERS.get(self.stream_id, []):
                socketio.emit('audio_data', {'stream_id': self.stream_id, 'data': data}, room=listener_id)
                
    def end_stream(self):
        with self.lock:
            if self.current_chunk:
                self._save_chunk()
            self.is_live = False
            logger.info(f"Stream ended: {self.stream_id}")

@app.route('/api/streams', methods=['GET'])
def list_streams():
    # List all active streams
    active = {id: {'is_live': stream.is_live, 'chunks': len(stream.chunks)} 
              for id, stream in ACTIVE_STREAMS.items()}
    return jsonify(active)

@app.route('/api/streams', methods=['POST'])
def create_stream():
    stream_id = str(uuid.uuid4())
    ACTIVE_STREAMS[stream_id] = AudioStream(stream_id)
    logger.info(f"Created new stream: {stream_id}")
    return jsonify({'stream_id': stream_id})

@app.route('/api/streams/<stream_id>/audio', methods=['POST'])
def add_audio(stream_id):
    if stream_id not in ACTIVE_STREAMS:
        return jsonify({'error': 'Stream not found'}), 404
        
    if not ACTIVE_STREAMS[stream_id].is_live:
        return jsonify({'error': 'Stream has ended'}), 400
        
    data = request.get_data()
    ACTIVE_STREAMS[stream_id].add_audio_data(data)
    return jsonify({'success': True})

@app.route('/api/streams/<stream_id>/end', methods=['POST'])
def end_stream(stream_id):
    if stream_id not in ACTIVE_STREAMS:
        return jsonify({'error': 'Stream not found'}), 404
        
    ACTIVE_STREAMS[stream_id].end_stream()
    return jsonify({'success': True})

@app.route('/api/streams/<stream_id>/chunks', methods=['GET'])
def get_chunks(stream_id):
    if stream_id not in ACTIVE_STREAMS:
        return jsonify({'error': 'Stream not found'}), 404
        
    return jsonify({
        'chunks': [f"{stream_id}/{chunk}" for chunk in ACTIVE_STREAMS[stream_id].chunks],
        'is_live': ACTIVE_STREAMS[stream_id].is_live
    })

@app.route('/api/chunks/<path:chunk_path>', methods=['GET'])
def get_chunk_data(chunk_path):
    parts = chunk_path.split('/')
    if len(parts) != 2:
        return jsonify({'error': 'Invalid chunk path'}), 400
        
    stream_id, chunk_filename = parts
    chunk_path = os.path.join(STORAGE_DIR, stream_id, chunk_filename)
    
    if not os.path.exists(chunk_path):
        return jsonify({'error': 'Chunk not found'}), 404
        
    return send_file(chunk_path, mimetype='audio/raw')

@socketio.on('connect')
def socket_connect():
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def socket_disconnect():
    for stream_id in list(LISTENERS.keys()):
        if request.sid in LISTENERS[stream_id]:
            LISTENERS[stream_id].remove(request.sid)
            if not LISTENERS[stream_id]:
                del LISTENERS[stream_id]
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_stream')
def join_stream(data):
    stream_id = data.get('stream_id')
    if not stream_id or stream_id not in ACTIVE_STREAMS:
        emit('error', {'message': 'Invalid stream ID'})
        return
        
    if stream_id not in LISTENERS:
        LISTENERS[stream_id] = set()
    LISTENERS[stream_id].add(request.sid)
    
    logger.info(f"Client {request.sid} joined stream {stream_id}")
    
    emit('joined', {
        'stream_id': stream_id,
        'is_live': ACTIVE_STREAMS[stream_id].is_live,
        'chunks': [f"{stream_id}/{chunk}" for chunk in ACTIVE_STREAMS[stream_id].chunks]
    })

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Audio Streaming Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind the server to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind the server to')
    
    args = parser.parse_args()
    
    logger.info(f"Starting server on {args.host}:{args.port}")
    socketio.run(app, host=args.host, port=args.port) 