#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# This is a DOCUMENTATION stub specific to this module, it extends
# a documentation fragment located in ansible.utils.module_docs_fragments
DOCUMENTATION = '''
---
module: rax
short_description: create / delete an instance in Rackspace Public Cloud
description:
     - creates / deletes a Rackspace Public Cloud instance and optionally
       waits for it to be 'running'.
version_added: "1.2"
options:
  auto_increment:
    description:
      - Whether or not to increment a single number with the name of the
        created servers. Only applicable when used with the I(group) attribute
        or meta key.
    default: yes
    choices:
      - "yes"
      - "no"
    version_added: 1.5
  config_drive:
    description:
      - Attach read-only configuration drive to server as label config-2
    default: no
    choices:
      - "yes"
      - "no"
    version_added: 1.7
  count:
    description:
      - number of instances to launch
    default: 1
    version_added: 1.4
  count_offset:
    description:
      - number count to start at
    default: 1
    version_added: 1.4
  disk_config:
    description:
      - Disk partitioning strategy
    choices:
      - auto
      - manual
    version_added: '1.4'
    default: auto
  exact_count:
    description:
      - Explicitly ensure an exact count of instances, used with
        state=active/present
    default: no
    choices:
      - "yes"
      - "no"
    version_added: 1.4
  extra_client_args:
    description:
      - A hash of key/value pairs to be used when creating the cloudservers
        client. This is considered an advanced option, use it wisely and
        with caution.
    version_added: 1.6
  extra_create_args:
    description:
      - A hash of key/value pairs to be used when creating a new server.
        This is considered an advanced option, use it wisely and with caution.
    version_added: 1.6
  files:
    description:
      - Files to insert into the instance. remotefilename:localcontent
    default: null
  flavor:
    description:
      - flavor to use for the instance
    default: null
  group:
    description:
      - host group to assign to server, is also used for idempotent operations
        to ensure a specific number of instances
    version_added: 1.4
  image:
    description:
      - image to use for the instance. Can be an C(id), C(human_id) or C(name)
    default: null
  instance_ids:
    description:
      - list of instance ids, currently only used when state='absent' to
        remove instances
    version_added: 1.4
  key_name:
    description:
      - key pair to use on the instance
    default: null
    aliases:
      - keypair
  meta:
    description:
      - A hash of metadata to associate with the instance
    default: null
  name:
    description:
      - Name to give the instance
    default: null
  networks:
    description:
      - The network to attach to the instances. If specified, you must include
        ALL networks including the public and private interfaces. Can be C(id)
        or C(label).
    default:
      - public
      - private
    version_added: 1.4
  state:
    description:
      - Indicate desired state of the resource
    choices:
      - present
      - absent
    default: present
  user_data:
    description:
      - Data to be uploaded to the servers config drive. This option implies
        I(config_drive). Can be a file path or a string
    version_added: 1.7
  wait:
    description:
      - wait for the instance to be in state 'running' before returning
    default: "no"
    choices:
      - "yes"
      - "no"
  wait_timeout:
    description:
      - how long before wait gives up, in seconds
    default: 300
author: Jesse Keating, Matt Martz
extends_documentation_fragment: rackspace.openstack
'''

EXAMPLES = '''
- name: Build a Cloud Server
  gather_facts: False
  tasks:
    - name: Server build request
      local_action:
        module: rax
        credentials: ~/.raxpub
        name: rax-test1
        flavor: 5
        image: b11d9567-e412-4255-96b9-bd63ab23bcfe
        key_name: my_rackspace_key
        files:
          /root/test.txt: /home/localuser/test.txt
        wait: yes
        state: present
        networks:
          - private
          - public
      register: rax

- name: Build an exact count of cloud servers with incremented names
  hosts: local
  gather_facts: False
  tasks:
    - name: Server build requests
      local_action:
        module: rax
        credentials: ~/.raxpub
        name: test%03d.example.org
        flavor: performance1-1
        image: ubuntu-1204-lts-precise-pangolin
        state: present
        count: 10
        count_offset: 10
        exact_count: yes
        group: test
        wait: yes
      register: rax
'''

try:
    import pyrax
    HAS_PYRAX = True
except ImportError:
    HAS_PYRAX = False


