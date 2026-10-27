variable "name" {
  description = "Name used to tag network resources."
  type        = string
}

variable "vpc_cidr" {
  description = "IPv4 range for the VPC."
  type        = string
}

variable "availability_zones" {
  description = "Two Availability Zones for the public subnets."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2
    error_message = "Provide exactly two different Availability Zones."
  }
}

variable "public_subnet_cidrs" {
  description = "IPv4 ranges for the two public subnets."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Provide exactly two public subnet CIDRs."
  }
}