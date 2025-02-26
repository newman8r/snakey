#!/bin/bash

echo "🔍 AWS Credentials Debug Tool 🔍"
echo "===============================\n"

echo "System Information:"
echo "-------------------"
echo "Current date/time: $(date)"
echo "Timezone: $(date +%Z)"
echo "Timezone offset: $(date +%z)"
echo "Current directory: $(pwd)"
echo ""

echo "AWS Configuration:"
echo "-----------------"
echo "Available AWS profiles:"
aws configure list-profiles
echo ""

echo "Checking emeraldflow profile:"
echo "----------------------------"
echo "AWS_CONFIG_FILE: $AWS_CONFIG_FILE"
echo "AWS_SHARED_CREDENTIALS_FILE: $AWS_SHARED_CREDENTIALS_FILE"
echo ""

echo "Checking AWS CLI version:"
aws --version
echo ""

# Try with different methods
echo "Attempt 1: Basic credential check"
echo "--------------------------------"
aws sts get-caller-identity --profile emeraldflow
echo ""

echo "Attempt 2: With explicit region"
echo "------------------------------"
aws sts get-caller-identity --region us-west-2 --profile emeraldflow
echo ""

echo "Attempt 3: With timezone and time offset adjustment"
echo "-------------------------------------------------"
TZ=UTC aws sts get-caller-identity --profile emeraldflow
echo ""

echo "Attempt 4: With explicit credentials"
echo "-----------------------------------"
echo "Reading credentials from profile..."
AWS_ACCESS_KEY=$(aws configure get aws_access_key_id --profile emeraldflow)
AWS_SECRET_KEY=$(aws configure get aws_secret_access_key --profile emeraldflow)

if [ -n "$AWS_ACCESS_KEY" ] && [ -n "$AWS_SECRET_KEY" ]; then
  echo "Found credentials, attempting direct usage..."
  AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY AWS_SECRET_ACCESS_KEY=$AWS_SECRET_KEY aws sts get-caller-identity
else
  echo "Could not retrieve credentials from profile."
fi
echo ""

echo "Attempt 5: Check configuration file formatting"
echo "--------------------------------------------"
echo "AWS Config file content (redacted):"
if [ -f ~/.aws/config ]; then
  cat ~/.aws/config | sed 's/\(.*key.*=\).*/\1 [REDACTED]/'
else
  echo "~/.aws/config file not found"
fi
echo ""

echo "AWS Credentials file content (redacted):"
if [ -f ~/.aws/credentials ]; then
  cat ~/.aws/credentials | sed 's/\(.*key.*=\).*/\1 [REDACTED]/'
else
  echo "~/.aws/credentials file not found"
fi
echo ""

echo "Try a simpler AWS command:"
echo "-------------------------"
AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY AWS_SECRET_ACCESS_KEY=$AWS_SECRET_KEY aws ec2 describe-regions --region us-west-2 --output json

echo "\n🔍 Debugging complete! Check the output above for clues." 