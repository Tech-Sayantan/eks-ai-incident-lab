variable "aws_region" {
  description = "AWS region for the state bucket."
  type        = string
  default     = "ap-south-1"
}

variable "state_bucket_name" {
  description = "Globally unique name for the Terraform state bucket."
  type        = string
}

variable "expected_account_id" {
  description = "Verified AWS account where resources should be created."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "Provide a 12-digit AWS account ID."
  }
}

