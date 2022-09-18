import errno
import optparse
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import dropbox
import yaml
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode
from tqdm import tqdm

app_version = '0.2.0'
dir_path = os.path.dirname(os.path.abspath(__file__))
timestamp_format = "%m/%d/%Y, %H:%M:%S"

parser = optparse.OptionParser(
    usage=f"""
    This script will back up your directories to Dropbox or local directory 

    usage: %prog [options]
    example: python %prog -q
    example: python %prog -q -c /path/to/config.yaml
    example: python %prog -q -c /path/to/config.yaml -t /path/to/.token
    """,
    version=f"v{app_version}"
)
parser.add_option("-q", "--quiet",
                  action="store_false", dest="verbose", default=True,
                  help="don't print status messages to stdout")

parser.add_option("-c", "--config",
                  action="store",  # optional because action defaults to "store"
                  dest="config",
                  default=f"{dir_path}/config.yaml",
                  help="OPTIONAL: Config file location", )

parser.add_option("-t", "--token",
                  action="store",  # optional because action defaults to "store"
                  dest="token",
                  default=f"{dir_path}/.token",
                  help="OPTIONAL: Token file location", )

options, args = parser.parse_args()
option_dict = vars(options)


def read_config(config_path):
    try:
        with open(config_path, "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                SimpleLogger.error(exc)
    except FileNotFoundError as exc:
        SimpleLogger.error(f"Backup config file not found - {exc}")


class SimpleLogger:
    @staticmethod
    def error(message):
        with open(f"{dir_path}/error.log", "a", encoding='utf-8') as f:
            timestamp = datetime.now().strftime(timestamp_format)
            f.write(f"[{timestamp}]: ERROR: {message}\n")
        sys.exit(f"ERROR: {message}")

    @staticmethod
    def msg(message):
        with open(f"{dir_path}/backup.log", "a", encoding='utf-8') as f:
            timestamp = datetime.now().strftime(timestamp_format)
            f.write(f"[{timestamp}]: {message}\n")
        if option_dict['verbose'] is True:
            print(message)


class Backup:
    def __init__(self, backup_name, backup_type, sources, destination):
        self.backup_name = backup_name
        self.backup_type = backup_type
        self.sources = sources
        self.destination = destination

    def backup_dir(self):
        for source in self.sources:
            SimpleLogger.msg(f"Backing up {source}")
            for (dirpath, dirnames, filenames) in (os.walk(source)):
                for filename in tqdm(filenames, desc=os.path.basename(dirpath), leave=False):
                    file_from = Path(dirpath, filename)
                    if 'local' in self.destination:
                        file_to = Path(self.destination['local']['path'],
                                       Path(dirpath).relative_to(Path(source).parent),
                                       filename)
                        local_bak = LocalBackup(file_from, file_to)
                        local_bak.copy_files()
                    if 'dropbox' in self.destination:
                        file_to = Path(self.destination['dropbox']['path'],
                                       Path(dirpath).relative_to(Path(source).parent),
                                       filename)
                        dbx_bak = DropboxBackup(file_from, file_to.as_posix())
                        dbx_bak.upload()
        SimpleLogger.msg("Backup is complete.")


class LocalBackup:
    def __init__(self, file, backup_path, archive=False):
        self.file = file
        self.backup_path = backup_path
        self.archive = archive

    def copy_files(self):
        try:
            shutil.copy(self.file, self.backup_path)
        except IOError as e:
            # ENOENT(2): file does not exist, raised also on missing dest parent dir
            if e.errno != errno.ENOENT:
                raise
            # try creating parent directories
            os.makedirs(os.path.dirname(self.backup_path))
            shutil.copy(self.file, self.backup_path)


class DropboxBackup:
    def __init__(self, file_from, file_to):
        self.file_from = file_from
        self.file_to = file_to
        self.token = self.read_token()

    @staticmethod
    def read_token():
        try:
            with open(option_dict['token']) as t:
                token = t.read()
                if len(token) == 0:  # Check for access token
                    SimpleLogger.error("Looks like you didn't add your Dropbox access token. ")
                return token
        except FileNotFoundError as err:
            SimpleLogger.error(err)

    @staticmethod
    def retry(func, *func_args, **kwargs):
        count = kwargs.pop("count", 5)
        delay = kwargs.pop("delay", 5)
        return any(func(*func_args, **kwargs)
                   or SimpleLogger.error(f"Failed to upload to Dropbox - "
                                         f"waiting for {delay} seconds before re-tyring again")
                   or time.sleep(delay)
                   for _ in range(count))

    def upload(self):
        # Create an instance of a Dropbox class, which can make requests to the API.
        with dropbox.Dropbox(self.token) as dbx:
            # Check that the access token is valid
            try:
                dbx.users_get_current_account()
            except AuthError:
                msg = "Invalid Dropbox access token; " \
                      "try re-generating an access token from the app console on the web."
                SimpleLogger.error(msg)
            # Create a backup
            with open(self.file_from, 'rb') as f:
                # We use WriteMode=overwrite to make sure that the settings in the file
                # are changed on upload
                try:
                    dbx.files_upload(f.read(), self.file_to, mode=WriteMode('overwrite'))
                    return True
                except ApiError as err:
                    # This checks for the specific error where a user doesn't have
                    # enough Dropbox space quota to upload this file
                    if (err.error.is_path() and
                            err.error.get_path().reason.is_insufficient_space()):
                        SimpleLogger.error("Cannot back up to Dropbox; insufficient space.")
                    elif err.user_message_text:
                        SimpleLogger.error(err.user_message_text)
                    else:
                        SimpleLogger.error(err)
                        return False


def main():
    config_dict = read_config(option_dict['config'])
    for item in config_dict:
        i = config_dict[item]
        for key, value in i.items():
            if key not in ['backup_type', 'source', 'destination']:
                SimpleLogger.error(f"Wrong configuration parameter: {key}")
        try:
            b = Backup(item, i['backup_type'], i['source'], i['destination'])
            if b.backup_type == 'dir':
                b.backup_dir()
            elif b.backup_type == 'db':
                print(i)
                SimpleLogger.msg("WARNING: Database backups not supported yet")
            else:
                SimpleLogger.error(f"unsupported backup type: {b.backup_type}")
        except KeyError as err:
            SimpleLogger.error(f"wrong Backup config, missing {err} parameter")
        except AttributeError as err:
            SimpleLogger.error(f"wrong Backup config, {err}")
        except KeyboardInterrupt:
            print("Operation is aborted by user")
            sys.exit(0)


if __name__ == '__main__':
    main()
