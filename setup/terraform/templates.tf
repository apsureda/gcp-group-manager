/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
data "template_file" "first_commit_csr" {
  count    = local.src_repo_type == "csr" ? 1 : 0
  template = file("templates/first_commit_csr.sh")
  vars = {
    git_repo     = google_sourcerepo_repository.ci_groups[0].name
    cicd_project = google_project.iac_project.project_id
  }
}

resource "local_file" "first_commit_csr" {
  count    = local.src_repo_type == "csr" ? 1 : 0
  content  = data.template_file.first_commit_csr[0].rendered
  filename = "../first_commit.sh"
}

data "template_file" "first_commit_github" {
  count    = local.src_repo_type == "github" ? 1 : 0
  template = file("templates/first_commit_github.sh")
  vars = {
    git_repo = local.src_repo_url
  }
}

resource "local_file" "first_commit_github" {
  count    = local.src_repo_type == "github" ? 1 : 0
  content  = data.template_file.first_commit_github[0].rendered
  filename = "../first_commit.sh"
}

data "template_file" "make_builder" {
  template = file("templates/make_builder.sh")
  vars = {
    cicd_project = google_project.iac_project.project_id
  }
}

resource "local_file" "make_builder" {
  content  = data.template_file.make_builder.rendered
  filename = "../make_builder.sh"
}

data "template_file" "factory_config" {
  template = file("templates/config.yaml")
  vars = {
    iac_bucket             = google_storage_bucket.factory_remote_state.name
    gcp_billing_account_id = var.gcp_billing_account_id
    group_domain           = var.group_domain
    group_parent           = var.group_parent
    tf_service_account     = google_service_account.group_creator_sa.email
  }
}

resource "local_file" "factory_config" {
  content  = data.template_file.factory_config.rendered
  filename = "../../config/config.yaml"
}