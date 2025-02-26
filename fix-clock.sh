#!/bin/bash

echo "🕒 System Clock Fixer 🕒"
echo "========================"

# Current time information
echo "Current system time: $(date)"

# Set timezone to US/Central for Austin, TX
echo "Setting timezone to US/Central (Austin, TX)..."
sudo ln -sf /usr/share/zoneinfo/US/Central /etc/localtime
echo "Timezone set. Current time with new timezone: $(date)"

# Get current time from time.gov or google
echo "Getting current time from network..."
CURRENT_DATE=$(curl -s --head https://www.google.com | grep -i "date:" | sed 's/date: //i' | sed 's/\r//')
echo "Network time: $CURRENT_DATE"

if [ -n "$CURRENT_DATE" ]; then
  echo "Setting system date based on network time..."
  sudo date -s "$CURRENT_DATE"
  echo "System time set to: $(date)"
else
  echo "Failed to get network time. Trying alternative method..."
  # Alternative using NTP directly
  sudo apt-get update && sudo apt-get install -y ntpdate
  sudo ntpdate time.google.com
  echo "System time now: $(date)"
fi

echo "Clock fixing complete! Test AWS commands now." 