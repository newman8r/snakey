#!/bin/bash

echo "🚀 Setting up EC2 instance with proper region handling..."

# Use unique names with timestamps to avoid duplicates
TIMESTAMP=$(date +%s)
SG_NAME="AudioStreamerSG-${TIMESTAMP}"
KEY_NAME="audio-streamer-key-${TIMESTAMP}"
KEY_FILE="${KEY_NAME}.pem"

# Create security group for our audio streaming server
echo "Creating security group: ${SG_NAME}..."
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --group-name ${SG_NAME} \
  --description "Security group for audio streaming server" \
  --profile emeraldflow \
  --region us-west-1 \
  --output text \
  --query 'GroupId')

echo "✅ Security Group created: $SECURITY_GROUP_ID"

# Add inbound rules for SSH and our custom audio ports
echo "Adding inbound rules..."
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --profile emeraldflow \
  --region us-west-1

# Port for audio streaming
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0 \
  --profile emeraldflow \
  --region us-west-1

# Create key pair for SSH access
echo "Creating new key pair: $KEY_NAME"
aws ec2 create-key-pair \
  --key-name $KEY_NAME \
  --query 'KeyMaterial' \
  --profile emeraldflow \
  --region us-west-1 \
  --output text > $KEY_FILE

chmod 400 $KEY_FILE
echo "✅ Key pair created: $KEY_FILE"

# Launch EC2 instance
echo "Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id ami-01891d4f3898759b2 \
  --count 1 \
  --instance-type t2.micro \
  --key-name $KEY_NAME \
  --security-group-ids $SECURITY_GROUP_ID \
  --profile emeraldflow \
  --region us-west-1 \
  --output text \
  --query 'Instances[0].InstanceId')

echo "✅ Instance launched: $INSTANCE_ID"

# Wait for instance to be running
echo "Waiting for instance to be running..."
aws ec2 wait instance-running \
  --instance-ids $INSTANCE_ID \
  --profile emeraldflow \
  --region us-west-1

# Get public DNS name
PUBLIC_DNS=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicDnsName' \
  --profile emeraldflow \
  --region us-west-1 \
  --output text)

PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --profile emeraldflow \
  --region us-west-1 \
  --output text)

echo "EC2 instance is now running!"
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
echo "To set up the server, run: ./setup-server.sh" 