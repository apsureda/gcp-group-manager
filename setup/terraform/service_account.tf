/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */

# This is the service account that will be used for creating Cloud Identity groups
resource "google_service_account" "group_creator_sa" {
  project      = google_project.iac_project.project_id
  account_id   = "group-creator"
  display_name = "Cloud Identity group creator"
}

# The Cloud Build SA will need permissions to impersonate the SA that will be used for running terraform.
resource "google_service_account_iam_binding" "cloud_build_impersonation" {
  service_account_id = google_service_account.group_creator_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"

  members = [
    "serviceAccount:${google_project.iac_project.number}@cloudbuild.gserviceaccount.com",
  ]
}
