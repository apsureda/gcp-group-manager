/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */

# add a random 4 hex char suffix to the project ID, so we can destry/apply this
# terraform file without running into project ID reuse conflicts.
resource "random_id" "cicd_project" {
  byte_length = 2
}

resource "google_project" "iac_project" {
  name            = var.iac_project_id
  folder_id       = var.iac_folder_id
  billing_account = var.gcp_billing_account_id
  project_id      = "${var.iac_project_id}-${random_id.cicd_project.hex}"
}