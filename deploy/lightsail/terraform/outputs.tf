output "instance_name" {
  description = "Lightsail instance name."
  value       = aws_lightsail_instance.app.name
}

output "static_ip_address" {
  description = "Static IPv4 address to use in the existing DNS provider after apply approval."
  value       = aws_lightsail_static_ip.app.ip_address
}

output "public_http_ports" {
  description = "Public HTTP and HTTPS ports routed to Caddy."
  value       = [80, 443]
}

output "ssh_allowed_cidrs" {
  description = "Trusted source ranges allowed to reach SSH."
  value       = var.enable_ssh_access ? var.ssh_cidrs : []
}
