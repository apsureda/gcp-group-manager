#!/usr/bin/python

"""Generate Terraform configuration files from a set of predefined templates.

Copyright 2021 Google LLC. This software is provided as-is, without warranty or
representation for any use or purpose. Your use of it is subject to your 
agreement with Google.  
"""
import os
import sys
import shutil
import argparse
import logging
import yaml
import json
import jinja2
import tf_dump
import glob

conf_cache = {}

def parse_args(argv):
  parser = argparse.ArgumentParser()

  # common options
  parser.add_argument('--template-dir', help='location of tf template files')
  parser.add_argument('--tf-out', help='directory where the generated Terraform files should be written')
  parser.add_argument('--config', help='yaml file containing the common configuration settings')
  parser.add_argument('--revert-forced-updates', action='store_true',
                      help='set to false any existing force_updates flag found in requests file')
  parser.add_argument('--resources', help='yaml file containing the resources to create')
  parser.add_argument('--log-level', required=False,
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO',
                      help='set log level')

  # add sub commands
  subparsers = parser.add_subparsers(help='available commands')

  log_config = subparsers.add_parser('ci-groups', help='generates cloud identity groups')
  log_config.set_defaults(func=cmd_ci_groups)

  return parser.parse_args(argv)

def get_config(config_file, mandatory_fields):
  """
  Reads a config file and checks for duplicates and for the existence of the 
  optional mandatory fields provided.
  """
  # Check if we have already loaded this config file
  global conf_cache
  if config_file in conf_cache:
      return conf_cache[config_file]
  # open the requests file, which is in YAML format
  stream = open(config_file, "r")
  config_stream = yaml.load_all(stream, Loader=yaml.FullLoader)
  config_params = {}
  # YAML files can have multiple "documents" go through the file and append all the
  # elements in a single map
  for doc in config_stream:
    for k,v in doc.items():
      if k in config_params:
        logging.error('\'%s\' defined twice in config file %s' % (k, config_file))
        sys.exit(1)
      config_params[k] = v
  # check that we have all the required config params
  if mandatory_fields and len(mandatory_fields) > 0:
    for k in mandatory_fields:
      if not k in config_params:
        logging.error('missing required param in config file: \'%s\'' % (k))
        sys.exit(1)
  # put this in our config cache to avoid loading each time
  conf_cache[config_file] = config_params
  return config_params

def generate_tf_files(template_dir, tf_out, tpl_type, context, replace, prefix=None):
  """
  Generates terraform files given a context and template folder.
  - template_dir: the folder containing the jinja templates to use.
  - tf_out: the folder where the resulting terraform files will be written.
  - tpl_type: the type of template to use (sub-folder of the templates folder).
  - comntext: the content object that will be passed to the jinja templates.
  - replace: remove previous output files before writing new ones.
  - prefix: used when generating several terraform configurations in the same
    output folder (currently used for projects).
  """
  # initialize jinja2 environment for tf templates
  env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), trim_blocks=True)
  # check for templates with the current template type
  template_list = []
  if os.path.isdir(template_dir + '/' + tpl_type):
    template_list = os.listdir(template_dir + '/' + tpl_type)
  if len(template_list) == 0:
    logging.warning('no templates found for request of type \'%s\'' % (tpl_type))
    return False

  # folder where the tf files will be generated
  out_folder = tf_out
  if prefix:
    out_folder += '/' + prefix

  # if replace requested, remove previous files. If not requested but previous files
  # present, return.
  if os.path.isdir(out_folder):
    if replace:
      shutil.rmtree(out_folder)
      logging.debug('removing previous config: \'%s\'' %(out_folder))
      os.mkdir(out_folder)
    else:
      logging.info('ignoring request \'%s\'. Found previous terraform config folder.' % (out_folder))
      return False
  else:
    os.makedirs(out_folder)

  # apply the selected templates
  logging.info('using context: %s' % (json.dumps(context, sort_keys=True)))
  for ttype in ['common', tpl_type]:
    template_list = []
    if os.path.isdir(template_dir + '/' + ttype):
      template_list = os.listdir(template_dir + '/' + ttype)
    else:
      continue

    for tplfile in template_list:
      # remove junk files
      if tplfile.startswith('.'):
        continue
      template = env.get_template(ttype + '/' + tplfile)
      out_file_name = out_folder + '/' + tplfile
      # remove jinjs2 extensions
      if out_file_name.endswith('.j2'):
        out_file_name = out_file_name[:-3]
      logging.debug('generating config file: \'%s\'' % (out_file_name))
      rendered = template.render(context=context).strip()
      if len(rendered) > 0:
        out_file = open(out_file_name, "w")
        out_file.write(rendered)
        out_file.close()
      elif os.path.exists(out_file_name):
        logging.debug('empty output. Remving previous file: \'%s\'' % (out_file_name))
        os.remove(out_file_name)
  return True

