/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */

resource "google_secret_manager_secret" "github_key" {
  count     = local.src_repo_type == "github" ? 1 : 0
  project   = google_project.iac_project.project_id
  secret_id = "github-key"

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_iam_member" "cloudbuld_member" {
  count     = local.src_repo_type == "github" ? 1 : 0
  project   = google_project.iac_project.project_id
  secret_id = google_secret_manager_secret.github_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_project.iac_project.number}@cloudbuild.gserviceaccount.com"
}
