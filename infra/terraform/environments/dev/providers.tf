terraform {
  required_version = ">= 1.15.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Portfolio / local dry-run default. For GovCloud apply, reconfigure with
  # backend-configs/s3.*.hcl.example (S3 + DynamoDB lock, isolated per env).
  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "aws" {
  region = var.aws_region
}

provider "aws" {
  alias  = "dr"
  region = var.dr_secondary_region
}
