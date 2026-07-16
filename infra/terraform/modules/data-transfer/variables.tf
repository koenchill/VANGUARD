variable "environment" {
  type        = string
  description = "Environment name."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for transfer endpoints / DataSync agents."
}

variable "connection_type" {
  type        = string
  description = "Enterprise connectivity mode."
  validation {
    condition     = contains(["direct_connect", "vpn", "cross_account", "snowball"], var.connection_type)
    error_message = "connection_type must be one of: direct_connect, vpn, cross_account, snowball."
  }
}

variable "source_endpoint" {
  type        = string
  description = "Source CIDR or endpoint identifier."
}

variable "source_account_id" {
  type        = string
  description = "Source AWS account ID when connection_type is cross_account."
}

variable "landing_bucket" {
  type        = string
  description = "Landing bucket (data lands under landing/raw/ only)."
}

variable "transfer_role_name" {
  type        = string
  description = "IAM role name for time-boxed read-only transfer."
}

variable "datasync_task_name" {
  type        = string
  description = "DataSync task name for bulk/network transfers."
}

variable "vpn_customer_gateway_ip" {
  type        = string
  description = "Customer gateway public IP when connection_type is vpn."
  default     = null
}

variable "vpn_bgp_asn" {
  type        = number
  description = "BGP ASN for the customer gateway when connection_type is vpn."
  default     = null
}

variable "dx_bandwidth" {
  type        = string
  description = "Direct Connect bandwidth when connection_type is direct_connect."
  default     = null
}

variable "dx_amazon_side_asn" {
  type        = number
  description = "Amazon side ASN for the DX gateway when connection_type is direct_connect."
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Additional tags."
  default     = {}
}
