/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
resource "google_sourcerepo_repository" "ci_groups" {
  count   = local.src_repo_type == "csr" ? 1 : 0
  name    = "ci-groups"
  project = google_project.iac_project.project_id
}

# The Cloud Build service account will need write access to the source repo, since
# it will perform code commits in it.
resource "google_sourcerepo_repository_iam_member" "editor" {
  count      = (local.src_repo_type == "csr" ? 1 : 0) * length(local.iac_members)
  project    = google_sourcerepo_repository.ci_groups[0].project
  repository = google_sourcerepo_repository.ci_groups[0].name
  role       = "roles/source.writer"
  member     = local.iac_members[count.index]
  # we need to wait for the Cloud Build API to be activated so its service account is ready
  depends_on = [google_project_service.iac_project[0]] # cloudbuild.googleapis.com is the first one in the list
}