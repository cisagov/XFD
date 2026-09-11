output "instance_id" {
  description = "EC2 instance ID of the runner"
  value       = aws_instance.cisadev_xfd_gh_actions_runner_ec2.id
}

output "instance_private_ip" {
  description = "Private IP of the runner"
  value       = aws_instance.cisadev_xfd_gh_actions_runner_ec2.private_ip
}