def create(module, names=[], flavor=None, image=None, meta={}, key_name=None,
           files={}, wait=True, wait_timeout=300, disk_config=None,
           group=None, nics=[], extra_create_args={}, user_data=None,
           config_drive=False, existing=[]):
    cs = pyrax.cloudservers
    changed = False

    if user_data:
        config_drive = True

    if user_data and os.path.isfile(user_data):
        try:
            f = open(user_data)
            user_data = f.read()
            f.close()
        except Exception, e:
            module.fail_json(msg='Failed to load %s' % user_data)

    # Handle the file contents
    for rpath in files.keys():
        lpath = os.path.expanduser(files[rpath])
        try:
            fileobj = open(lpath, 'r')
            files[rpath] = fileobj.read()
            fileobj.close()
        except Exception, e:
            module.fail_json(msg='Failed to load %s' % lpath)
    try:
        servers = []
        for name in names:
            servers.append(cs.servers.create(name=name, image=image,
                                             flavor=flavor, meta=meta,
                                             key_name=key_name,
                                             files=files, nics=nics,
                                             disk_config=disk_config,
                                             config_drive=config_drive,
                                             userdata=user_data,
                                             **extra_create_args))
    except Exception, e:
        module.fail_json(msg='%s' % e.message)
    else:
        changed = True

    if wait:
        end_time = time.time() + wait_timeout
        infinite = wait_timeout == 0
        while infinite or time.time() < end_time:
            for server in servers:
                try:
                    server.get()
                except:
                    server.status == 'ERROR'

            if not filter(lambda s: s.status not in FINAL_STATUSES,
                          servers):
                break
            time.sleep(5)

    success = []
    error = []
    timeout = []
    for server in servers:
        try:
            server.get()
        except:
            server.status == 'ERROR'
        instance = rax_to_dict(server, 'server')
        if server.status == 'ACTIVE' or not wait:
            success.append(instance)
        elif server.status == 'ERROR':
            error.append(instance)
        elif wait:
            timeout.append(instance)

    untouched = [rax_to_dict(s, 'server') for s in existing]
    instances = success + untouched

    results = {
        'changed': changed,
        'action': 'create',
        'instances': instances,
        'success': success,
        'error': error,
        'timeout': timeout,
        'instance_ids': {
            'instances': [i['id'] for i in instances],
            'success': [i['id'] for i in success],
            'error': [i['id'] for i in error],
            'timeout': [i['id'] for i in timeout]
        }
    }

    if timeout:
        results['msg'] = 'Timeout waiting for all servers to build'
    elif error:
        results['msg'] = 'Failed to build all servers'

    if 'msg' in results:
        module.fail_json(**results)
    else:
        module.exit_json(**results)


def delete(module, instance_ids=[], wait=True, wait_timeout=300, kept=[]):
    cs = pyrax.cloudservers

    changed = False
    instances = {}
    servers = []

    for instance_id in instance_ids:
        servers.append(cs.servers.get(instance_id))

    for server in servers:
        try:
            server.delete()
        except Exception, e:
            module.fail_json(msg=e.message)
        else:
            changed = True

        instance = rax_to_dict(server, 'server')
        instances[instance['id']] = instance

    # If requested, wait for server deletion
    if wait:
        end_time = time.time() + wait_timeout
        infinite = wait_timeout == 0
        while infinite or time.time() < end_time:
            for server in servers:
                instance_id = server.id
                try:
                    server.get()
                except:
                    instances[instance_id]['status'] = 'DELETED'
                    instances[instance_id]['rax_status'] = 'DELETED'

            if not filter(lambda s: s['status'] not in ('', 'DELETED',
                                                        'ERROR'),
                          instances.values()):
                break

            time.sleep(5)

    timeout = filter(lambda s: s['status'] not in ('', 'DELETED', 'ERROR'),
                     instances.values())
    error = filter(lambda s: s['status'] in ('ERROR'),
                   instances.values())
    success = filter(lambda s: s['status'] in ('', 'DELETED'),
                     instances.values())

    instances = [rax_to_dict(s, 'server') for s in kept]

    results = {
        'changed': changed,
        'action': 'delete',
        'instances': instances,
        'success': success,
        'error': error,
        'timeout': timeout,
        'instance_ids': {
            'instances': [i['id'] for i in instances],
            'success': [i['id'] for i in success],
            'error': [i['id'] for i in error],
            'timeout': [i['id'] for i in timeout]
        }
    }

    if timeout:
        results['msg'] = 'Timeout waiting for all servers to delete'
    elif error:
        results['msg'] = 'Failed to delete all servers'

    if 'msg' in results:
        module.fail_json(**results)
    else:
        module.exit_json(**results)


