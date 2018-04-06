#!/usr/bin/python

"""
   DESCRIPTION
      ACL Editor with CRUD functionality to demonstrate eAPI scripting around ACLs. 
   INSTALLATION
      In order to install this extension:
         - copy 'crud_acl_editor.py' to /mnt/flash and rename to 'crud_acl_editor' (remove extension)
         - enable the Command API interface:
               management api http-commands
                  no shutdown
         - change SWITCH_IP, USERNAME and PASSWORD at the top of the
           script to the ones appropriate for your installation. If
           running locally, use '127.0.0.1' for the IP.
      crud_acl_editor can then be started using the following methods
      Execute directly from bash (from the switch, or a remote
          switch/server running Python):
         (bash)# sudo python /mnt/flash/crud_acl_editor
   COMPATIBILITY
      Version 1.0 has been developed and tested against EOS-lab-4.20.1FX and
      is using the Command API interface. Hence, it should maintain
      backward compatibility with future EOS releases.
  LIMITATIONS
      None known.
  VERSION
  crud_acl_editor.py v1.0
    - Perform non-trivial CRUD operations on ACLs 
"""

from jsonrpclib import Server
import ssl, pprint

#define switch parameters
switches = ["192.168.X.X"] # able to define a list of switches to connect to
username = "arista"
password = "arista"
#disable SSL verification
ssl._create_default_https_context = ssl._create_unverified_context

def viewACL(ipaddr):
    # show all acls
    commandsToRun = [
        "enable",
        "show ip access-lists"
    ];
    urlString = "https://{}:{}@{}/command-api".format(username, password, ipaddr)  # 1
    switchReq = Server(urlString)  # 2
    response = switchReq.runCmds(1, commandsToRun)  # 3
    for acl in response[1]['aclList']:
        if acl["readonly"] == False:
            pprint.pprint(acl)

def addACL(ipaddr, name,rules):
    # add new acl
    commandsToRun = [
        "enable",
        "configure"
    ];
    aclname = "ip access-list "+name
    commandsToRun+=[aclname]
    commandsToRun+=rules
    urlString = "https://{}:{}@{}/command-api".format(username, password, ipaddr)  # 1
    switchReq = Server(urlString)  # 2
    switchReq.runCmds(1, commandsToRun)  # 3

def editACL(ipaddr, name):
    # edit acl
    commandsToRun = [
        "enable",
        "show ip access-lists"
    ];
    urlString = "https://{}:{}@{}/command-api".format(username, password, ipaddr)  # 1
    switchReq = Server(urlString)  # 2
    response = switchReq.runCmds(1, commandsToRun)  # 3
    found = False
    for acl in response[1]['aclList']:
        if acl["name"] == name:
            found = True
            while True:
                editMenu = "\n\n1. View all Rules\n2. Edit existing rule\n3. Add new rule\n4. Delete rule\n5. Back to Main Menu\n"
                print(editMenu)
                choice = input("Enter Menu Number to proceed: ")
                if choice =="1":
                    print("Existing rules: \n")
                    commandsToRun0 = [
                        "enable",
                        "show ip access-lists"
                    ];
                    urlString = "https://{}:{}@{}/command-api".format(username, password, ipaddr)  # 1
                    switchReq = Server(urlString)  # 2
                    response = switchReq.runCmds(1, commandsToRun0)  # 3
                    for acl1 in response[1]['aclList']:
                        if acl1["name"] == name:
                            for sequence1 in acl1["sequence"]:
                                print(sequence1["sequenceNumber"], ": ", sequence1["text"])
                elif choice == "2":
                    toEdit = input("Enter rule sequence to edit")
                    newRule = input("Enter new rule sequence")
                    commandsToRun1 = [
                        "enable",
                        "configure"
                    ];
                    aclname = "ip access-list " + name
                    remrule = "no "+toEdit
                    commandsToRun1+=[aclname,remrule,newRule]
                    urlString = "https://{}:{}@{}/command-api".format(username, password, ipaddr)  # 1
                    switchReq = Server(urlString)  # 2
                    response = switchReq.runCmds(1, commandsToRun1)  # 3
                    print("Edited ACL: ", name)
                elif choice == "3":
                    rulestr = input("Enter new ACL rules separated by commas")
                    rules = rulestr.split(",")
                    addACL(ipaddr, name, rules)
                    print("Edited ACL: ", name)
                elif choice == "4":
                    toDel = input("Enter rule sequence to delete")
                    commandsToRun2 = [
                        "enable",
                        "configure"
                    ];
                    aclname = "ip access-list " + name
                    delrule = "no " + toDel
                    commandsToRun2 += [aclname, delrule]
                    urlString = "https://{}:{}@{}/command-api".format(username, password, ipaddr)  # 1
                    switchReq = Server(urlString)  # 2
                    response = switchReq.runCmds(1, commandsToRun2)  # 3
                    print("Edited ACL: ", name, " Deleted rule: ", toDel)
                elif choice == "5":
                    print("--- Back to Main Menu ---")
                    break
                else:
                    print("Invalid Input, try again")
    if not found:
        print("No such ACL exists")

def deleteACL(ipaddr,name):
    #remove acl
    commandsToRun = [
       "enable",
       "configure"
    ];
    aclname = "no ip access-list " + name
    commandsToRun += [aclname]
    urlString = "https://{}:{}@{}/command-api".format(username, password, ipaddr)  # 1
    switchReq = Server(urlString)  # 2
    response = switchReq.runCmds(1, commandsToRun)  # 3
    print("Removed ACL: ", name)
    pprint.pprint(response)  # 4

if __name__=="__main__":
    print("--- ACL Editor ---")
    ipaddr = input("Enter IP of switch: ")
    menu = "Menu: \n1. View ACLs\n2. Add new ACLs\n3. Edit ACLs\n4. Delete ACL\n5. Exit\n"
    if ipaddr in switches:
        while True:
            print(menu)
            choice = input("Enter Menu Number to proceed: ")
            if choice=="1":
                viewACL(ipaddr)
            elif choice=="2":
                name = input("Enter name of new ACL: \n")
                rulestr = input("Enter new ACL rules separated by commas")
                rules=rulestr.split(",")
                addACL(ipaddr, name, rules)
            elif choice=="3":
                name = input("Enter name of ACL to edit: ")
                editACL(ipaddr,name)
            elif choice =="4":
                name = input("Enter name of ACL to delete: ")
                deleteACL(ipaddr, name)
            elif choice=="5":
                print("--- Exiting ACL Editor ---")
                break
            else:
                print("Invalid Input, try again")
    else:
        print("Invalid IP entered")










