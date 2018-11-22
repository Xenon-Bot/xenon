# Xenon

## Requirements

You need Python 3.6.x to run the bot. >=3.7 and <=3.5 are not supported!  
Use `pip install -U -r requirements.txt` to install all python packages.

## config.py

config.py contains all sensitive values and some startup configurations.
You can use example_config.py, change all values that start with "your" and rename it to config.py.

If you only want to use specific parts of the bot, you can edit the variable "extensions". All extensions should work independent of each other.
(But I wouldn't recommend you to disable the errors extension.)

## Database

The bot requires a rethinkdb-database running on port 28015. All backups, templates and user information are saved there.
You can find more information about rethinkdb [here](https://www.rethinkdb.com/docs/install/).

## Logs

The bot creates log files in the logs/ directory. You might need to create it if it isn't already there.
