#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author: Hernan Collazo
# Email: hernan.collazo@gmail.com
#

import ConfigParser
import paramiko
import sys
import time
import re
# from paramiko_expect import SSHClientInteraction
import datetime
import os

# Configuration file (fullpath)
configFile = "/opt/nsbt/nsbt.cfg"

# Config information
mycfg = ConfigParser.ConfigParser()
mycfg.read(configFile)
debug = mycfg.get("default", "debug")
switches_list = mycfg.get("default", "switches_inventory")
bkpdir = mycfg.get("default", "backup_dir")

errors_counter = 0

def banner():
    print("\n")
    print("*" * 42)
    print("Network Switches Backup Tool")
    print("*" * 42)
    print("\n")
    return


def msg(devicename, message):
    print("[%s] - %s" % (devicename, message))
    return


def escape_ansi(line):
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)


def file_size(file_path):
    if os.path.isfile(file_path):
        file_info = os.stat(file_path)
        return file_info.st_size


def check_bkp(hostname, bkpfile, bkp_type):
    bkpsize = file_size(bkpfile)
    msg(hostname, 'Checking Backup...')
    if bkpsize > 900:
        msg(hostname, '\tBackup Size: OK (' + str(bkpsize) + ' bytes).')
        if bkp_type.lower() == "dell":
            if 'Dell' in open(bkpfile).read():
                msg(hostname,
                    '\tBackup Content: OK (Dell string found)')
                bkp_status = 0
            elif 'PowerConnect' in open(bkpfile).read():
                msg(hostname,
                    '\tBackup Content: OK (PowerConnect string found)')
                bkp_status = 0
            elif 'username supportassist' in open(bkpfile).read():
                msg(hostname,
                    '\tBackup Content: OK (PowerConnect string found)')
                bkp_status = 0
            else:
                msg(hostname,
                    '\tBackup Content: ERROR (Dell string NOT found)')
                bkp_status = 1
        if bkp_type.lower() == "hp":
            if 'HEWLETT-PACKARD' in open(bkpfile).read():
                msg(hostname, '\tBackup Content: OK (HP string found)')
                bkp_status = 0
            else:
                msg(hostname, '\tBackup Content: ERROR (HP string NOT found)')
                bkp_status = 1
    else:
        msg(hostname, '\tBackup Size: ERROR (' + str(bkpsize) + ' bytes).')
        bkp_status = 1
    return bkp_status


banner()

try:
    with open(switches_list) as file:
        pass
except IOError as e:
    print("""\nERROR: Unable to open switches_inventory file (please
          check your config file!).\n""")
    sys.exit(1)

print("Using %s as inventory file...\n" % switches_list)
with open(switches_list) as fp:
    line = fp.readline()
    while line:
        connect_error = False
        if not line.startswith("#"):
            line = line.rstrip("\n")
            switch = line.split(",")
            hostname = switch[0]
            description = switch[1]
            ip = switch[2]
            port = switch[3]
            login = switch[4]
            password = switch[5]
            enable = switch[6]
            swtype = switch[7]
            msg(hostname, "Backup process started.")
            msg(hostname, "Description: " + description)
            # if debug and debug == 'True':
            #     print("-" * 50)
            #     print(hostname)
            #     print(description)
            #     print(ip)
            #     print(port)
            #     print(login)
            #     print(password)
            #     print(enable)
            #     print(swtype)
            #     print("-" * 50)
            msg(hostname, "Switch type: " + swtype.upper())
            if swtype.lower() == "dell":
                msg(hostname, "Starting SSH session...")
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    client.connect(ip, username=login,
                                   password=password, port=port, timeout=30)
                except Exception as e:
                    connect_error = True
                if connect_error is False:
                    msg(hostname, "DELL - SSH session OK.")
                    chan = client.invoke_shell()
                    msg(hostname, "Interactive session started.")
                    time.sleep(1)
                    chan.send('enable\n')
                    chan.send(enable + '\n')
                    time.sleep(1)
                    chan.send('terminal length 0\n')
                    time.sleep(1)
                    chan.send('show running-config\n')
                    time.sleep(10)
                    output = chan.recv(99999)
                    cdate = datetime.datetime.today().strftime('%Y%m%d-%H%M%S')
                    bkpfile = bkpdir + "/" + hostname + "." + cdate + ".dump"
                    msg(hostname, "Backup created at " + bkpfile + ".")
                    bkp = open(bkpfile, "w")
                    bkp.write(output)
                    bkp.close()
                    client.close()
                    bkp_status = check_bkp(hostname, bkpfile, swtype.lower())
                else:
                    msg(hostname, "Error trying to establish ssh connection.")
                    bkp_status = 1
            elif swtype.lower() == "hp":
                msg(hostname, "Starting SSH session...")
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    client.connect(ip, username=login, password=password,
                                   port=port, timeout=30)
                except Exception as e:
                    connect_error = True
                if connect_error is False:
                    msg(hostname, "HP - SSH session OK.")
                    chan = client.invoke_shell()
                    msg(hostname, "Interactive session started.")
                    chan.send('enable\n')
                    chan.send(enable + '\n')
                    chan.send('no page\n')
                    chan.send('terminal width 1920\n')
                    chan.send('configure\n')
                    chan.send('console local-terminal vt100\n')
                    chan.send('show running-config\n')
                    time.sleep(10)
                    output = chan.recv(99999)
                    output_final = escape_ansi(output)
                    bkpfile = bkpdir + "/" + hostname + "." + cdate + ".dump"
                    msg(hostname, "Backup created at " + bkpfile + ".")
                    bkp = open(bkpfile, "w")
                    bkp.write(output_final.replace('\r', ''))
                    bkp.close()
                    client.close()
                    bkp_status = check_bkp(hostname, bkpfile, swtype.lower())
                else:
                    msg(hostname, "Error trying to establish ssh connection.")
                    bkp_status = 1
            else:
                msg(hostname, 'ERROR - Unknown switch type.')
                bkp_status = 1
            if bkp_status == 1:
                msg(hostname, 'ERROR - Backup file corrupted.')
                errors_counter += 1
            if bkp_status == 0:
                msg(hostname, 'Backup file is OK.')
            print("\n")
        line = fp.readline()

print('\nGlobal Backup Status: %s errors.\n' % errors_counter)
if errors_counter == 0:
    sys.exit(0)
else:
    sys.exit(1)

