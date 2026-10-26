terraform {
  backend "s3" {
    bucket              = "eks-ai-incident-lab-tfstate-49f4a969"
    key                 = "eks-ai-incident-lab/bootstrap/terraform.tfstate"
    region              = "ap-south-1"
    encrypt             = true
    use_lockfile        = true
    allowed_account_ids = ["923988301700"]
  }
}