terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Remote state (recommended for teams / CI). Create the bucket once, then uncomment.
  # backend "s3" {
  #   bucket       = "gearloop-tfstate-<your-account-id>"
  #   key          = "gearloop/eks.tfstate"
  #   region       = "ap-south-1"
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "gearloop"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
