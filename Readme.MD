# Simple Backup
Version 0.1

A simple script to back up your directories to Dropbox or local directory

## Configuration

Edit `config.yaml` to configure parameters for your backup

#### backup_type

- `dir` Backup of directory and its contents
- `db` Backup of SQL database *(Not Supported yet)*

#### source

List of directories

```  
source:
    - /foo/bar/backup_dir
```

#### destination
Specify Backup destination, it can be single option or multiple destionations

- `local` Backup to the local directory
- `dropbox` Backup to Dropbox directory
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
```