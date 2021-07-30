/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
resource "google_project_iam_member" "iac_team" {
  count   = length(var.iac_members)
  project = google_project.iac_project.project_id
  role    = "roles/editor"
  member  = var.iac_members[count.index]
}
