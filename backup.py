import os
import sys
import optparse
import yaml
import time
from datetime import datetime
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

app_version = 0.1
dir_path = os.path.dirname(os.path.abspath(__file__))
timestamp_format = "%m/%d/%Y, %H:%M:%S"

# Add OAuth2 access token here.
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
                print(yaml.safe_load(stream))
            except yaml.YAMLError as exc:
                log_error(exc)
    except FileNotFoundError as exc:
        log_error(f"Backup config file not found - {exc}")


def retry(func, *func_args, **kwargs):
    count = kwargs.pop("count", 5)
    delay = kwargs.pop("delay", 5)
    return any(func(*func_args, **kwargs)
               or log_error("waiting for %s seconds before retyring again" % delay)
               or time.sleep(delay)
               for _ in range(count))


class BackupConfig:
    def __init__(self, backup_type, verify):
        self.type = backup_type
        self.verify = verify


def dropbox_backup(file, backup_path):
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
        with open(file, 'rb') as f:
            # We use WriteMode=overwrite to make sure that the settings in the file
            # are changed on upload
            print("Uploading " + file + " to Dropbox as " + backup_path + "...")
            try:
                dbx.files_upload(f.read(), file, mode=WriteMode('overwrite'))
            except ApiError as err:
                # This checks for the specific error where a user doesn't have
                # enough Dropbox space quota to upload this file
                if (err.error.is_path() and
                        err.error.get_path().reason.is_insufficient_space()):
                    sys.exit("ERROR: Cannot back up; insufficient space.")
                elif err.user_message_text:
                    print(err.user_message_text)
                    sys.exit()
                else:
                    log_error(err)
                    sys.exit()


def main():
    read_config()


if __name__ == '__main__':
    main()
