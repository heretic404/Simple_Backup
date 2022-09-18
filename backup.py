import os
import sys
import shutil
import errno
import yaml
import time
import zlib
from datetime import datetime
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from tqdm import tqdm
from pathlib import Path

app_version = '0.1.1'
dir_path = os.path.dirname(os.path.abspath(__file__))
timestamp_format = "%m/%d/%Y, %H:%M:%S"
# Add OAuth2 access token, by creating .token file
# You can generate one for yourself in the App Console.
# See <https://blogs.dropbox.com/developers/2014/05/generate-an-access-token-for-your-own-account/>
TOKEN = ''


def log_error(message):
    with open(f"{dir_path}/error.log", "a", encoding='utf-8') as f:
        timestamp = datetime.now().strftime(timestamp_format)
        f.write(f"[{timestamp}]: {message}\n")
    print(message)


def read_config():
    try:
        with open(f"{dir_path}/config.yaml", "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                log_error(exc)
    except FileNotFoundError as exc:
        log_error(f"ERROR: Backup config file not found - {exc}")


def retry(func, *func_args, **kwargs):
    count = kwargs.pop("count", 5)
    delay = kwargs.pop("delay", 5)
    return any(func(*func_args, **kwargs)
               or log_error("ERROR: Failed to upload to Dropbox - waiting for %s seconds before retyring again" % delay)
               or time.sleep(delay)
               for _ in range(count))


class Backup:
    def __init__(self, backup_name, **kwargs):
        self.backup_name = backup_name
        for key, value in kwargs.items():
            if key in ['backup_type', 'source', 'destination', 'auth']:
                setattr(self, key, value)
            else:
                log_error(f"ERROR: Wrong configuration parameter: {key}")
                sys.exit()


def backup_dir(sources, destination):
    for source in sources:
        print(f"Backing up {source}")
        for (dirpath, dirnames, filenames) in (os.walk(source)):
            for filename in tqdm(filenames, desc=os.path.basename(dirpath), leave=False):
                file_from = Path(dirpath, filename)
                if 'local' in destination:
                    file_to = Path(destination['local']['path'],
                                   Path(dirpath).relative_to(Path(source).parent),
                                   filename)
                    local_backup(file_from, file_to)

                if 'dropbox' in destination:
                    file_to = Path(destination['dropbox']['path'],
                                   Path(dirpath).relative_to(Path(source).parent),
                                   filename)
                    retry(dropbox_upload, file_from, file_to.as_posix(), count=3, delay=1)
    print("Backup is complete.")


def local_backup(file, backup_path):
    try:
        shutil.copy(file, backup_path)
    except IOError as e:
        # ENOENT(2): file does not exist, raised also on missing dest parent dir
        if e.errno != errno.ENOENT:
            raise
        # try creating parent directories
        os.makedirs(os.path.dirname(backup_path))
        shutil.copy(file, backup_path)


def dropbox_upload(file_from, file_to):
    try:
        with open(f"{dir_path}/.token") as t:
            TOKEN = t.read()

            if len(TOKEN) == 0:  # Check for access token
                log_error("ERROR: Looks like you didn't add your Dropbox access token. ")
                sys.exit()

    except FileNotFoundError as err:
        log_error(err)
        sys.exit()

    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(TOKEN) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            msg = "ERROR: Invalid Dropbox access token; " \
                  "try re-generating an access token from the app console on the web."
            log_error(msg)
            sys.exit(msg)
        # Create a backup
        with open(file_from, 'rb') as f:
            # We use WriteMode=overwrite to make sure that the settings in the file
            # are changed on upload
            try:
                dbx.files_upload(f.read(), file_to, mode=WriteMode('overwrite'))
                return True
            except ApiError as err:
                # This checks for the specific error where a user doesn't have
                # enough Dropbox space quota to upload this file
                if (err.error.is_path() and
                        err.error.get_path().reason.is_insufficient_space()):
                    log_error("ERROR: Cannot back up to Dropbox; insufficient space.")
                    sys.exit()
                elif err.user_message_text:
                    print(err.user_message_text)
                    sys.exit()
                else:
                    log_error(err)
                    return False


def main():
    config_dict = read_config()
    for item in config_dict:
        b = Backup(item, **config_dict[item])
        try:
            if b.backup_type == 'dir':
                backup_dir(b.source, b.destination)
        except AttributeError as err:
            log_error(f"ERROR: wrong Backup config {err}")
        except KeyboardInterrupt:
            print("Operation is aborted by user")
            sys.exit(0)


if __name__ == '__main__':
    main()
