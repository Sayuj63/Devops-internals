terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws        = { source = "hashicorp/aws",        version = "~> 5.60" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.31" }
    helm       = { source = "hashicorp/helm",       version = "~> 2.14" }
    random     = { source = "hashicorp/random",     version = "~> 3.6"  }
    tls        = { source = "hashicorp/tls",        version = "~> 4.0"  }
  }

  # Remote state — enable once the bootstrap bucket exists.
  # backend "s3" {
  #   bucket         = "itm-sim-prov-tfstate"
  #   key            = "envs/prod/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "itm-sim-prov-tflock"
  #   encrypt        = true
  # }
}
