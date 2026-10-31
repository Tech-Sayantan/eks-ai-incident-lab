variable "name" {
  type = string
}

variable "kubernetes_version" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "operator_cidr" {
  type = string
}

variable "operator_arn" {
  type = string
}