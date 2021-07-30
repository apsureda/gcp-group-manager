#!/usr/bin/python

"""Generate a unified CODEOWNERS file from OWNER files found in the individual folders.

Copyright 2021 Google LLC. This software is provided as-is, without warranty or
representation for any use or purpose. Your use of it is subject to your 
agreement with Google.  
"""
import os
import sys
import argparse
import logging
import glob

def parse_args(argv):
  parser = argparse.ArgumentParser()

  # common options
  parser.add_argument('--repo-root', help='path to the root of the code repository', required=True)
  parser.add_argument('--codeowners-out', help='path of the generated CODEOWNERS file', required=False)
  parser.add_argument('--add-owners', help='add owners in the form: /path1=owner1,owner2;/path2=owner3,owner4', required=False)
  parser.add_argument('--log-level', required=False,
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO',
                      help='set log level')
  return parser.parse_args(argv)

def parse_owners(args):
  # get the list of the OWNERS files found in the repository
  owners_files = glob.glob(args.repo_root + '/**/OWNERS', recursive=True)
  owners_files.sort()

  # parse the OWNERS files, and generate consolidated CODEOWNERS file
  path_owners = {}
  for owners_file in owners_files:
    dirname = os.path.dirname(owners_file)
    f = open(owners_file, "r")
    members = []
    for line in f:
      owners_line = line
      comment_idx = owners_line.find('#')
      if comment_idx != -1:
        owners_line = owners_line[:comment_idx]
      owners_line = owners_line.strip()
      members.append(owners_line)
    path_owners['/' + dirname] = members

  # add owners from command line param if any
  if args.add_owners:
    folder_owners = args.add_owners.split(';')
    for folder_owner in folder_owners:
      folder_pair = folder_owner.split('=')
      if len(folder_pair) != 2:
        logging.error('invalid --codeowners-out value. Please, use the proper format: /path1=owner1,owner2;/path2=owner3,owner4')
        sys.exit(1)
      folder = folder_pair[0]
      members = folder_pair[1].split(',')
      if not folder in path_owners:
        path_owners[folder] = members
      else:
        path_owners[folder].extend(members)
      print(path_owners)

  # I no code owners were found, just retrun
  if len(path_owners) == 0:
    return

  # write CODEOWNERS data to destination file (or stdout)
  if args.codeowners_out:
    dirname = os.path.dirname(args.codeowners_out)
    if not os.path.exists(dirname):
      os.makedirs(dirname)
    cof = open(args.codeowners_out, "w")
  else:
    cof = sys.stdout
  for k in sorted(path_owners.keys()):
    # write the line for the yaml config files folder
    cof.write(k + ' ' + ' '.join(path_owners[k]) + '\n')
  cof.close()

if __name__ == '__main__':
  args = parse_args(sys.argv[1:])
  logging.getLogger().setLevel(getattr(logging, args.log_level))
  FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
  logging.basicConfig(format=FORMAT)
  parse_owners(args)
