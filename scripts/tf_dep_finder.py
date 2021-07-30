#!/usr/bin/python

"""Determine what terraform packages should be built based on a list of modified
files and the computed dependencies between the packages.

Copyright 2021 Google LLC. This software is provided as-is, without warranty or
representation for any use or purpose. Your use of it is subject to your 
agreement with Google.  
"""

import argparse
import os
import sys
import logging
import re
import glob
from collections import defaultdict

def parse_modules(tf_content, current_path):
  """
  Look for module declarations. These blocks have the following structure:
  module "program" {
    source = "../../../modules/program"
    param_1 = "${var.param_1}"
    ...
  }
  fortunately, "source" is a reserved keywork in terraform, so we can assume
  that all "source" elements are pointers to othe rmodules.
  """
  result = []
  p = re.compile(r'\Wsource\s*=\s*"([^"]+)"')
  result = p.findall(tf_content)
  # remove duplicates
  if len(result) > 1:
    res_set = set(result)
    result = list(res_set)
  # return the canonical path to the modules
  # i.e. change this: 'programs/it/cloud/../../../modules/program'
  # to this: 'modules/program'
  result = [os.path.normpath(current_path + '/' + element) for element in result]
  return result

def parse_data_refs(tf_content):
  """
  Look for references to other remote states. These references look like this:
  gcp_org_id = "${data.terraform_remote_state.foundation.org_id}"
  """
  result = []
  p = re.compile(r'data\.terraform_remote_state\.([_a-z][_\-0-9a-z]*)\.')
  result = p.findall(tf_content)
  # remove duplicates
  if len(result) > 1:
    res_set = set(result)
    result = list(res_set)
  
  return result

def parse_backends(tf_content):
  """
  Look for backend blocks. These blocks have the following structure:
  terraform {
    backend "gcs" {
      bucket = "tf-bootstrap-vdf"
      prefix = "terraform/tenants/it/programs/cloud"
    }
  }
  """
  result = []
  p = re.compile(r'terraform\s+\{[^\{\}]*backend\s+"[^"]+"\s*\{[^\}]+\}\s+\}')
  backends = p.findall(tf_content)
  if len(backends) == 0:
    return result
  # for each backend, get the bucket name and prefix
  p_bucket = re.compile(r'bucket\s*=\s*"([^"]+)"')
  p_prefix = re.compile(r'prefix\s*=\s*"([^"]+)"')
  p_name = re.compile(r'backend\s*"([^"]+)"')
  for backend in backends:
    gcs_object = ''
    m = p_bucket.search(backend)
    if m:
      gcs_object = 'gs://' + m.group(1)
    m = p_prefix.search(backend)
    if m:
      gcs_object = gcs_object + '/' + m.group(1)
    m = p_name.search(backend)
    if m:
      gcs_object = gcs_object + '/' + m.group(1) + '.tfstate'
    result.append(gcs_object)
  return result
  
def parse_remote_states(tf_content):
  """
  Parse remote states configurations from the provided file content. Returns a list of
  tuples. Ex.: ('foundation', 'gc://tf-bootstrap-vdf/terraform/foundation')
  Sample configuration:
  data "terraform_remote_state" "foundation" {
    backend = "gcs"
    config {
      bucket = "tf-bootstrap-vdf"
      prefix = "terraform/foundation"
    }
  }
  """
  result = []
  p = re.compile(r'data\s+\"terraform_remote_state\"\s+\"[^\"]+\"\s*\{[^\{\}]*backend\s*=\s*\"gcs\"\s*config\s*=?\s*\{[^\}]+\}\s+\}')
  r_states = p.findall(tf_content)
  if len(r_states) == 0:
    return result
  # for each remote state, get the bucket name and prefix
  p_name = re.compile(r'data\s+"terraform_remote_state"\s+"([^"]+)"\s*\{')
  p_backend_type = re.compile(r'backend\s*=\s*"([^"]+)"')
  p_bucket = re.compile(r'bucket\s*=\s*"([^"]+)"')
  p_prefix = re.compile(r'prefix\s*=\s*"([^"]+)"')
  for r_state in r_states:
    rs_name = ''
    m = p_name.search(r_state)
    if m:
      rs_name = m.group(1)
    gcs_object = ''
    m = p_bucket.search(r_state)
    if m:
      gcs_object = 'gs://' + m.group(1)
    m = p_prefix.search(r_state)
    if m:
      gcs_object = gcs_object + '/' + m.group(1)
    m = p_backend_type.search(r_state)
    if m:
      gcs_object = gcs_object + '/' + m.group(1) + '.tfstate'
    result.append((rs_name, gcs_object))
  return result

