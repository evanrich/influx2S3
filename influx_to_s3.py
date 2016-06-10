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
import os
import glob
import tarfile
import time
import sys
import shutil
from subprocess import call
from dateutil import tz

# some variables we'll use
BACKUP_PATH = '/var/tmp/restore/'
BACKUP_TIME = str(int(time.time()))
INFLUXDB_DATA_DIR = "/var/lib/influxdb/data"
INFLUXDB_META_DIR = "/var/lib/influxdb/meta"
BACKUP_BUCKET = ''
ACCESS_KEY_ID = ''
SECRET_KEY = ''
UPLOAD_FOLDER = 'influxdb'
CLIENT = boto3.client(
    's3',
    aws_access_key_id = ACCESS_KEY_ID,
    aws_secret_access_key = SECRET_KEY,
)


def backup(database_name):

    # backup
    call(["influxd", "backup", "-database", database_name, BACKUP_PATH])

    # create tar file
    # time = str(int(time.time()))

    tar = tarfile.open(BACKUP_PATH + database_name + '_'
                       + BACKUP_TIME + '.tar.gz', "w:gz")
    for name in glob.glob(BACKUP_PATH + "*.00"):
        # print os.path.basename(name)
        tar.add(name, arcname=os.path.basename(name))
    tar.close()

    # upload backup
    archive_path = max(glob.iglob(BACKUP_PATH + '*.gz'), key=os.path.getctime)
    archive_name = os.path.basename(archive_path)
    CLIENT.upload_file(archive_path, BACKUP_BUCKET, UPLOAD_FOLDER + '/'
                       + archive_name)

    # cleanup
    files = glob.glob(BACKUP_PATH + '*')
    for f in files:
        os.remove(f)
    return;


def restore(backup_to_restore, download_path, database_name):
    print "Downloading restore point: %s" % backup_to_restore

    if not os.path.exists(download_path + "/" + database_name):
        os.makedirs(download_path + "/" + database_name)

    CLIENT.download_file(BACKUP_BUCKET, backup_to_restore, download_path + '/'
                         + 'InfluxRestore.tar.gz')

    # untar backup
    archive_path = max(glob.iglob(download_path + "/" + '*.gz'),
                       key=os.path.getctime)
    archive_name = os.path.basename(archive_path)

    print download_path
    print "Extracting Archive..."
    os.chdir(download_path)
    tar = tarfile.open('InfluxRestore.tar.gz')
    tar.extractall()
    tar.close()

    # cleanup
    files = glob.glob(download_path + '*.gz')
    for f in files:
        os.remove(f)

    # restore
    print "Stopping influxD process"
    call(["service", "influxdb", "stop"])
    print "Restoring backup from %s" % download_path
    print "Restoring metadata..."
    call(["influxd", "restore", "-metadir", INFLUXDB_META_DIR, download_path])
    print "Restoring database..."
    call(["influxd", "restore", "-database", databaseName, "-datadir",
         INFLUXDB_DATA_DIR, download_path])
    print "Fixing permissions (influxdb/influxdb)..."
    call(["chown", "-R", "influxdb:influxdb", INFLUXDB_DATA_DIR])
    print "Starting InfluxD process back up"
    call(["service", "influxdb", "start"])

    # cleanup

    # remove restore folder and contents
    shutil.rmtree(download_path)


def restorepoints(database_name):
    to_zone = tz.gettz('America/Los_Angeles')
    objects = CLIENT.list_objects(Bucket=BACKUP_BUCKET, Prefix='influxdb/'
                                  + database_name)

    for item in objects['Contents']:
        print(item['LastModified'].astimezone(to_zone).strftime('%Y-%m-%d_%H%M%S %Z') + " " + item['Key'])
    return;


def main(argv):

    parser = argparse.ArgumentParser(description='Script to backup or restore' +
                                     'InfluxDB backups to/from AWS S3.')
    parser.add_argument('-b', '--backup', type=str,
                        help='Backup a given Database')
    parser.add_argument('-p', '--path', type=str, default='/var/tmp/',
                        help='Location of for Database Backups')
    parser.add_argument('-r', '--restore', type=str,
                        help='Restore a backup from S3')
    parser.add_argument('-db', '--databasename', type=str,
                        help='DB name to restore from backup')
    parser.add_argument('-rp', '--restorepoints', action='store_true',
                        help='Get a list of available backups from S3')
    args = parser.parse_args()

    if (args.backup is not None and args.restore is None):
        print "backup has been set to %s" % args.backup
        print "destination has been set to %s" % args.path
        backup(args.backup)

    if (args.restore is not None and args.backup is None):
        if (args.databasename is not None):

            download_path = args.path + "/" + args.databasename

            if not os.path.exists(download_path):
                print "Restore path %s does not exist, creating..." % download_path
                os.makedirs(download_path)

            print "Downloading and Restoring %s from S3" % args.restore
            restore(args.restore, download_path, args.databasename)

    if (args.backup is not None and args.restore is not None):
        print "You cannot backup and restore at the same time!"

    if (args.backup is None and args.restore is None and args.restorepoints is not None):
        restorepoints(args.databasename)


if __name__ == "__main__":
    main(sys.argv[1:])

