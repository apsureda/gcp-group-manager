/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
locals {
  iac_members   = concat(var.iac_members, ["serviceAccount:${google_project.iac_project.number}@cloudbuild.gserviceaccount.com"])
  src_repo_type = var.github_owner != null && var.github_name != null ? "github" : "csr"
  src_repo_url  = local.src_repo_type == "github" ? "git@github.com:${var.github_owner}/${var.github_name}.git" : google_sourcerepo_repository.ci_groups[0].name
}