def topology_sort(vertex, adjacency_list, visited_list, output_stack):
  """
  Sort build dependencies using depth-first search, as described in
  https://en.wikipedia.org/wiki/Topological_sorting
  """
  if not visited_list[vertex]:
      visited_list[vertex] = True
      for neighbor in adjacency_list[vertex]:
          topology_sort(neighbor, adjacency_list, visited_list, output_stack)
      output_stack.insert(0, vertex)

def get_build_chain(deps, build_root):
  """
  Get the full depth list of builds depending from a build node.
  """
  build_chain = [build_root]
  if build_root in deps:
    for dep in deps[build_root]:
      build_chain.extend(get_build_chain(deps, dep))
  return build_chain

def compute_deps(tf_root):
  """
  Walk through all the terraform files in a root folder, parse each file and compute
  dependencies between terraform packages (independent tf config sets).
  """
  backend2package = {}
  tf_packages = {}
  for tf_file in glob.iglob(tf_root + '/**/*.tf', recursive=True):
    tf_file = os.path.normpath(tf_file)
    # all the .tf files in the same folder are part of the same configuration
    tf_folder = os.path.dirname(tf_file)
    if not tf_folder in tf_packages:
      tf_packages[tf_folder] = {'RS_DEF' : [], 'RS_REF' : [], 'MD_REF' : [], 'LINKERS' : []}
    f = open(tf_file, "r")
    tf_content = f.read()
    # find the GCS url of the current remote storage backend
    if 'backend' in tf_content:
      for backend in parse_backends(tf_content):
        backend2package[backend] = tf_folder
    if '"terraform_remote_state"' in tf_content:
      tf_packages[tf_folder]['RS_DEF'].extend(parse_remote_states(tf_content))
    if 'module ' in tf_content:
      tf_packages[tf_folder]['MD_REF'].extend(parse_modules(tf_content, tf_folder))
    if 'data.terraform_remote_state.' in tf_content:
      tf_packages[tf_folder]['RS_REF'].extend(parse_data_refs(tf_content))
    f.close()
  logging.debug('backends found: %s' % str(backend2package))
  logging.debug('refs found: %s' % str(tf_packages))

  # compute package dependencies
  for tf_package in tf_packages:
    # keep only the remote states that are curently being used
    active_rstates = []
    for rs_def in tf_packages[tf_package]['RS_DEF']:
      if rs_def[0] in tf_packages[tf_package]['RS_REF']:
        active_rstates.append(rs_def[1])
      else:
        logging.info('ignoring unused remote state \'%s\' in package \'%s\'' % (rs_def[0], tf_package))
    tf_packages[tf_package]['RS_REF'] = active_rstates
    # we do not need remote states definitions anymore
    tf_packages[tf_package].pop('RS_DEF') 
    # subscribe as dependent from used packages
    for rs_ref in tf_packages[tf_package]['RS_REF']:
      provider = backend2package[rs_ref]
      if not tf_package in tf_packages[provider]['LINKERS']:
        tf_packages[provider]['LINKERS'].append(tf_package)
    for provider in tf_packages[tf_package]['MD_REF']:
      if not provider in tf_packages:
        logging.warn('module \'%s\' referenced from package \'%s\' not found.' % (provider, tf_package))
        continue
      if not tf_package in tf_packages[provider]['LINKERS']:
        tf_packages[provider]['LINKERS'].append(tf_package)
    # remove unneeded objects
    tf_packages[tf_package].pop('RS_REF')
    tf_packages[tf_package].pop('MD_REF')
  # Make final structure with only dependences
  dependencies = {}
  for pk in tf_packages:
    if len(tf_packages[pk]['LINKERS']) > 0:
      dependencies[pk] = tf_packages[pk]['LINKERS']
      logging.debug('PAK: ' + str(pk))
      logging.debug(tf_packages[pk]['LINKERS'])
  logging.debug('dependecy graph: %s' % str(dependencies))
  return dependencies

