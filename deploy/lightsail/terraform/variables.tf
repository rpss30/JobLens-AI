variable "aws_region" {
  description = "AWS region for the Lightsail production server."
  type        = string
  default     = "ca-central-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "Use an AWS region name such as ca-central-1."
  }
}

variable "availability_zone" {
  description = "Lightsail availability zone in the selected region."
  type        = string
  default     = "ca-central-1a"
}

variable "environment" {
  description = "Environment tag value."
  type        = string
  default     = "Production"

  validation {
    condition     = contains(["Production"], var.environment)
    error_message = "This template is intended only for the approved production Lightsail target."
  }
}

variable "instance_name" {
  description = "Lightsail instance name."
  type        = string
  default     = "joblens-production"
}

variable "static_ip_name" {
  description = "Lightsail static IPv4 address name."
  type        = string
  default     = "joblens-production-ip"
}

variable "blueprint_id" {
  description = "Lightsail OS blueprint ID. Verify with aws lightsail get-blueprints before a reviewed plan."
  type        = string
  default     = "ubuntu_24_04"
}

variable "bundle_id" {
  description = "Lightsail bundle ID. The example maps to the 2 GB baseline in docs/lightsail-deployment-plan.md."
  type        = string
  default     = "small_3_0"
}

variable "key_pair_name" {
  description = "Existing Lightsail key pair name used for SSH access."
  type        = string
  default     = null
  nullable    = true
}

variable "enable_ssh_access" {
  description = "Whether to open SSH at the Lightsail firewall."
  type        = bool
  default     = true
}

variable "ssh_cidrs" {
  description = "Trusted IPv4 CIDR ranges allowed to reach SSH. Never use 0.0.0.0/0."
  type        = list(string)
  default     = ["203.0.113.10/32"]

  validation {
    condition = alltrue([
      for cidr in var.ssh_cidrs : can(cidrhost(cidr, 0)) && cidr != "0.0.0.0/0"
    ])
    error_message = "Provide valid, trusted IPv4 CIDR ranges for SSH and do not use 0.0.0.0/0."
  }
}

variable "extra_tags" {
  description = "Additional non-secret tags to merge with the required project tags."
  type        = map(string)
  default     = {}
}
