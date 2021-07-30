/*
 * Copyright 2021 Google LLC. This software is provided as-is, without warranty
 * or representation for any use or purpose. Your use of it is subject to your 
 * agreement with Google.  
 */
locals {
  terraform_builder = "hashicorp/terraform:1.0.1"
  factory_config    = "config/config.yaml"
  requests_root     = "group_root"
}

resource "google_cloudbuild_trigger" "tf_apply_trigger" {
  project     = google_project.iac_project.project_id
  name        = "tf-apply"
  description = "generates terraform files and runs a tf apply on group modification requests"
  disabled    = var.disable_build_triggers

  # Add trigger_template block obly if repo type is csr
  dynamic "trigger_template" {
    for_each = local.src_repo_type == "csr" ? [""] : []
    content {
      project_id   = google_project.iac_project.project_id
      branch_name  = "main"
      invert_regex = true
      repo_name    = google_sourcerepo_repository.ci_groups[0].name
    }
  }

  # Add github block obly if repo type is github
  dynamic "github" {
    for_each = local.src_repo_type == "github" ? [""] : []
    content {
      owner = var.github_owner
      name  = var.github_name
      push {
        branch = "main"
      }
    }
  }

  substitutions = {
    _REQUESTS_FILE  = local.requests_root
    _FACTORY_CONFIG = local.factory_config
    _GIT_REPO       = local.src_repo_url
    _IAC_BUILDER    = var.iac_builder
  }

  included_files = ["${local.requests_root}/**/*.yaml"]

  build {
    step {
      name       = "gcr.io/google.com/cloudsdktool/cloud-sdk:slim"
      entrypoint = "bash"
      dir        = "/git_tmp"
      args = [
        "-c",
        <<-EOT
        set -x
        # set main as default branch
        git config --global init.defaultBranch main
        # clone the repo
        if [[ "$${_GIT_REPO}" == *"github.com"* ]]; then
          gcloud secrets versions access 1 --secret="github-key" --project=$PROJECT_ID > /root/.ssh/id_rsa
          chmod 600 /root/.ssh/id_rsa
          cat <<EOF >/root/.ssh/config
          Hostname github.com
          IdentityFile /root/.ssh/id_rsa
        EOF
          echo "github.com,140.82.118.4 ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" > /root/.ssh/known_hosts
          git clone $${_GIT_REPO} tmp-requests
        else
          gcloud source repos clone $${_GIT_REPO} tmp-requests --project=$PROJECT_ID
        fi
        cd tmp-requests
        git checkout $BRANCH_NAME
        EOT
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
      volumes {
        name = "ssh"
        path = "/root/.ssh"
      }
    }

    # run the environments requests file, and issue output to the terraform folder
    # in the branch of the current request.
    step {
      name = "gcr.io/$PROJECT_ID/prj-factory"
      dir  = "/git_tmp/tmp-requests"
      args = [
        "/tf_generator.py",
        "--resources=$${_REQUESTS_FILE}",
        "--config=$${_FACTORY_CONFIG}",
        "--template-dir=/templates",
        "--tf-out=terraform",
        "ci-groups",
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
    }

    # get the git log to see what changed
    step {
      name       = "gcr.io/google.com/cloudsdktool/cloud-sdk:slim"
      entrypoint = "bash"
      args = [
        "-c",
        <<-EOT
        set -x
        cd /git_tmp/tmp-requests
        git status --porcelain | tee git_diff.txt
        EOT
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
    }

    # get the list of tf configurations that need to be built
    step {
      name = "gcr.io/$PROJECT_ID/prj-factory"
      dir  = "/git_tmp/tmp-requests"
      args = [
        "/tf_dep_finder.py",
        "--tf-root=terraform",
        "--changelog=git_diff.txt",
        "--output=tf_build_steps.txt",
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
    }

    # run a terraform plan to check what changes will be made.
    step {
      name       = local.terraform_builder
      entrypoint = "sh"
      args = [
        "-c",
        <<-EOT
        set -e
        cd /git_tmp/tmp-requests
        base_dir=$(pwd)
        output_log=/git_tmp/terraform_output.txt
        > $${output_log}
        echo "Running terraform plan on modified terraform configurations" | tee -a $${output_log}
        echo "Build steps:" | tee -a $${output_log}
        cat tf_build_steps.txt >> $${output_log}
        for tf_conf in `cat tf_build_steps.txt`; do
          echo "*****************************************************************" | tee -a $${output_log}
          echo "* Processing terrform configuration $${tf_conf}" | tee -a $${output_log}
          echo "*****************************************************************" | tee -a $${output_log}
          cd $${tf_conf}
          terraform init -no-color | tee tf_init_out.txt
          grep "Terraform has been successfully initialized" tf_init_out.txt || (echo "terraform init did not succeed." ; exit 1)
          rm tf_init_out.txt
          terraform fmt
          (terraform apply -auto-approve -no-color || exit 1) | tee -a $${output_log}
          echo "" | tee -a $${output_log}
          cd $${base_dir}
        done
        EOT
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
    }

    # push the changes to the current branch in the repo.
    step {
      name       = "gcr.io/google.com/cloudsdktool/cloud-sdk:slim"
      entrypoint = "bash"
      args = [
        "-c",
        <<-EOT
        set -x
        cd /git_tmp/tmp-requests
        git add terraform
        git config --global user.email "$${_IAC_BUILDER}"
        git config --global user.name "Project Factory"
        git commit --author="Build Pipeline <$${_IAC_BUILDER}>" --file=/git_tmp/terraform_output.txt
        git push -u origin $BRANCH_NAME
        EOT
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
      volumes {
        name = "ssh"
        path = "/root/.ssh"
      }
    }
  }
}

resource "google_cloudbuild_trigger" "sanity_check" {
  project     = google_project.iac_project.project_id
  name        = "sanity-check"
  description = "run the generators in dry run mode to see if there are any systax issues"
  disabled    = var.disable_build_triggers

  # Add trigger_template block obly if repo type is csr
  dynamic "trigger_template" {
    for_each = local.src_repo_type == "csr" ? [""] : []
    content {
      project_id   = google_project.iac_project.project_id
      branch_name  = "main"
      invert_regex = true
      repo_name    = google_sourcerepo_repository.ci_groups[0].name
    }
  }

  # Add github block obly if repo type is github
  dynamic "github" {
    for_each = local.src_repo_type == "github" ? [""] : []
    content {
      owner = var.github_owner
      name  = var.github_name
      pull_request {
        branch          = "main"
        comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
      }
    }
  }

  substitutions = {
    _REQUESTS_FILE  = local.requests_root
    _FACTORY_CONFIG = local.factory_config
    _GIT_REPO       = local.src_repo_url
    _IAC_BUILDER    = var.iac_builder
  }

  included_files = [
    "${local.requests_root}/**/*.yaml",
    "${local.requests_root}/**/OWNERS",
  ]

  build {
    # run the environments requests file, and issue output to the terraform folder
    # in the branch of the current request.
    step {
      name = "gcr.io/$PROJECT_ID/prj-factory"
      dir  = "/git_tmp/tmp-requests"
      args = [
        "/tf_generator.py",
        "--resources=$${_REQUESTS_FILE}",
        "--config=$${_FACTORY_CONFIG}",
        "--template-dir=/templates",
        "--tf-out=terraform",
        "ci-groups",
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
    }

    # update the CODEOWNERS file and issue output to stdout
    step {
      name = "gcr.io/$PROJECT_ID/prj-factory"
      dir  = "/git_tmp/tmp-requests"
      args = [
        "/codeowners_gen.py",
        "--repo-root=group_root",
        "--add-owners=*=@$${_GITHUB_OWNER}"
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
    }
  }
}



# resource "google_cloudbuild_trigger" "tf_apply_trigger" {
#   project     = google_project.iac_project.project_id
#   name        = "tf-apply"
#   description = "apply the terraform configuration generated in the previous step"
#   disabled    = var.disable_build_triggers

#   # Add trigger_template block obly if repo type is csr
#   dynamic "trigger_template" {
#     for_each = local.src_repo_type == "csr" ? [""] : []
#     content {
#       project_id  = google_project.iac_project.project_id
#       branch_name = "main"
#       repo_name   = google_sourcerepo_repository.ci_groups[0].name
#     }
#   }

#   # Add github block obly if repo type is github
#   dynamic "github" {
#     for_each = local.src_repo_type == "github" ? [""] : []
#     content {
#       owner = var.github_owner
#       name  = var.github_name
#       push {
#         branch = "main"
#       }
#     }
#   }

#   included_files = ["terraform/**"]

#   build {
#     step {
#       name       = local.terraform_builder
#       entrypoint = "sh"
#       args = [
#         "-c",
#         <<-EOT
#         base_dir=$(pwd)
#         echo "Running terraform apply on modified terraform configurations"
#         for tf_conf in `cat tf_build_steps.txt`; do
#           echo "*****************************************************************"
#           echo "* Processing terrform configuration $${tf_conf}"
#           echo "*****************************************************************"
#           cd $${tf_conf}
#           terraform init && terraform apply -auto-approve || exit 1
#           echo ""
#           cd $${base_dir}
#         done
#         EOT
#       ]
#     }
#     timeout = "1200s"
#   }
# }

resource "google_cloudbuild_trigger" "codeowners_trigger" {
  project     = google_project.iac_project.project_id
  name        = "codeowners-update"
  description = "update the CODEOWNERS file if any OWNERS file was changed"
  disabled    = var.disable_build_triggers

  # Add trigger_template block obly if repo type is csr
  dynamic "trigger_template" {
    for_each = local.src_repo_type == "csr" ? [""] : []
    content {
      project_id  = google_project.iac_project.project_id
      branch_name = "main"
      repo_name   = google_sourcerepo_repository.ci_groups[0].name
    }
  }

  # Add github block obly if repo type is github
  dynamic "github" {
    for_each = local.src_repo_type == "github" ? [""] : []
    content {
      owner = var.github_owner
      name  = var.github_name
      push {
        branch = "main"
      }
    }
  }

  substitutions = {
    _CODEOWNERS_FILE = ".github/CODEOWNERS"
    _GIT_REPO        = local.src_repo_url
    _IAC_BUILDER     = var.iac_builder
    _GITHUB_OWNER    = var.github_owner
  }

  included_files = ["${local.requests_root}/**/OWNERS"]

  build {

    step {
      name       = "gcr.io/google.com/cloudsdktool/cloud-sdk:slim"
      entrypoint = "bash"
      dir        = "/git_tmp"
      args = [
        "-c",
        <<-EOT
        set -x
        # set main as default branch
        git config --global init.defaultBranch main
        # clone the repo
        if [[ "$${_GIT_REPO}" == *"github.com"* ]]; then
          gcloud secrets versions access 1 --secret="github-key" --project=$PROJECT_ID > /root/.ssh/id_rsa
          chmod 600 /root/.ssh/id_rsa
          cat <<EOF >/root/.ssh/config
          Hostname github.com
          IdentityFile /root/.ssh/id_rsa
        EOF
          echo "github.com,140.82.118.4 ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" > /root/.ssh/known_hosts
          git clone $${_GIT_REPO} tmp-requests
        else
          gcloud source repos clone $${_GIT_REPO} tmp-requests --project=$PROJECT_ID
        fi
        cd tmp-requests
        git checkout $BRANCH_NAME
        EOT
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
      volumes {
        name = "ssh"
        path = "/root/.ssh"
      }
    }

    # update the CODEOWNERS file
    step {
      name = "gcr.io/$PROJECT_ID/prj-factory"
      dir  = "/git_tmp/tmp-requests"
      args = [
        "/codeowners_gen.py",
        "--repo-root=group_root",
        "--codeowners-out=$${_CODEOWNERS_FILE}",
        "--add-owners=*=@$${_GITHUB_OWNER}"
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
    }

    # push the changes to the current branch in the repo.
    step {
      name       = "gcr.io/google.com/cloudsdktool/cloud-sdk:slim"
      entrypoint = "bash"
      args = [
        "-c",
        <<-EOT
        set -x
        cd /git_tmp/tmp-requests
        git add $${_CODEOWNERS_FILE} || echo "No CODEOWNERS file found"
        git config --global user.email "$${_IAC_BUILDER}"
        git config --global user.name "Project Factory"
        git commit --author="Build Pipeline <$${_IAC_BUILDER}>" -m "Updating CODEOWNERS file"
        git push -u origin $BRANCH_NAME
        EOT
      ]
      volumes {
        name = "git_tmp"
        path = "/git_tmp"
      }
      volumes {
        name = "ssh"
        path = "/root/.ssh"
      }
    }
  }
}