def compute_build_steps(changelog, tf_root):
  """
  From a list of modified files and a terraform configuration root, walk through
  all the terraform folders, infer dependencies by looking at the tf files and
  generate an ordered build list.
  The providfed change log file must be in the format produced by the 
  'git status --porcelain' command. Example:
  ?? terraform/programs/it/cloud/iam_bindings.tf
  ?? terraform/modules/program/iam.tf
  ?? terraform/modules/tenant/iam.tf
  """
  tainted_packages = []
  regex = r'^.*(' + tf_root + '\/.+\.(tf|tfvars))$'
  p = re.compile(regex)
  with open(changelog) as f:
    expanded_lines = []
    for line in f.readlines():
      line = line.strip()
      if line.endswith('/'):
        for fn in glob.iglob(line[line.find(' ')+1:] + '**', recursive=True):
          expanded_lines.append(fn)
      else:
        expanded_lines.append(line)
    for line in expanded_lines:
      m = p.match(line)
      if m:
        changed_tf_pkg = os.path.dirname(m.group(1))
        if not changed_tf_pkg in tainted_packages:
          tainted_packages.append(changed_tf_pkg)
  logging.debug('Tainted: ' + str(tainted_packages))
  # arrange the order of the builds
  deps = compute_deps(tf_root)
  # get the list of nodes that must be touched
  adjacency_list = defaultdict()
  visited_list = defaultdict()
  for pkg in tainted_packages:
    build_chain = get_build_chain(deps, pkg)
    logging.debug('build chain [%s]: %s' %(pkg, ' -> '.join(build_chain)))
    for node in build_chain:
      adjacency_list[node] = deps.get(node, '')
      visited_list[node] = False
  output_stack = []
  for vertex in visited_list:
    topology_sort(vertex, adjacency_list, visited_list, output_stack)
  return output_stack

def main(changelog, tf_root, output):
  tf_root = os.path.normpath(tf_root)
  if not os.path.isdir(tf_root):
    logging.error('directory provided in --tf-root does not exist: ' + tf_root)
    sys.exit(1)
  if not os.path.exists(changelog):
    logging.error('file provided in --changelog does not exist: ' + changelog)
    sys.exit(1)
  build_steps = compute_build_steps(changelog, tf_root)
  if output:
    output_file = open(output, 'w')
    for bs in build_steps:
      output_file.write(bs + '\n')
  else: 
    for bs in build_steps:
      print(bs)

def parse_args(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--tf-root', required=True,
                      help='directory where to look for program folders')
  parser.add_argument('--changelog', required=True,
                      help='list of files that were modified (git status --porcelain)')
  parser.add_argument('--output', required=False,
                      help='write build order to this file instead of std output')
  parser.add_argument('--log-level', required=False,
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO',
                      help='set log level')
  return parser.parse_args(argv)

if __name__ == '__main__':
  args = parse_args(sys.argv[1:])
  logging.getLogger().setLevel(getattr(logging, args.log_level))
  FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
  logging.basicConfig(format=FORMAT)
  main(args.changelog, args.tf_root, args.output)
