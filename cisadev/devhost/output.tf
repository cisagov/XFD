output "instance_id" {
  description = "EC2 instance ID of the dev host"
  value       = aws_instance.cisadev_xfd_dev_host.id
}

output "instance_private_ip" {
  description = "Private IP to RDP into (port 3389)"
  value       = aws_instance.cisadev_xfd_dev_host.private_ip
}
