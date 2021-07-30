/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
locals {
  kms_roles = [
    "roles/cloudkms.cryptoKeyDecrypter",
    "roles/cloudkms.cryptoKeyEncrypter",
  ]
}

resource "google_kms_key_ring" "project_factory" {
  project    = google_project.iac_project.project_id
  name       = "project-factory"
  location   = var.region                              # needs to be in the same region as the GCS buckets
  depends_on = [google_project_service.iac_project[1]] # cloudkms.googleapis.com is the second one in the list
}

# KMS key for the SAP backup bucket
resource "google_kms_crypto_key" "build_secrets" {
  name            = "build-secrets"
  key_ring        = google_kms_key_ring.project_factory.self_link
  rotation_period = "7776000s" # 90 days
}

resource "google_kms_crypto_key_iam_member" "crypto_key" {
  count         = length(local.kms_roles) * length(local.iac_members)
  crypto_key_id = google_kms_crypto_key.build_secrets.id
  role          = local.kms_roles[floor(count.index / length(local.iac_members))]
  member        = local.iac_members[count.index % length(local.iac_members)]
  # we need to wait for the Cloud KMS API to be activated so its service account is ready
  depends_on = [google_project_service.iac_project[1]] # cloudkms.googleapis.com is the second one in the list
}