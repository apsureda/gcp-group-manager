/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
resource "google_storage_bucket" "factory_remote_state" {
  name                        = "tf-state-${google_project.iac_project.project_id}"
  project                     = google_project.iac_project.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  storage_class               = "REGIONAL"
}

resource "google_storage_bucket_iam_member" "editor" {
  count  = length(local.iac_members)
  bucket = google_storage_bucket.factory_remote_state.name
  role   = "roles/storage.objectAdmin"
  member = element(local.iac_members, count.index)
  # we need to wait for the Cloud Build API to be activated so its service account is ready
  depends_on = [google_project_service.iac_project[0]] # cloudbuild.googleapis.com is the first one in the list
}