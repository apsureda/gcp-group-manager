/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */

# grant billing account user role to iac members so we can attach projects to the billing account and
# create log sinks on the billing account
resource "google_billing_account_iam_member" "iac_members" {
  count              = length(var.factory_bill_roles) * length(local.iac_members)
  billing_account_id = var.gcp_billing_account_id
  role               = var.factory_bill_roles[floor(count.index / length(local.iac_members))]
  member             = local.iac_members[count.index % length(local.iac_members)]
}
