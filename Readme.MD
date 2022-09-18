# Simple Backup
Version 0.2.1

A simple script to back up your directories to Dropbox or local directory

## Usage
usage: backup.py [options]
```
example: python backup.py -q
example: python backup.py -q -c /path/to/config.yaml -t /path/to/.token
```

Options:
- `--version`  show program's version number and exit
- `-h, --help` show this help message and exit
- `-q, --quiet` don't print status messages to stdout
- `-c config.yaml, --config=/path/to/config.yaml` OPTIONAL: Config file location
- `-t .token, --token=/path/to/.token` OPTIONAL: Token file location
- `-a tar, --archive=tar` OPTIONAL: Archive format: `zip` (default), `tar` or `bztar`
## Configuration

Edit `config.yaml` to configure parameters for your backup

#### backup_type

- `dir` Backup of directory and its contents
- `db` Backup of SQL database *(Not Supported yet)*

```  
backup_type: dir
```

#### source

List of directories

```  
source:
    - /foo/bar/backup_dir
```

#### destination
Specify Backup destination, it can be single option or multiple destionations

- `local` Backup to the local directory
  - `path` Path where files should be copied
  - `archive` OPTIONAL: True or False (default) - specifies if directory needs to be archivated
- `dropbox` Backup to Dropbox directory
  - `path` Path where files should be uploaded
- `ftp` Backup to FTP server *(Not Supported yet)*

Dropbox requires OAuth2 access token, You can generate it in the Dropbox App Console.

See [Generate an access token for your own account](https://blogs.dropbox.com/developers/2014/05/generate-an-access-token-for-your-own-account/) 
Put it in the `.token` file in the same directory there script is located

```
destination:
    dropbox:
        path: /foo/bar
    local:
        path: /foo/bar/destination_dir
        archive: True
```