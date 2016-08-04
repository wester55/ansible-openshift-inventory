#!/usr/bin/env python
import ConfigParser, argparse, os, sys, subprocess, json

class OcInventory(object):

    def _empty_inventory(self):
        return {"_meta": {"hostvars": {}}}

    def read_settings(self):

        config = ConfigParser.RawConfigParser()
        config.read('openshift.ini')
        try:
            self.oc_master = str(config.get('Global', 'oc_master')).rstrip('\',\"').lstrip('\',\"')
            self.oc_master_port = str(config.get('Global', 'oc_master_port')).rstrip('\',\"').lstrip('\',\"')
            self.oc_user = str(config.get('Global', 'oc_user')).rstrip('\',\"').lstrip('\',\"')
            self.oc_password = str(config.get('Global', 'oc_password')).rstrip('\',\"').lstrip('\',\"')
            self.oc_exe_path = str(config.get('Global', 'oc_exe_path')).rstrip('\',\"').lstrip('\',\"')
        except:
            self.oc_master = os.environ.get('OC_MASTER',None)
            self.oc_master_port = os.environ.get('OC_MASTER_PORT',None)
            self.oc_user = os.environ.get('OC_USER',None)
            self.oc_password = os.environ.get('OC_PASSWORD',None)
            self.oc_exe_path = os.environ.get('OC_EXE_PATH',None)
            if not (self.oc_master and self.oc_master_port and self.oc_user and self.oc_password):
                print("Not all required variables initialized.")
                exit(1)
            if not self.oc_exe_path:
                try:
                    self.oc_exe_path = str(subprocess.check_output('which oc', shell=True)).rstrip("\n")
                except:
                    sys.exit('ERROR: executable oc not found')

    def parse_cli_args(self):
        ''' Command line argument processing '''

        parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on Openshift')
        parser.add_argument('--list', action='store_true', default=True,
                            help='List instances (default: True)')
        parser.add_argument('--host', action='store',
                            help='Get all the variables about a specific instance')
        self.args = parser.parse_args()

    def __init__(self):

        self.inventory = self._empty_inventory()
        self.data_to_print = {}
        self.parse_cli_args()
        self.read_settings()
        self.login()

        if self.args.host:
            self.data_to_print = self.get_host_info(self.args.host)
        elif self.args.list:
            self.data_to_print = self.get_inventory()

        print(self.data_to_print)

    def get_host_info(self,instance):

        result = {}
        try:
            out = json.loads(subprocess.check_output([self.oc_exe_path, 'export', 'pod', instance, '--output=json'], shell=True))
            result["ansible_host"] = str(out['spec']['nodeName'])
            return result
        except:
            return result

    def get_inventory(self):

        result = self._empty_inventory()
        cont = subprocess.check_output([self.oc_exe_path, 'get', 'pods'], shell=True)
        for line in cont.split('\n'):
            if line is not '':
                if not line.startswith("NAME"):
                    instance = line.split()[0]
                    if not instance.endswith("build"):
                        out = json.loads(subprocess.check_output([self.oc_exe_path, 'export', 'pod', instance, '--output=json'], shell=True))
                        result["_meta"]["hostvars"][instance] = {"ansible_host":str(out['spec']['nodeName'])}
        return result

    def login(self):
        result = subprocess.check_output([self.oc_exe_path,'login',self.oc_master + ":" + self.oc_master_port,'-u',self.oc_user,'-p',self.oc_password],shell=True)
        if not str(result).startswith("Login successful."):
            print("Unable to login to Openshift master")
            exit(1)

    def get_auth_error_message(self):
        ''' create an informative error message if there is an issue authenticating'''
        errors = ["Authentication error retrieving ec2 inventory."]
        if None in [os.environ.get('AWS_ACCESS_KEY_ID'), os.environ.get('AWS_SECRET_ACCESS_KEY')]:
            errors.append(' - No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY environment vars found')
        else:
            errors.append(
                ' - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment vars found but may not be correct')

        boto_paths = ['/etc/boto.cfg', '~/.boto', '~/.aws/credentials']
        boto_config_found = list(p for p in boto_paths if os.path.isfile(os.path.expanduser(p)))
        if len(boto_config_found) > 0:
            errors.append(" - Boto configs found at '%s', but the credentials contained may not be correct" % ', '.join(
                boto_config_found))
        else:
            errors.append(" - No Boto config found at any expected location '%s'" % ', '.join(boto_paths))

        return '\n'.join(errors)

    def fail_with_error(self, err_msg, err_operation=None):
        '''log an error to std err for ansible-playbook to consume and exit'''
        if err_operation:
            err_msg = 'ERROR: "{err_msg}", while: {err_operation}'.format(
                err_msg=err_msg, err_operation=err_operation)
        sys.stderr.write(err_msg)
        sys.exit(1)


# Run the script
OcInventory()