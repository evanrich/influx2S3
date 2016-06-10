<snippet>
  <content>

DISCLAIMER: 
I am not a python developer, this was thrown together using the help of google and stack overflow.   We needed a easy way to backup/restore our influx databases into S3.  This script accomplishes that, but could probably be cleaned up/improved greatly.   If anyone comes across this project and finds it useful, I'd really apprecate any feedback/improvements.

## Installation
Download script, insert your AWS Access ID, secret key, bucket name, and a folder you want to upload to (I default to a folder called influxdb).  You need to set the following:

```sh
backup_bucket   = '<put your bucket name here>'
access_key_id   = '<insert your aws access key here>'
secret_key      = '<insert your secret access key here>'
upload_folder   = '<leave as influxdb, or insert a folder name here>'
```

## Usage

Backup a database:
```sh
./influx_to_s3.py -b graphite
```

List restore points for a database:
```sh
./influx_to_s3.py -rp -d [Database Name]

root@metrics:/home/erichardson/influx_to_s3# ./influx_to_s3.py -rp -d graphite
2016-06-08_143228 PDT influxdb/graphite_1465421217.tar.gz
2016-06-08_154445 PDT influxdb/graphite_1465425555.tar.gz
2016-06-09_145035 PDT influxdb/graphite_1465508713.tar.gz
```

Restore a database:
```sh
./influx_to_s3.py -r [full_restore_point] -d [database Name] -p [path to restore to]
 ./influx_to_s3.py -r influxdb/graphite_1465508713.tar.gz -d graphite -p /var/tmp/restore/
 ```
 
 getting help:
 ```sh
 ./influx_to_s3.py -h
```
## Contributing
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D

</snippet>
