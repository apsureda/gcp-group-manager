/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
variable "iac_project_id" {
  type        = string
  description = "ID of the GCP project that will be created for the project factory"
}

variable "gcp_org_id" {
  type        = string
  description = "GCP organization ID"
}

variable "group_domain" {
  description = "The Cloud Identity domain that will be used for groups (group.name@mudomain.com)."
  type        = string
}

variable "group_parent" {
  description = "The customer ID of the organization to attach the groups to (use 'gcloud organizations list' to find yours)."
  type        = string
}

variable "gcp_billing_account_id" {
  type        = string
  description = "GCP Billing account ID"
}

variable "iac_folder_id" {
  type        = string
  description = "ID of the folder under which the GCP project for the project factory will be located"
}

variable "region" {
  type        = string
  default     = "europe-west1"
  description = "GCP region that will be used for regional resources (GCS buckets, KMS keyring)"
}

variable "iac_members" {
  type        = list(any)
  description = "List of members who will be granted the necessary permissions to manually execute the terraform code."
  default     = []
}

variable "iac_builder" {
  type        = string
  description = "email address to use for the code commits pushed to the git repo by the project factory."
}

variable "disable_build_triggers" {
  type        = bool
  description = "optionally disable the build triggers (in case you prefer to run the terraform code manually)"
  default     = false
}

variable "github_owner" {
  type        = string
  description = "if using a github.com hosted repo, the owner of the repo"
}

variable "github_name" {
  type        = string
  description = "if using a github.com hosted repo, the name of the repo"
}

variable "factory_roles" {
  type        = list(any)
  description = "the IAM roles required by the factory to do its job"
  default = [
    "roles/editor",
    "roles/resourcemanager.projectIamAdmin",
    "roles/billing.projectManager",
    "roles/resourcemanager.folderAdmin",
    "roles/resourcemanager.folderEditor",
    "roles/resourcemanager.projectCreator",
    "roles/resourcemanager.projectDeleter",
    "roles/logging.configWriter",
  ]
}

variable "factory_org_roles" {
  type        = list(any)
  description = "the IAM roles required by the factory to do its job"
  default = [
    "roles/orgpolicy.policyAdmin",
    "roles/logging.configWriter",
  ]
}

variable "factory_bill_roles" {
  type        = list(any)
  description = "the IAM roles required by the factory to do its job"
  default = [
    "roles/billing.admin",
    "roles/logging.configWriter",
  ]
}

variable "gcp_services" {
  type        = list(any)
  description = "GCP services that need to be activated in the project factory GCP project"
  default = [
    "cloudbuild.googleapis.com",
    "cloudkms.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "storage-api.googleapis.com",
    "storage-component.googleapis.com",
    "containerregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
    "appengine.googleapis.com",
    "sourcerepo.googleapis.com",
    "serviceusage.googleapis.com",
    "billingbudgets.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudidentity.googleapis.com",
    "secretmanager.googleapis.com",
  ]
}

variable "terraform_service_account" {
  description = "Service account email of the account to impersonate to run Terraform."
  type        = string
}
