#!/bin/bash

# Create ~/.aws/config if it doesn't exist
mkdir -p ~/.aws

echo "Setting up AWS CLI to handle timestamp discrepancies..."

# Check if config exists
if [ -f ~/.aws/config ]; then
  # Add or update the clock skew setting
  if grep -q "\[default\]" ~/.aws/config; then
    # If default section exists, check if clock_skew setting exists
    if grep -q "clock_skew" ~/.aws/config; then
      # Replace existing clock_skew setting
      sed -i 's/clock_skew = .*/clock_skew = 9999999/g' ~/.aws/config
    else
      # Add clock_skew to default section
      sed -i '/\[default\]/a clock_skew = 9999999' ~/.aws/config
    fi
  else
    # Add default section with clock_skew
    echo -e "[default]\nclock_skew = 9999999" >> ~/.aws/config
  fi

  # Add or update the clock skew for emeraldflow profile
  if grep -q "\[profile emeraldflow\]" ~/.aws/config; then
    # If emeraldflow section exists, check if clock_skew setting exists
    if grep -q "clock_skew" ~/.aws/config; then
      # Replace existing clock_skew setting in emeraldflow section
      sed -i '/\[profile emeraldflow\]/,/\[/ s/clock_skew = .*/clock_skew = 9999999/g' ~/.aws/config
    else
      # Add clock_skew to emeraldflow section
      sed -i '/\[profile emeraldflow\]/a clock_skew = 9999999' ~/.aws/config
    fi
  else
    # Add emeraldflow section with clock_skew
    echo -e "\n[profile emeraldflow]\nclock_skew = 9999999" >> ~/.aws/config
  fi
else
  # Create new config file with clock_skew settings
  cat > ~/.aws/config << EOF
[default]
clock_skew = 9999999

[profile emeraldflow]
clock_skew = 9999999
EOF
fi

echo "AWS CLI configured to handle timestamp discrepancies!"
echo "You should now be able to use AWS CLI commands with your profile." 