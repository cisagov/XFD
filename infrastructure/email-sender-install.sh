#!/bin/bash

# Create temporary directory for SSM Agent installation
sudo mkdir -p /tmp/ssm
cd /tmp/ssm || return

# Download and install the SSM Agent
wget https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb
sudo dpkg -i amazon-ssm-agent.deb
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
rm amazon-ssm-agent.deb

# Update packages
sudo apt-get update -y

# Install Python3 and pip
sudo apt-get install -y python3 python3-pip

# Install necessary Python libraries
pip3 install boto3 pandas

# Create working directory for email script
sudo mkdir -p /var/www/email_sender
sudo chmod -R 755 /var/www/email_sender
