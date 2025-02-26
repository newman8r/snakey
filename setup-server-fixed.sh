#!/bin/bash

# Load EC2 instance info
source ./ec2-info.sh

echo "🚀 Setting up audio streaming server on $PUBLIC_DNS..."
echo "Using key file: $KEY_FILE"

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
  pip3 install --user boto3 flask flask-socketio python-socketio numpy

  # Create S3 bucket for audio storage if it doesn't exist
  python3 - << 'PYTHON_EOF'
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3', region_name='us-west-1')
bucket_name = 'emeraldflow-audio-stream'

try:
    s3.head_bucket(Bucket=bucket_name)
    print(f"Bucket {bucket_name} already exists")
except ClientError:
    try:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'us-west-1'}
        )
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