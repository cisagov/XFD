data "aws_ssm_parameter" "ami_id" {
  name = var.ssm_ami_id
}

data "aws_ssm_parameter" "subnet_id" {
  name = var.ssm_subnet_id
}

data "aws_ssm_parameter" "security_group_id" {
  name = var.ssm_security_group_id
}

resource "aws_instance" "cisadev_xfd_dev_host" {
  ami                         = data.aws_ssm_parameter.ami_id.value
  instance_type               = var.instance_type
  subnet_id                   = data.aws_ssm_parameter.subnet_id.value
  vpc_security_group_ids      = [data.aws_ssm_parameter.security_group_id.value]
  key_name                    = var.key_name
  iam_instance_profile        = var.iam_instance_profile
  associate_public_ip_address = var.associate_public_ip_address
  tags                        = var.tags

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    username = var.devhost_username
    password = var.devhost_password
    desktop  = var.desktop
  })
}
