output "worker_ecs_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

# output "db_accessor_instance_id" {
#   value = try(aws_instance.db_accessor[0].id, null)
# }

output "was_reporting_instance_id" {
  description = "ID of the WAS reporting EC2 instance when enabled in the DMZ environment."
  value       = try(aws_instance.was_reporting[0].id, null)
}

output "was_reporting_private_ip" {
  description = "Private IP address of the WAS reporting EC2 instance when enabled in the DMZ environment."
  value       = try(aws_instance.was_reporting[0].private_ip, null)
}