def cloudservers(module, state=None, name=None, flavor=None, image=None,
                 meta={}, key_name=None, files={}, wait=True, wait_timeout=300,
                 disk_config=None, count=1, group=None, instance_ids=[],
                 exact_count=False, networks=[], count_offset=0,
                 auto_increment=False, extra_create_args={}, user_data=None,
                 config_drive=False):
    cs = pyrax.cloudservers
    cnw = pyrax.cloud_networks
    if not cnw:
        module.fail_json(msg='Failed to instantiate client. This '
                             'typically indicates an invalid region or an '
                             'incorrectly capitalized region name.')

    servers = []

    # Add the group meta key
    if group and 'group' not in meta:
        meta['group'] = group
    elif 'group' in meta and group is None:
        group = meta['group']

    # Normalize and ensure all metadata values are strings
    for k, v in meta.items():
        if isinstance(v, list):
            meta[k] = ','.join(['%s' % i for i in v])
        elif isinstance(v, dict):
            meta[k] = json.dumps(v)
        elif not isinstance(v, basestring):
            meta[k] = '%s' % v

    # When using state=absent with group, the absent block won't match the
    # names properly. Use the exact_count functionality to decrease the count
    # to the desired level
    was_absent = False
    if group is not None and state == 'absent':
        exact_count = True
        state = 'present'
        was_absent = True

    if image:
        image = rax_find_image(module, pyrax, image)

    nics = []
    if networks:
        for network in networks:
            nics.extend(rax_find_network(module, pyrax, network))

    # act on the state
    if state == 'present':
        for arg, value in dict(name=name, flavor=flavor,
                               image=image).iteritems():
            if not value:
                module.fail_json(msg='%s is required for the "rax" module' %
                                     arg)

        # Idempotent ensurance of a specific count of servers
        if exact_count is not False:
            # See if we can find servers that match our options
            if group is None:
                module.fail_json(msg='"group" must be provided when using '
                                     '"exact_count"')
            else:
                if auto_increment:
                    numbers = set()

                    try:
                        name % 0
                    except TypeError, e:
                        if e.message.startswith('not all'):
                            name = '%s%%d' % name
                        else:
                            module.fail_json(msg=e.message)

                    pattern = re.sub(r'%\d*[sd]', r'(\d+)', name)
                    for server in cs.servers.list():
                        if server.metadata.get('group') == group:
                            servers.append(server)
                        match = re.search(pattern, server.name)
                        if match:
                            number = int(match.group(1))
                            numbers.add(number)

                    number_range = xrange(count_offset, count_offset + count)
                    available_numbers = list(set(number_range)
                                             .difference(numbers))
                else:
                    for server in cs.servers.list():
                        if server.metadata.get('group') == group:
                            servers.append(server)

                # If state was absent but the count was changed,
                # assume we only wanted to remove that number of instances
                if was_absent:
                    diff = len(servers) - count
                    if diff < 0:
                        count = 0
                    else:
                        count = diff

                if len(servers) > count:
                    state = 'absent'
                    kept = servers[:count]
                    del servers[:count]
                    instance_ids = []
                    for server in servers:
                        instance_ids.append(server.id)
                    delete(module, instance_ids=instance_ids, wait=wait,
                           wait_timeout=wait_timeout, kept=kept)
                elif len(servers) < count:
                    if auto_increment:
                        names = []
                        name_slice = count - len(servers)
                        numbers_to_use = available_numbers[:name_slice]
                        for number in numbers_to_use:
                            names.append(name % number)
                    else:
                        names = [name] * (count - len(servers))
                else:
                    instances = []
                    instance_ids = []
                    for server in servers:
                        instances.append(rax_to_dict(server, 'server'))
                        instance_ids.append(server.id)
                    module.exit_json(changed=False, action=None,
                                     instances=instances,
                                     success=[], error=[], timeout=[],
                                     instance_ids={'instances': instance_ids,
                                                   'success': [], 'error': [],
                                                   'timeout': []})
        else:
            if group is not None:
                if auto_increment:
                    numbers = set()

                    try:
                        name % 0
                    except TypeError, e:
                        if e.message.startswith('not all'):
                            name = '%s%%d' % name
                        else:
                            module.fail_json(msg=e.message)

                    pattern = re.sub(r'%\d*[sd]', r'(\d+)', name)
                    for server in cs.servers.list():
                        if server.metadata.get('group') == group:
                            servers.append(server)
                        match = re.search(pattern, server.name)
                        if match:
                            number = int(match.group(1))
                            numbers.add(number)

                    number_range = xrange(count_offset,
                                          count_offset + count + len(numbers))
                    available_numbers = list(set(number_range)
                                             .difference(numbers))
                    names = []
                    numbers_to_use = available_numbers[:count]
                    for number in numbers_to_use:
                        names.append(name % number)
                else:
                    names = [name] * count
            else:
                search_opts = {
                    'name': '^%s$' % name,
                    'image': image,
                    'flavor': flavor
                }
                servers = []
                for server in cs.servers.list(search_opts=search_opts):
                    if server.metadata != meta:
                        continue
                    servers.append(server)

                if len(servers) >= count:
                    instances = []
                    for server in servers:
                        instances.append(rax_to_dict(server, 'server'))

                    instance_ids = [i['id'] for i in instances]
                    module.exit_json(changed=False, action=None,
                                     instances=instances, success=[], error=[],
                                     timeout=[],
                                     instance_ids={'instances': instance_ids,
                                                   'success': [], 'error': [],
                                                   'timeout': []})

                names = [name] * (count - len(servers))

        create(module, names=names, flavor=flavor, image=image,
               meta=meta, key_name=key_name, files=files, wait=wait,
               wait_timeout=wait_timeout, disk_config=disk_config, group=group,
               nics=nics, extra_create_args=extra_create_args,
               user_data=user_data, config_drive=config_drive,
               existing=servers)

    elif state == 'absent':
        if instance_ids is None:
            for arg, value in dict(name=name, flavor=flavor,
                                   image=image).iteritems():
                if not value:
                    module.fail_json(msg='%s is required for the "rax" '
                                         'module' % arg)
            search_opts = {
                'name': '^%s$' % name,
                'image': image,
                'flavor': flavor
            }
            for server in cs.servers.list(search_opts=search_opts):
                if meta != server.metadata:
                    continue
                servers.append(server)

            instance_ids = []
            for server in servers:
                if len(instance_ids) < count:
                    instance_ids.append(server.id)
                else:
                    break

        if not instance_ids:
            module.exit_json(changed=False, action=None, instances=[],
                             success=[], error=[], timeout=[],
                             instance_ids={'instances': [],
                                           'success': [], 'error': [],
                                           'timeout': []})

        delete(module, instance_ids=instance_ids, wait=wait,
               wait_timeout=wait_timeout)


