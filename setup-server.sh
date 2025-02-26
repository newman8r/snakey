#!/bin/bash

# Load EC2 instance info
source ./ec2-info.sh

echo "Setting up audio streaming server on $PUBLIC_DNS..."

# Copy server code to EC2 instance
scp -i audio-streamer-key.pem server.py ec2-user@$PUBLIC_DNS:~/

# Connect to instance and run setup commands
ssh -i audio-streamer-key.pem ec2-user@$PUBLIC_DNS << 'EOF'
  # Update system and install dependencies
  sudo yum update -y
  sudo yum install -y python3 python3-pip
  
  # Install required Python packages
  pip3 install --user boto3 flask flask-socketio numpy

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

echo "🎉 Server environment setup complete!"