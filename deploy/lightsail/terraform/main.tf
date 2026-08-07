locals {
  common_tags = merge(
    var.extra_tags,
    {
      Project     = "JobLens"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  public_ports = concat(
    [
      {
        protocol   = "tcp"
        from_port  = 80
        to_port    = 80
        cidrs      = ["0.0.0.0/0"]
        ipv6_cidrs = []
      },
      {
        protocol   = "tcp"
        from_port  = 443
        to_port    = 443
        cidrs      = ["0.0.0.0/0"]
        ipv6_cidrs = []
      },
    ],
    var.enable_ssh_access ? [
      {
        protocol   = "tcp"
        from_port  = 22
        to_port    = 22
        cidrs      = var.ssh_cidrs
        ipv6_cidrs = []
      }
    ] : [],
  )
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

resource "aws_lightsail_instance" "app" {
  name              = var.instance_name
  availability_zone = var.availability_zone
  blueprint_id      = var.blueprint_id
  bundle_id         = var.bundle_id
  ip_address_type   = "ipv4"
  key_pair_name     = var.key_pair_name

  tags = local.common_tags
}

resource "aws_lightsail_static_ip" "app" {
  name = var.static_ip_name
}

resource "aws_lightsail_static_ip_attachment" "app" {
  static_ip_name = aws_lightsail_static_ip.app.name
  instance_name  = aws_lightsail_instance.app.name
}

resource "aws_lightsail_instance_public_ports" "app" {
  instance_name = aws_lightsail_instance.app.name

  dynamic "port_info" {
    for_each = local.public_ports

    content {
      protocol   = port_info.value.protocol
      from_port  = port_info.value.from_port
      to_port    = port_info.value.to_port
      cidrs      = port_info.value.cidrs
      ipv6_cidrs = port_info.value.ipv6_cidrs
    }
  }
}
