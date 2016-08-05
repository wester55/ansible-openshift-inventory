#!/usr/bin/env python
import ConfigParser, argparse, os, sys, subprocess, json

class OcInventory(object):

    def __init__(self):

        self.data_to_print = {}
        self.parse_cli_args()
        self.read_settings()
        self.login()

        if self.args.host:
            self.data_to_print = self.get_host_info(self.args.host)
        elif self.args.list:
            self.data_to_print = self.get_inventory()

        print(str(self.data_to_print).replace('\'', '"'))

    def _empty_inventory(self):
        return {"pods":{"hosts":[],"vars":{}},"_meta":{"hostvars":{}}}

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

    def get_host_info(self,instance):

        result = {}
        try:
            out = json.loads(subprocess.check_output([self.oc_exe_path, 'export', 'pod', instance, '--output=json'], shell=self.set_shell()))
            result["ansible_host"] = str(out['spec']['nodeName'])
            return result
        except:
            return result

    def get_inventory(self):

        result = self._empty_inventory()
        cont = subprocess.check_output([self.oc_exe_path, 'get', 'pods'], shell=self.set_shell())
        for line in cont.split('\n'):
            if line is not '':
                if not line.startswith("NAME"):
                    instance = line.split()[0]
                    if not instance.endswith("build"):
                        out = json.loads(subprocess.check_output([self.oc_exe_path, 'export', 'pod', instance, '--output=json'], shell=self.set_shell()))
                        result["_meta"]["hostvars"][instance] = {"ansible_ssh_host":str(out['spec']['nodeName'])}
                        result["pods"]["hosts"].append(str(instance))
        return result

    def login(self):
        try:
            with open(os.devnull, 'w') as devnull:
                result = str(subprocess.check_output([self.oc_exe_path,'whoami'],shell=self.set_shell(),stderr=devnull)).rstrip('\n')
            if result == self.oc_user:
                return True
        except:
            pass
        with open(os.devnull, 'w') as devnull:
            result = subprocess.check_output([self.oc_exe_path,'login',self.oc_master + ":" + self.oc_master_port,'-u',self.oc_user,'-p',self.oc_password,'--insecure-skip-tls-verify=true'],shell=self.set_shell(),stderr=devnull)
        if not str(result).startswith("Login successful."):
            print("Unable to login to Openshift master")
            print(result)
            exit(1)

    def set_shell(self):
        if sys.platform == "win32":
            return True
        else:
            return False

# Run the script
OcInventory()