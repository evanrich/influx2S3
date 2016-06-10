#!/usr/bin/env python

'''
Description:  Script to backup influxdb and save to s3
Dependency:   Boto, installed via apt-get install python-boto
Author:  Evan Richardson
Date:  160527
Version: 1.0
'''

import argparse
import boto3
import botocore
import os
import glob
import tarfile
import time
import sys
import shutil
import getopt
from subprocess import call
from dateutil import tz

#some variables we'll use
backup_path='/var/tmp/restore/'
backuptime = str(int(time.time()))
influx_data_dir = "/var/lib/influxdb/data"
influx_meta_dir = "/var/lib/influxdb/meta"
backup_bucket   = ''
access_key_id   = ''
secret_key      = ''
upload_folder   = 'influxdb'
client=boto3.client(
    's3',
    aws_access_key_id = access_key_id,
    aws_secret_access_key = secret_key,
)

def backup( databaseName ):

    #backup
    call(["influxd", "backup", "-database", databaseName, backup_path])

    #create tar file
    #time = str(int(time.time()))

    tar = tarfile.open(backup_path + databaseName + '_' + backuptime + '.tar.gz', "w:gz")
    for name in glob.glob(backup_path + "*.00"):
        #print os.path.basename(name)
        tar.add(name, arcname=os.path.basename(name))
    tar.close()

    #upload backup
    archive_path = max(glob.iglob(backup_path + '*.gz'), key=os.path.getctime)
    archive_name = os.path.basename(archive_path)
    client.upload_file(archive_path, backup_bucket, upload_folder + '/' + archive_name)

    #cleanup
    files = glob.glob(backup_path + '*')
    for f in files:
        os.remove(f)
    return;

def restore( backupToRestore, downloadPath, databaseName ):
    print "Downloading restore point: %s" % backupToRestore

    if not os.path.exists(downloadPath + "/" + databaseName):
        os.makedirs(downloadPath + "/" + databaseName)

    client.download_file(backup_bucket, backupToRestore, downloadPath + '/' + 'InfluxRestore.tar.gz')

    #untar backup
    archive_path = max(glob.iglob(downloadPath + "/" + '*.gz'), key=os.path.getctime)
    archive_name = os.path.basename(archive_path)

    print backup_path
    print "Extracting Archive..."
    os.chdir(downloadPath)
    tar = tarfile.open('InfluxRestore.tar.gz')
    tar.extractall()
    tar.close()

    #cleanup
    files = glob.glob(backup_path + '*.gz')
    for f in files:
        os.remove(f)


    #restore
    print "Stopping influxD process"
    call(["service", "influxdb", "stop"])
    print "Restoring backup from %s" % backup_path
    print "Restoring metadata..."
    call(["influxd", "restore", "-metadir", influx_meta_dir, downloadPath])
    print "Restoring database..."
    call(["influxd", "restore", "-database", databaseName, "-datadir", influx_data_dir, downloadPath])
    print "Fixing permissions (influxdb/influxdb)..."
    call(["chown", "-R", "influxdb:influxdb", influx_data_dir])
    print "Starting InfluxD process back up"
    call(["service", "influxdb", "start"])

    #cleanup
    #files = glob.glob(backup_path + '*')

    #remove restore folder and contentsa
    shutil.rmtree(backup_path)
    #for f in files:
    #    os.remove(f)
    #return;


def restorepoints( databaseName ):
    to_zone = tz.gettz('America/Los_Angeles')
    objects = client.list_objects(Bucket=backup_bucket, Prefix='influxdb/' + databaseName )

    for item in objects['Contents']:
        print(item['LastModified'].astimezone(to_zone).strftime('%Y-%m-%d_%H%M%S %Z') + " " + item['Key'])
    return;

def main(argv):

    parser = argparse.ArgumentParser(description='Script to backup or restore InfluxDB backups to/from AWS S3.')
    parser.add_argument('-b', '--backup', type=str, help='Backup a given Database')
    parser.add_argument('-p', '--path', type=str, default='/var/tmp/', help='Location of for Database Backups')
    parser.add_argument('-r', '--restore',type=str, help='Restore a backup from S3')
    parser.add_argument('-db', '--databasename', type=str, help='DB name to restore from backup')
    parser.add_argument('-rp', '--restorepoints', action='store_true', help='Get a list of available backups from S3')
    args = parser.parse_args()

    if (args.backup is not None and args.restore is None):
        print "backup has been set to %s" % args.backup
        print "destination has been set to %s" % args.path
        backup( args.backup )

    if (args.restore is not None and args.backup is None):
        if (args.databasename is not None):

            download_path = args.path + "/" + args.databasename

            if not os.path.exists(download_path):
                print "Restore path %s does not exist, creating..." % download_path
                os.makedirs(download_path)

            print "Downloading and Restoring %s from S3" % args.restore
            restore( args.restore, download_path, args.databasename )
            #restore( args.restore )

    if (args.backup is not None and args.restore is not None):
        print "You cannot backup and restore at the same time!"

    if (args.backup is None and args.restore is None and args.restorepoints is not None):
       restorepoints( args.databasename )


if __name__ == "__main__":
   main(sys.argv[1:])

