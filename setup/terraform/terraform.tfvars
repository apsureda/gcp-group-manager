iac_project_id            = "ci-group-factory"
iac_folder_id             = "folders/1068507387329" # /FACTORY
gcp_billing_account_id    = "0131D6-94FD9F-065EAB"
gcp_org_id                = "116143322321"
group_domain              = "apszaz.com"
group_parent              = "customers/C018pf49b"
terraform_service_account = "project-factory-19674@apszaz-cft-tf.iam.gserviceaccount.com"
github_owner              = "apsureda"
github_name               = "gci-groups"

# List of members who will be granted the necessary permissions to manually execute the terraform code (optional)
#iac_members            = ["group:gcp-global-cicd@apszaz.com"]
# email address to use for the code commits pushed to the git repo by the project factory
iac_builder = "project-factory@apszaz.com"
