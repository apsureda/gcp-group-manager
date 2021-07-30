import sys

"""Generate decently formated Terraform code from python code. See an example
of usage in the main function.

Copyright 2021 Google LLC. This software is provided as-is, without warranty or
representation for any use or purpose. Your use of it is subject to your 
agreement with Google.  
"""

class TFBlock(object):
  """
  This class represents a Terraform resource. You can add elements and blocks to it,
  and use the dump_tf function to obtain the resulting terraform code.
  """

  # these will be used to define the preferred order of keys in the terraform file.
  # Keys not included here will be printed in alphabetical order. Feel free to add
  # more lines if the resource you are using is not included in this list.
  _KEY_ORDER = {
    'resource/google_compute_disk' : ['name', 'project', 'zone', 'type', 'size'],
    'resource/google_compute_instance' : ['name', 'project', 'zone', 'machine_type',
      'min_cpu_platform', 'boot_disk', 'attached_disk', 'scratch_disk', 
      'network_interface', 'can_ip_forward', 'service_account', 'metadata' ],
    'service_account' : ['email', 'scopes'],
    'boot_disk' : ['device_name', 'auto_delete', 'initialize_params'],
    'resource/google_organization_policy' : ['org_id', 'constraint'],
    'resource/google_folder_organization_policy' : ['folder', 'constraint'],
    'resource/google_project_organization_policy' : ['project', 'constraint'],
    'resource/google_logging_billing_account_sink' : ['billing_account', 'name', 'destination', 'filter', 'include_children'],
    'resource/google_logging_organization_sink' : ['org_id', 'name', 'destination', 'filter', 'include_children'],
    'resource/google_logging_folder_sink' : ['folder', 'name', 'destination', 'filter', 'include_children'],
    'resource/google_logging_project_sink' : ['project', 'name', 'destination', 'filter', 'include_children'],
  }

  def __init__(self, block_type=None, labels=None, elements=None):
    """
    Create a terraform object. 
    - block_type can be "resource" or "data"
    - labels are the labels assocuated to the terraform object. Example:
      ['google_compute_instance', 'my_instance']
    - elements are the optional elemets to add to the terraform object. You can use
      the add_element function to add elements later.
    """
    self.block_type = block_type
    self.labels = labels
    if elements:
      self.elements = elements
    else:
      self.elements = {}
  
  def add_element(self, key, value):
    """
    Add and element to the map of this block's elements.
    """
    self.elements[key] = value

  def add_elements(self, map):
    """
    Add all elements from a map to this block's elements.
    """
    if type(map) is dict:
      for key, value in map.items():
        self.elements[key] = value

  def add_block(self, nblock):
    """
    Add a named block to the current block.
    """
    key = nblock.block_type
    if not key in self.elements:
      self.elements[key] = nblock
    else:
      if type(self.elements[key]) is list:
        self.elements[key].append(nblock)
      else:
        self.elements[key] = [self.elements[key], nblock]

  def is_anonymous(self):
    """
    Anonymous blocks are the ones that do not have any block type ID attached to
    them. Example, the elements inside the list of network interfaces:
     network_interface = [
      {
        subnetwork         = "default"
        subnetwork_project = "factory-dm2tf-tests"
      },
    ]
    """
    return self.block_type is None

  def order_elements(self, u_elements):
    """
    Gets a list of keys found in a terraform resource, and applies the preferred
    order as defined in the _KEY_ORDER. 
    """
    order_types = []
    o_elements = []
    # most specific order type takes priority (e.g. 'resource/google_compute_disk')
    if self.block_type and self.labels:
      order_types.append(self.block_type + '/' + self.labels[0])
    # specific order type comes next (e.g. 'resource')
    if self.block_type:
      order_types.append(self.block_type)
    # pile in keys as they appear in order type configurations
    for ot in order_types:
      if ot in self._KEY_ORDER:
        for k in self._KEY_ORDER[ot]:
          if k in u_elements and not k in o_elements:
            o_elements.append(k)
    # remaining keys will be added in alphabetical order
    for k in sorted(u_elements):
      if k in u_elements and not k in o_elements:
        o_elements.append(k) 
    return o_elements

  def dump_tf(self, context=None, indent=' '):
    """
    Returns the terraform code resulting from the current structure. This
    function will traverse the block's elements recursively and return the
    full terraform code of the resource by producing the terraform output of
    each one of the elements. The elements can be:
     - Primitives: strings / booleans
     - Blocks: with or without block type and labels
     - Lists: typically containing anonymous blocks or strings
    """
    # If no context was provided, this function was called on the objects itself.
    # Context is provided for printing non block elements (strings, booleans, lists)
    if not context:
      context = self
    # For ease of use, we allow passing anonymous blocks as plain dict structures.
    # We convert these to TFBlockhere to simplify the logic.
    if type(context) is dict:
      context = TFBlock(elements=context)
    # This is where we will concatenate the output for each element.
    output = ''
    INDENT = '  '
    if isinstance(context, TFBlock):
      # block opening:
      # resource "google_compute_instance" "sap-hana-single-1561556081-tf" {
      if self.block_type:
        output += self.block_type + ' '
      if self.labels:
        for l in self.labels:
          output += '"' + l + '" '
      output += '{\n'

      # print arguments and blocks included in the block. these can be contained
      # under the 'ELEMENTS' key, or just plain in the comntext if no other
      # metadata was needed for this block.
      if len(self.elements) > 0:
        # ket a sorted list of the element keys
        s_elements = self.order_elements(self.elements.keys())
        # get max key length for padding
        max_length = max([len(x) for x in s_elements])
        # print out each key followed by its associated value or block
        for k in s_elements:
          v = self.elements[k]
          # convert plain dict structs to TFBlock
          if type(v) is dict:
            v = TFBlock(elements=v)
          if isinstance(v, TFBlock):
            output += INDENT
            # blocks with block type are printed without 'key ='
            if v.is_anonymous():
              output += k.ljust(max_length) + ' = '
            sub_block = v.dump_tf(indent=indent + INDENT)
            output += sub_block.replace('\n', '\n' + indent)
            output += '\n'
            continue
          if type(v) is list and len(v) > 0:
            if type(v[0]) is TFBlock and k == v[0].block_type:
              for ve in v:
                sub_block = ve.dump_tf(indent=indent)
                output += sub_block.replace('\n', '\n' + indent)
                output += '\n'
            else:
              output += INDENT
              output += k.ljust(max_length) + ' = '
              sub_block = self.dump_tf(v, indent=indent + INDENT)
              output += sub_block.replace('\n', '\n' + indent)
              output += '\n'
            continue

          # convert integers to strings. Terraform does not take integers.
          if type(v) is int:
            v = str(v)
          if type(v) is str:
            output += INDENT + k.ljust(max_length) + ' = '
            output += v + '\n'
            #output += '"' + v + '"\n'
          elif type(v) is bool:
            output += INDENT + k.ljust(max_length) + ' = '
            if v:
              output += 'true\n'
            else:
              output += 'false\n'
      output += '}'
    elif type(context) is list:
      output += '[\n'
      for v in context:
        if type(v) is dict:
          v = TFBlock(elements=v)
        if type(v) is str:
          output += '  "' + v + '",\n'
        elif isinstance(v, TFBlock):
          sub_block = v.dump_tf(indent=indent+INDENT)
          output += INDENT + sub_block.replace('\n', '\n' + indent) + ',\n'
      output += ']'
    return output

if __name__ == '__main__':
  test_block = TFBlock(block_type='resource', labels=['google_compute_instance', 'sap-hana-single'])
  test_block.add_element('name', '"sap-hana-single"')
  test_block.add_element('can_ip_forward', True)

  test_net_if_1 = TFBlock(block_type='network_interface')
  test_net_if_1.add_element('subnetwork', '"default"')
  test_block.add_block(test_net_if_1)
  test_net_if_2 = TFBlock(block_type='network_interface')
  test_net_if_2.add_element('subnetwork', '"custom"')
  test_block.add_block(test_net_if_2)

  anon_block_1 = TFBlock()
  anon_block_1.add_element('key_1', '"val_1"')
  anon_block_2 = TFBlock()
  anon_block_2.add_element('key_2', '"val_2"')
  test_block.add_element('anon_block', [anon_block_1, anon_block_2])
  
  #print(test_net_if.dump_tf())
  print(test_block.dump_tf())

  sys.exit(0)
