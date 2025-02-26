#!/bin/bash

# Load EC2 instance info
source ./ec2-info.sh

# Set the timezone to Pacific time (where AWS US-West-2 region is)
export TZ="America/Los_Angeles"

echo "🚀 Setting up audio streaming server on $PUBLIC_DNS..."
echo "Using timezone: $TZ"
echo "Current time with TZ adjustment: $(date)"

# Copy server code to EC2 instance
echo "Copying server code to EC2..."
scp -i "$KEY_FILE" -o StrictHostKeyChecking=no server.py ec2-user@$PUBLIC_DNS:~/

# Connect to instance and run setup commands
echo "Setting up server environment..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ec2-user@$PUBLIC_DNS << 'EOF'
  # Update system and install dependencies
  sudo yum update -y
  sudo yum install -y python3 python3-pip
  
  # Install required Python packages
  pip3 install --user boto3 flask flask-socketio numpy

  # Create S3 bucket for audio storage if it doesn't exist
  python3 - << 'PYTHON_EOF'
import boto3
from botocore.exceptions import ClientError
import os

# Set timezone to match our script
os.environ['TZ'] = 'America/Los_Angeles'

s3 = boto3.client('s3')
bucket_name = 'emeraldflow-audio-stream'

try:
    s3.head_bucket(Bucket=bucket_name)
    print(f"Bucket {bucket_name} already exists")
except ClientError:
    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} created")
    except ClientError as e:
        print(f"Error creating bucket: {e}")
PYTHON_EOF

  echo "Server setup complete!"
EOF

echo "✅ Server environment setup complete!"
echo ""
echo "To start the server on EC2, run:"
echo "ssh -i $KEY_FILE ec2-user@$PUBLIC_DNS \"python3 ~/server.py\""
echo ""
echo "To send audio to the server, run:"
echo "./send-audio.py --server http://$PUBLIC_DNS:8000 --list-devices"
echo "Then:"
echo "./send-audio.py --server http://$PUBLIC_DNS:8000 --device <DEVICE_INDEX>"
echo ""
echo "To receive audio from the server, run:"
echo "./receive-audio.py --server http://$PUBLIC_DNS:8000 --stream-id <STREAM_ID> --list-devices"
echo "Then:"
echo "./receive-audio.py --server http://$PUBLIC_DNS:8000 --stream-id <STREAM_ID> --device <DEVICE_INDEX>" 