def main():
    argument_spec = rax_argument_spec()
    argument_spec.update(
        dict(
            auto_increment=dict(default=True, type='bool'),
            config_drive=dict(default=False, type='bool'),
            count=dict(default=1, type='int'),
            count_offset=dict(default=1, type='int'),
            disk_config=dict(choices=['auto', 'manual']),
            exact_count=dict(default=False, type='bool'),
            extra_client_args=dict(type='dict', default={}),
            extra_create_args=dict(type='dict', default={}),
            files=dict(type='dict', default={}),
            flavor=dict(),
            group=dict(),
            image=dict(),
            instance_ids=dict(type='list'),
            key_name=dict(aliases=['keypair']),
            meta=dict(type='dict', default={}),
            name=dict(),
            networks=dict(type='list', default=['public', 'private']),
            service=dict(),
            state=dict(default='present', choices=['present', 'absent']),
            user_data=dict(no_log=True),
            wait=dict(default=False, type='bool'),
            wait_timeout=dict(default=300),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=rax_required_together(),
    )

    if not HAS_PYRAX:
        module.fail_json(msg='pyrax is required for this module')

    service = module.params.get('service')

    if service is not None:
        module.fail_json(msg='The "service" attribute has been deprecated, '
                             'please remove "service: cloudservers" from your '
                             'playbook pertaining to the "rax" module')

    auto_increment = module.params.get('auto_increment')
    config_drive = module.params.get('config_drive')
    count = module.params.get('count')
    count_offset = module.params.get('count_offset')
    disk_config = module.params.get('disk_config')
    if disk_config:
        disk_config = disk_config.upper()
    exact_count = module.params.get('exact_count', False)
    extra_client_args = module.params.get('extra_client_args')
    extra_create_args = module.params.get('extra_create_args')
    files = module.params.get('files')
    flavor = module.params.get('flavor')
    group = module.params.get('group')
    image = module.params.get('image')
    instance_ids = module.params.get('instance_ids')
    key_name = module.params.get('key_name')
    meta = module.params.get('meta')
    name = module.params.get('name')
    networks = module.params.get('networks')
    state = module.params.get('state')
    user_data = module.params.get('user_data')
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    setup_rax_module(module, pyrax)

    if extra_client_args:
        pyrax.cloudservers = pyrax.connect_to_cloudservers(
            region=pyrax.cloudservers.client.region_name,
            **extra_client_args)
        client = pyrax.cloudservers.client
        if 'bypass_url' in extra_client_args:
            client.management_url = extra_client_args['bypass_url']

    if pyrax.cloudservers is None:
        module.fail_json(msg='Failed to instantiate client. This '
                             'typically indicates an invalid region or an '
                             'incorrectly capitalized region name.')

    cloudservers(module, state=state, name=name, flavor=flavor,
                 image=image, meta=meta, key_name=key_name, files=files,
                 wait=wait, wait_timeout=wait_timeout, disk_config=disk_config,
                 count=count, group=group, instance_ids=instance_ids,
                 exact_count=exact_count, networks=networks,
                 count_offset=count_offset, auto_increment=auto_increment,
                 extra_create_args=extra_create_args, user_data=user_data,
                 config_drive=config_drive)


# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.rax import *

# invoke the module
main()
