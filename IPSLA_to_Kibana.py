#!/usr/bin/python

"""
   DESCRIPTION
      IPSLA Metrics logging tool allows for metrics to be checked against a threshold and
      logged to Kibana if above configured levels.
   INSTALLATION
      In order to install this extension:
         - copy 'IPSLA_to_Kibana.py' to /mnt/flash and rename to 'IPSLA' (remove extension)
         - enable the Command API interface:
               management api http-commands
                  no shutdown
         - configure hosts to be monitored on the switch
                monitor connectivity
                    host google-dns
                        description
                            Monitoring link to Google DNS
                        ip 8.8.8.8
                        url http://www.google.com
         - change SWITCH_IP, USERNAME and PASSWORD at the top of the
           script to the ones appropriate for your installation. If
           running locally, use '127.0.0.1' for the IP.
      IPSLA can then be started using any of the following methods:
      1 - Execute directly from bash (from the switch, or a remote
          switch/server running Python):
         (bash)# sudo python /mnt/flash/IPSLA
      2 - Run at switch boot time by adding the following startup
          config:
         (config)# event-handler IPSLA
         (config)# trigger on-boot
         (config)# action bash sudo python /mnt/flash/IPSLA
         (config)# asynchronous
         (config)# exit
         Note that in order for this to work, you will also have to
         enable the Command API interface in the startup-config (see
         above).
   COMPATIBILITY
      Version 1.0 has been developed and tested against EOS-4.20.0FX-Virtual-Router-EFT and
      is using the Command API interface. Hence, it should maintain
      backward compatibility with future EOS releases.
  LIMITATIONS
      None known.
  VERSION
  IPSLA.py v1.1
    - ability to set thresholds for metrics as well as timeout between metric colletion
    - eAPI call to get IPSLA metrics from vEOSRouter directly
    - check metrics against thresholds and send to syslog (to be picked up by Kibana)
  IPSLA.py v1.2
    - specify source in log
    - send logs to logstash on UDP port 514/5514 on logstash server (push mechanism)
    - change sleep window to 60 seconds
"""
from jsonrpclib import Server, ProtocolError, loads, history
import sys,logging,time, socket

#define switch parameters
TRANSPORT = "https"
SWITCH_IP = "127.0.0.1"
USERNAME = "arista"
PASSWORD = "arista"

#define thresholds
JITTER_THRESHOLD = 0
PACKET_LOSS_THRESHOLD = 0
HTTP_RT_THRESHOLD = 0
LATENCY_THRESHOLD = 0

#disable SSL verification on macOS
#ssl._create_default_https_context = ssl._create_unverified_context

#define loggers
logfile_DEBUG = "/var/log/IPSLA_debug.log"
logfile_WARNING = "/var/log/IPSLA_warn.log"
LOGSTASH_HOST = "192.168.100.100" #change appropriately
LOGSTASH_PORT = 5514 #change appropriately

def setup_logger(logger_name, log_file, level):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fileHandler = logging.FileHandler(log_file)
    fileHandler.setFormatter(formatter)
    l.setLevel(level)
    l.addHandler(fileHandler)

def log(msg):
    '''Log message to stdout and logging file
    Args:
        msg: string to print to syslog debug file
    Returns: None
    '''
    logger1 = logging.getLogger("log1")
    logger1.debug(msg)

def setup_eapi_connection():
    '''Sets up eAPI connection
        Args: None
        Returns:
            Server(url) - eAPI connection
    '''
    url = "%s://%s:%s@%s/command-api" % (TRANSPORT, USERNAME, PASSWORD, SWITCH_IP)
    log("Setting up connection to %s" % url)
    return Server(url)

def run_cmds(eapi, commands, format="json"):
    '''Log message to stdout and logging file
        Args:
            eapi: api connection to switch
            commands: commands to run
            format: format of response from switch, default is json
        Returns: None
    '''
    log("Running command: %s" % commands)
    try:
        result = eapi.runCmds(1, commands, format)
    except ProtocolError:
        errorResponse = loads(history.response)
        log("Failed to run cmd:%s. %s" %
            (commands, errorResponse["error"]["data"][0]["errors"][-1]))
        sys.exit(1)
    return result

def checkThreshold(httpRT, jitter, latency, packetloss):
    '''Check values from switch against thresholds
        Args:
            httpRT: HTTP Round Trip Time
            jitter: jitter value
            latency: latency value
            packetloss: packetloss value
        Returns: True if any one of the values are above threshold, else false
    '''
    if httpRT > HTTP_RT_THRESHOLD or jitter > JITTER_THRESHOLD or latency > LATENCY_THRESHOLD or packetloss > PACKET_LOSS_THRESHOLD:
        return True
    else:
        return False

def sendToSyslog(src, dest, ip, httpRT, jitter, latency, packetloss):
    '''Send values above threshold to syslog warning file
        Args:
            src: source of IPSLA ping
            dest: destination of IPSLA ping
            httpRT: HTTP Round Trip Time
            jitter: jitter value
            latency: latency value
            packetloss: packetloss value
        Returns: None
    '''
    # step 1 - write to local log file
    logger2 = logging.getLogger("log2")
    log_str = "%s %s %s %f %f %f %f" % (src, dest, ip, httpRT, jitter, latency, packetloss)
    logger2.warning(log_str)
    # step 2 - send to logstash server at port 5514
    udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (LOGSTASH_HOST, LOGSTASH_PORT)
    udpsock.connect(server_address)
    udpmsg = "WARNING " + log_str
    udpsock.sendall(udpmsg)
    udpsock.close()

def main():
    # step 1 - setup eAPI connections
    eapi = setup_eapi_connection()
    # step 2 - setup loggers
    setup_logger('log1', logfile_DEBUG, logging.DEBUG)
    setup_logger('log2', logfile_WARNING, logging.WARNING)
    #step 3 - get router hostname to log as source of metric collection
    runCommands = [
        "show hostname"
    ]
    source = run_cmds(eapi, runCommands, "json")[0]["hostname"]
    # step 4 - collect all monitor metrics
    runCommands = [
        "show monitor connectivity"
    ]
    while True:
        hosts_list = run_cmds(eapi, runCommands, "json")[0]["hosts"]
        for host in hosts_list:
            check = checkThreshold(hosts_list[host]["httpResponseTime"], hosts_list[host]["jitter"],
                                   hosts_list[host]["latency"], hosts_list[host]["packetLoss"])
            if check is True: #can add an else to direct values below threshold to another destination (example nagios)
                sendToSyslog(source, hosts_list[host]["hostName"], hosts_list[host]["ipAddr"],
                             hosts_list[host]["httpResponseTime"], hosts_list[host]["jitter"],
                             hosts_list[host]["latency"], hosts_list[host]["packetLoss"])
        time.sleep(60) #can change this value as per requirement

if __name__=="__main__":
        main()
