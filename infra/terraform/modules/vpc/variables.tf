variable "environment" {
  type        = string
  description = "Environment name."
}

variable "cidr_block" {
  type        = string
  description = "VPC IPv4 CIDR block."
}

variable "private_subnets" {
  type        = list(string)
  description = "Private subnet CIDR blocks (one per AZ)."
}

variable "availability_zones" {
  type        = list(string)
  description = "Availability zones aligned to private_subnets by index."
}

variable "enable_dns_hostnames" {
  type        = bool
  description = "Enable DNS hostnames in the VPC."
}

variable "enable_dns_support" {
  type        = bool
  description = "Enable DNS support in the VPC."
}

variable "tags" {
  type        = map(string)
  description = "Additional tags applied to all resources."
  default     = {}
}
