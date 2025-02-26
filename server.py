#!/usr/bin/env python3
import os
import time
import json
import boto3
import threading
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import tempfile
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'audio-streamer-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
S3_BUCKET = 'emeraldflow-audio-stream'
CHUNK_DURATION = 5  # seconds
ACTIVE_STREAMS = {}
LISTENERS = {}

# Initialize S3 client
s3 = boto3.client('s3', region_name='us-west-1')

class AudioStream:
    def __init__(self, stream_id):
        self.stream_id = stream_id
        self.chunks = []
        self.current_chunk = None
        self.current_chunk_start = 0
        self.is_live = True
        self.lock = threading.Lock()
        
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
            
        chunk_id = f"{self.stream_id}/{int(self.current_chunk_start)}.raw"
        self.chunks.append(chunk_id)
        
        # Upload to S3
        with open(self.current_chunk.name, 'rb') as f:
            s3.upload_fileobj(f, S3_BUCKET, chunk_id)
        
        # Notify all listeners
        for listener_id in LISTENERS.get(self.stream_id, []):
            socketio.emit('new_chunk', {'chunk_id': chunk_id}, room=listener_id)
            
        # Cleanup local file
        os.unlink(self.current_chunk.name)
        
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
        'chunks': ACTIVE_STREAMS[stream_id].chunks,
        'is_live': ACTIVE_STREAMS[stream_id].is_live
    })

@app.route('/api/chunks/<path:chunk_id>', methods=['GET'])
def get_chunk_data(chunk_id):
    # Retrieve the chunk from S3
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        s3.download_fileobj(S3_BUCKET, chunk_id, temp_file)
        temp_file.close()
        return send_file(temp_file.name, mimetype='audio/raw')
    except Exception as e:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def socket_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def socket_disconnect():
    for stream_id in list(LISTENERS.keys()):
        if request.sid in LISTENERS[stream_id]:
            LISTENERS[stream_id].remove(request.sid)
            if not LISTENERS[stream_id]:
                del LISTENERS[stream_id]

@socketio.on('join_stream')
def join_stream(data):
    stream_id = data.get('stream_id')
    if not stream_id or stream_id not in ACTIVE_STREAMS:
        emit('error', {'message': 'Invalid stream ID'})
        return
        
    if stream_id not in LISTENERS:
        LISTENERS[stream_id] = set()
    LISTENERS[stream_id].add(request.sid)
    
    emit('joined', {
        'stream_id': stream_id,
        'is_live': ACTIVE_STREAMS[stream_id].is_live,
        'chunks': ACTIVE_STREAMS[stream_id].chunks
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000) 