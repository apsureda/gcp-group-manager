/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
output "iac_project_id" {
  value = google_project.iac_project.project_id
}