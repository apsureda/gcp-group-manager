/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
terraform {
  # Use a local terraform state on the first run, then add the IAC project bucket
  # as remote state. Or simply use a pre-existing bucket, if you already have one.
  # backend "gcs" {
  #   bucket = "tf-state-[IAC_PROJECT_ID]"
  #   prefix = "tf-factory/iac_pipeline"
  # }

  required_providers {
    google = {
      version = "~> 3.76"
    }
  }
}

provider "google" {
  impersonate_service_account = var.terraform_service_account
}

