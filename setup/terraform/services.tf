/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */

resource "google_project_service" "iac_project" {
  count              = length(var.gcp_services)
  project            = google_project.iac_project.project_id
  service            = var.gcp_services[count.index]
  disable_on_destroy = false
}
