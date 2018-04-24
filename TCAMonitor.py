#!/usr/bin/env python
# Copyright (c) 2016 Arista Networks, Inc.  All rights reserved.
# Arista Networks, Inc. Confidential and Proprietary.

"""
   DESCRIPTION
      The TCAM Monitoring SDK agent monitors for state changes in hardware tables and sends
      number of free, used, committed, and maximum table entries to a MySQL table every time
      there is a new entry added to a TCAM table.
   INSTALLATION
      In order to install this extension:
         - copy 'TCAMonitor' to /mnt/flash
         - configure Sysdb Mount profile by typing the following script from bash
               bin=/mnt/flash/TCAMonitor
               [ ${bin%.*} == $bin ] || echo "Error: remove dots from binary name"
               name=$(basename $bin)
               dest=/usr/lib/SysdbMountProfiles/$name
               source="/usr/lib/SysdbMountProfiles/EosSdkAll"
               cat $source | sed "1s/agentName[ ]*:.*/agentName:${name}-%sliceId/" > /tmp/tmp_$name
               delta=$(cmp /tmp/tmp_$name $source)
               if [ "$?" = "0" ]; then
                 echo "Error: something is wrong"
               else
                 sudo mv /tmp/tmp_$name $dest
               fi
      TCAMonitor can then be started using the following method:
      - Configure daemon
         (config)# daemon TCAMonitor
         (config)# exec /mnt/flash/TCAMonitor
         (config)# no shut
         (config)# exit
       - Monitor the values currently registered with the agent
         # show daemon TCAMonitor

   COMPATIBILITY
      Version 1.0 has been developed and tested against 4.20.5F-REV-0-1-HW and
      is using the EOS SDK v2.2.0. Hence, it should maintain
      backward compatibility with future EOS releases.
  LIMITATIONS
      None known.
"""

import eossdk
import sys
import MySQLdb

class TCAMonitor(eossdk.HardwareTableHandler, eossdk.AgentHandler):
   def __init__(self, hwTableMgr, agentMgr):
      '''Class TCAMonitor initilization and construction
       Args:
           self: init TCAMonitor Class self object
           hwTableMgr: Hardware Table Manager called from SDK to manage hardware tables registered to sysdb
           agentMgr: Agent Manager called from SDK to manage the agent lifecycle
       Returns: None
       '''
      eossdk.AgentHandler.__init__(self, agentMgr)
      eossdk.HardwareTableHandler.__init__(self, hwTableMgr)
      self.tracer = eossdk.Tracer("EosSdkTCAMonitor")
      self.hwTableMgr_ = hwTableMgr
      self.agentMgr_ = agentMgr
      self.tracer.trace0("Constructed")

   def on_initialized(self):
      """ Callback provided by AgentHandler when all state is synchronized
      Args:
          self: init TCAMonitor Class self object
      """
      self.tracer.trace0("We are initialized!")
      self.watch_all_hardware_tables(True)
      self.tracer.trace0("Started watch of hardware tables")
      for tableKey in self.hwTableMgr_.hardware_table_iter():
          usage = self.hwTableMgr_.usage(tableKey)
          free_key = tableKey.table_name()+"-"+tableKey.feature()+": Free Entries"
          used_key = tableKey.table_name()+"-"+tableKey.feature()+": Used Entries"
          committed_key = tableKey.table_name()+"-"+tableKey.feature()+": Committed Entries"
          max_key = tableKey.table_name()+"-"+tableKey.feature()+": Maximum Entries"
          self.agentMgr_.status_set(free_key , str(usage.free_entries()))
          self.agentMgr_.status_set(used_key , str(usage.used_entries()))
          self.agentMgr_.status_set(committed_key , str(usage.committed_entries()))
          self.agentMgr_.status_set(max_key , str(self.hwTableMgr_.max_entries(tableKey)))

   def on_hardware_table_entry_set(self, tableKey, tableEntry):
      """ Callback provided by AgentHandler when all state is synchronized
      Args:
          self: init TCAMonitor Class self object
          tableKey: The unique identifier for a hardware table.
          tableEntry: The hardware table entry for a given table key. COntains usage and max_entry statistics for that table.
      """
      threshold = 21000
      usage = tableEntry.usage()
      free_key = tableKey.table_name() + "-" + tableKey.feature() + ": Free Entries"
      used_key = tableKey.table_name() + "-" + tableKey.feature() + ": Used Entries"
      committed_key = tableKey.table_name() + "-" + tableKey.feature() + ": Committed Entries"
      max_key = tableKey.table_name() + "-" + tableKey.feature() + ": Maximum Entries"
      self.agentMgr_.status_set(free_key, str(usage.free_entries()))
      self.agentMgr_.status_set(used_key, str(usage.used_entries()))
      self.agentMgr_.status_set(committed_key, str(usage.committed_entries()))
      self.agentMgr_.status_set(max_key, str(tableEntry.max_entries()))
      if (usage.used_entries()+usage.committed_entries() > threshold):

          conn = MySQLdb.connect(host="localhost",user="root",passwd="newpassword",db="engy1")
          x = conn.cursor()
          try:
            x.execute("""INSERT INTO TCAM_Table VALUES (%s,%s,%i,%i,%i,%i)""", (tableKey.table_name(), tableKey.feature(),
                                                                               usage.free_entries(),usage.used_entries(),
                                                                               usage.committed_entries(),tableEntry.max_entries()))
            conn.commit()
          except:
            conn.rollback()
          conn.close()

if __name__ == "__main__":
   sdk = eossdk.Sdk()
   _ = TCAMonitor(sdk.get_hardware_table_mgr(), sdk.get_agent_mgr())
   sdk.main_loop(sys.argv)

