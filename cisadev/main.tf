provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "cisadev_xfd_gh_actions_runner_ec2" {
  ami                         = "ami-xxxxxxxxxxxxxxxxx"
  instance_type               = "t2.micro"
  subnet_id                   = "subnet-xxxxxxxxxxxxxxxxx"
  vpc_security_group_ids      = ["sg-xxxxxxxxxxxxxxxxx"]
  key_name                    = " "
  iam_instance_profile        = "CustomEc2-InstanceProfile"
  associate_public_ip_address = false
  tags = {
    Name        = "CyHy Dashboard GitHub Actions Runner"
    Environment = "staging"
    Owner       = "XFD Dashboard"
  }
  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail

    #Update system and install required packages
    apt-get update -y
    apt-get install -y curl tar wget perl

    #Run the GitHub Runner setup as a non-root user
    sudo -u ubuntu mkdir -p /home/ubuntu/actions-runner
    cd /home/ubuntu/actions-runner

    #Download the latest runner package
    sudo -u ubuntu  curl \
      -o actions-runner-linux-x64-2.335.1.tar.gz \
      -L  https://github.com/actions/runner/releases/download/v2.335.1/actions-runner-linux-x64-2.335.1.tar.gz

    #Extract the installer
    sudo -u ubuntu tar xzf ./actions-runner-linux-x64-2.335.1.tar.gz

    if [ ! -f .runner ]; then
    #Configure the runner
      sudo -u ubuntu ./config.sh \
        --unattended \
        --url https://github.com/enterprises/cisa \
        --token XXXXXXXXXXXXXXXXXXXXXXXXXXXXX \
        --runner-group xfd-runner-group \
        --name cyhy-dashboard-runner
    fi

     sudo ./svc.sh install ubuntu
     sudo ./svc.sh start
    EOF
}
