#!/bin/bash

echo "🚀 Setting up EC2 instance with timezone adjustment..."

# Set the timezone to Pacific time (where AWS US-West-2 region is)
export TZ="America/Los_Angeles"

echo "Using timezone: $TZ"
echo "Current time with TZ adjustment: $(date)"

# Create security group for our audio streaming server
echo "Creating security group for audio streaming..."
SECURITY_GROUP_ID=$(TZ=$TZ aws ec2 create-security-group \
  --group-name AudioStreamerSG-$(date +%s) \
  --description "Security group for audio streaming server" \
  --profile emeraldflow \
  --output text \
  --query 'GroupId')

if [ -z "$SECURITY_GROUP_ID" ]; then
  echo "❌ Failed to create security group. Check AWS credentials."
  exit 1
fi

echo "✅ Security Group created: $SECURITY_GROUP_ID"

# Add inbound rules for SSH and our custom audio ports
echo "Adding inbound rules..."
TZ=$TZ aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --profile emeraldflow

# Port for audio streaming
TZ=$TZ aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0 \
  --profile emeraldflow

# Create key pair for SSH access if it doesn't exist
KEY_NAME="audio-streamer-key-$(date +%s)"
KEY_FILE="$KEY_NAME.pem"

echo "Creating new key pair: $KEY_NAME..."
TZ=$TZ aws ec2 create-key-pair \
  --key-name $KEY_NAME \
  --query 'KeyMaterial' \
  --profile emeraldflow \
  --output text > $KEY_FILE

if [ ! -s "$KEY_FILE" ]; then
  echo "❌ Failed to create key pair. Check AWS credentials."
  exit 1
fi

chmod 400 $KEY_FILE
echo "✅ Key pair created: $KEY_FILE"

# Launch EC2 instance
echo "Launching EC2 instance..."
INSTANCE_ID=$(TZ=$TZ aws ec2 run-instances \
  --image-id ami-0c7217cdde317cfec \
  --count 1 \
  --instance-type t2.micro \
  --key-name $KEY_NAME \
  --security-group-ids $SECURITY_GROUP_ID \
  --profile emeraldflow \
  --output text \
  --query 'Instances[0].InstanceId')

if [ -z "$INSTANCE_ID" ]; then
  echo "❌ Failed to launch EC2 instance. Check AWS credentials."
  exit 1
fi

echo "✅ Instance launched: $INSTANCE_ID"

# Wait for instance to be running
echo "Waiting for instance to be running..."
TZ=$TZ aws ec2 wait instance-running \
  --instance-ids $INSTANCE_ID \
  --profile emeraldflow

# Get public DNS name
PUBLIC_DNS=$(TZ=$TZ aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicDnsName' \
  --profile emeraldflow \
  --output text)

PUBLIC_IP=$(TZ=$TZ aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --profile emeraldflow \
  --output text)

echo "🎉 EC2 instance is now running!"
echo "Public DNS: $PUBLIC_DNS"
echo "Public IP: $PUBLIC_IP"
echo "Instance ID: $INSTANCE_ID"

# Save instance info for later use
cat > ec2-info.sh << EOF
PUBLIC_DNS="$PUBLIC_DNS"
PUBLIC_IP="$PUBLIC_IP"
INSTANCE_ID="$INSTANCE_ID"
KEY_FILE="$KEY_FILE"
EOF

echo "EC2 setup complete! 🎉"
echo "To setup the server, run: ./run-server-setup.sh" 