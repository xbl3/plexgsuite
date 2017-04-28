#!/usr/local/bin/python3

# Author: Jake Tame
# Email: jaketame@me.com
# Desc: Disk monitor that checks to see that disk usage is above a set threshold and upload to GCD via RCLONE
# Desc: To be run via service

import json, shutil, logging, time, subprocess, os
from shutil import disk_usage
from datetime import datetime

# Load configuration file and pull in variables
CONFIG = json.loads(open('config.cfg').read())
RLCONE = CONFIG['plexgcd']['rclone']
RCLONE_TRANSFERs = CONFIG['plexgcd']['rclone_transfer']
NZBGET = CONFIG ['plexgcd']['nzbget']
DISK_PATH = CONFIG['plexgcd']['disk_check_path']
LOG_PATH = CONFIG['plexgcd']['log_path']
LOG_FILE = LOG_PATH + 'diskmonitor.log'
#threshold = int(config['plexgcd']['disk_threshold'])
THRESHOLD = int("50")
START_TIME = CONFIG['plexgcd']['start_time']
END_TIME = CONFIG['plexgcd']['end_time']
LOCAL_DIR = CONFIG['plexgcd']['local_dir']
REMOTE_DIR = CONFIG['plexgcd']['remote_dir']
REMOTE_NAME = CONFIG['plexgcd']['remote_name']
# Set logging and default to info
logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,filename=LOG_FILE,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def logging_call(popenargs, **kwargs):
    process = subprocess.Popen(popenargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def check_output():
           while True:
                output = process.stdout.readline().decode()
                if output:
                    logger.log(logging.INFO, output)
                else:
                    break

    # keep checking stdout/stderr until the child exits
    while process.poll() is None:
        check_output()

def check_usage():
    # Return percentage of disk usage of mountpoint in config file
    (total, used, free) = disk_usage(DISK_PATH)
    logging.debug("Path is %s " % DISK_PATH )
    logging.debug("Raw values are total %s used %s free %s" % (total, used, free) )
    perc = (float(used) / total) * 100
    logging.debug("Calculation used %s / %s = %s%% " %(used, total, perc) )
    return int(perc)

def check_time():
    # Check to see if start time is greater than current time but less than the end time for upload window
    if START_TIME >= TIME_NOW < END_TIME:
        return True
    else:
        return False

def pause_nzbget():
    command = ([NZBGET, '-P'])
    result = subprocess.Popen(command)
    result.communicate()

def resume_nzbget():
    command = ([NZBGET, '-U'])
    result = subprocess.Popen(command)
    result.communicate()

def rclone_upload():
# For each directory under your LOCAL_DIR we are going to upload, will exclude hidden folders
    for dir in os.listdir(LOCAL_DIR):
        if not os.path.isdir(os.path.join(LOCAL_DIR, dir)):
            continue
        logging.info('Uploading directory : ' + dir)
        logging_call([RCLONE, 'move', '--dry-run', '--transfers', RCLONE_TRANSFERS, '--drive-chunk-size=16M', '--exclude', 'filepart', LOCAL_DIR + dir + '/', REMOTE_NAME  + dir + '/'])

def main():
    logging.info("Disk monitor started")
while True:
    # Get current time
    TIME_NOW = datetime.now().strftime('%H:%M')
    # Using the function check_usage to return current used percentage of mount
    USED_PERC = check_usage()
    logging.debug("Showing current used_perc = %s " %(USED_PERC) )

    # Checking to make sure used space is over the threshold otherwise sleep for 60 seconds to check again
    if USED_PERC >= THRESHOLD:
        logging.warning("Path %s currently at %s%% used space" % (DISK_PATH, USED_PERC) )
        logging.info("Checking time to ensure within allowed upload hours")

        # Checking that the check_time function returns true meaning we are within our window, crack on uploading
        if check_time() == True:
            logging.debug("Time is now %s within window of start time %s and end time %s" % (TIME_NOW, START_TIME, END_TIME) )
            logging.info("Time %s is within schedule, uploading" % (TIME_NOW) )
            # Pause NZBGet to get best upload speed
#            logging.info("Pausing NZBGet for best upload")
    #        pause_nzbget()
            # Upload via RCLONE
            rclone_upload()
            # Resume NZBGet
#            logging.info("Resuming NZBGet")
#            resume_nzbget()

        else:
            # Comparing the start window and the current time to pause all downloading and script until it is within the window
            START = datetime.strptime(START_TIME, '%H:%M')
            NOW = datetime.strptime(TIME_NOW, '%H:%M')
            SLEEP_TIME = START - NOW
            logging.info("Path is at %s%% / %s%% but outside timewindow, pausing downloads and script until %s" % (USED_PERC, THRESHOLD, START_TIME) )
            logging.debug("Sleeping time is %s and %s in seconds" % (SLEEP_TIME, SLEEP_TIME.seconds) )
            # Pause NZBGet to avoid disk filling up and leave paused to get best upload speed, will resume post upload
            pause_nzbget()
            # Sleep time
            time.sleep(SLEEP_TIME.seconds)

    else:
        # Looping until used percentage is above threshold
        logging.info("Path %s currently at %s%% free" % (DISK_PATH, USED_PERC) )
        logging.debug("Sleeping for 60 seconds")
        # Sleep time loop for 60 seconds
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Stopping...")