def cmd_ci_groups(args):
  """
  Generates the terraform files for Cloud Identity groups based on the group folder hierarchy.
  """
  def tf_group(group):
    """
    Generates the terraform code for a group
    """
    tf_block = tf_dump.TFBlock(block_type='resource', labels=['google_cloud_identity_group', group['full_name']])
    tf_block.add_element('display_name', '"%s"' % (group['full_name']))
    tf_block.add_element('initial_group_config', '"WITH_INITIAL_OWNER"')
    tf_block.add_element('parent', '"%s"' % (parent))
    tf_key_block = tf_dump.TFBlock(block_type='group_key')
    tf_key_block.add_element('id', '"%s"' % (group['unique_id']))
    tf_block.add_block(tf_key_block)
    labels = {
      '"cloudidentity.googleapis.com/groups.discussion_forum"' : '""'
    }
    tf_block.add_element('labels', labels)
    return tf_block.dump_tf()

  def tf_member(group_id, member_id, roles):
    """
    Generates the terraform code for a group member
    """
    member_id = member_id.lower()
    tf_block = tf_dump.TFBlock(block_type='resource', labels=['google_cloud_identity_group_membership', group_id + '_' + member_id.lower().replace('@', '_').replace('.', '_')])
    tf_block.add_element('group', 'google_cloud_identity_group.%s.id' % (group_id))
    tf_key_block = tf_dump.TFBlock(block_type='preferred_member_key')
    tf_key_block.add_element('id', '"%s"' % (member_id))
    tf_block.add_block(tf_key_block)
    for role in roles:
      tf_roles_block = tf_dump.TFBlock(block_type='roles')
      tf_roles_block.add_element('name', '"%s"' % (role))
      tf_block.add_block(tf_roles_block)
    return tf_block.dump_tf()

  # check that the resources provided is a folder
  if not os.path.exists(args.resources) or not os.path.isdir(args.resources):
    logging.error('the provided resource path does not exist or is not a folder: ' + args.resources)
    return False

  all_groups = {}
  groups_by_src = {}

  # get the list of group configuration files
  conf_files = glob.glob(args.resources + '/**/*.yaml', recursive=True)

  # read configuration file
  tf_config = get_config(args.config, ['gcs_bucket', 'group_domain', 'group_parent', 'tf_service_account'])

  # the number of folder components to be used in the group prefix
  prefix_length = 2
  domain = tf_config['group_domain']
  parent = tf_config['group_parent']
  rs_bucket = tf_config['gcs_bucket']
  tf_sa = tf_config['tf_service_account']

  # parse group config files
  for conf_file in conf_files:
    f = open(conf_file, "r")
    resources = yaml.load(f, Loader=yaml.FullLoader)
    # ignore empty files
    if not resources:
      continue
    for group in resources:
      if not 'name' in group:
        logging.error('group definitions must have a name: ' + conf_file)
        return False
      g_name = group['name']
      # the path of the file: remove the root folder and the file name
      g_path = conf_file[len(args.resources)+1:conf_file.rfind('/')]
      g_prefix = '-'.join(g_path.lower().split('/')[0:prefix_length])
      # create the unique ID for the group, which is composed of the prefix, plus the domain.
      group['full_name'] = g_prefix + '-' + g_name
      g_unique_id = group['full_name'] + '@' + domain
      group['unique_id'] = g_unique_id
      group['path'] = g_path
      group['conf'] = conf_file
      # ignore entry if already exists
      if g_unique_id in all_groups:
        # TODO: need to kee a record of previously added groups because a new duplicate could appear before the existing one.
        logging.warn('group ' + g_unique_id + ' was already defined in ' + all_groups[g_unique_id]['conf'] + '. Ignoring entry from ' + conf_file)
        continue
      # add the group to the list of groups by unique id
      all_groups[g_unique_id] = group
      # add the group to the list of groups by source file
      if conf_file in groups_by_src:
        groups_by_src[conf_file].append(group)
      else:
        groups_by_src[conf_file] = [group]

  # create a terraform configuration for each one of the config folders
  refreshed_configs = {}
  for conf_file in groups_by_src.keys():
    groups = groups_by_src[conf_file]
    # the path of the file: remove the root folder and the file name
    conf_path = conf_file[len(args.resources)+1:conf_file.rfind('/')]
    out_dir = args.tf_out + '/' + conf_path
    if not os.path.exists(out_dir):
      os.makedirs(out_dir)
    elif not out_dir in refreshed_configs:
      # generate the terraform config file
      commons_context = {
        'gcs_bucket' : rs_bucket,
        'gcs_prefix' : 'ci_groups/' + conf_path,
        'tf_sa' : tf_sa
      }
      generate_tf_files(args.template_dir, out_dir, 'common', commons_context, True)
      refreshed_configs[out_dir] = True
    # the resulting file name: replace .yaml by .tf
    tf_file_name = conf_file[conf_file.rfind('/')+1:conf_file.rfind('.')] + '.tf'
    tf_output = ''
    for group in groups:
      tf_output += tf_group(group) + '\n\n'
      # consolidate the list of members, since each member can have multiple roles
      all_members = {}
      # first, create the list with the MEMBER role for each member
      for mtype in ['members', 'managers', 'owners']:
        for member in group[mtype]:
          if not member in all_members:
            all_members[member] = ['MEMBER']
      for member in group['owners']:
        all_members[member].append('OWNER')
      for member in group['managers']:
        all_members[member].append('MANAGER')
      for member in all_members:
        tf_output += tf_member(group['full_name'], member, all_members[member]) + '\n\n'
    # write the tf code for this file
    f = open(out_dir + '/' + tf_file_name, 'w')
    f.write(tf_output)
    f.close()
  return True

if __name__ == '__main__':
  args = parse_args(sys.argv[1:])
  logging.getLogger().setLevel(getattr(logging, args.log_level))
  FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
  logging.basicConfig(format=FORMAT)
  args.func(args)
