# Xenon

> :warning: **This version of the bot is no longer under active development**: You can find the newest version of the bot and more information at Magic-Bots/xenon-worker  
  
  
[![Codefresh build status]( https://g.codefresh.io/api/badges/pipeline/merlintor/Xenon%2Fdeploy?type=cf-1)]( https://g.codefresh.io/public/accounts/merlintor/pipelines/5d4d4cc311b8859327cf24e0)
[![Discord Server]( https://discordapp.com/api/guilds/410488579140354049/embed.png)]( https://discord.club/discord)

## Disclaimer

You might need basic knowledge of python, pip, git and the console of your operating system to run this bot.  
If you need further help you can join the [support discord](https://discord.club/discord), but I won't answer any question regarding the topics above.

[Hosted Version](https://discordbots.org/bot/xenon)

## With Docker (Recommended)

Download and install [docker](https://www.docker.com/) on your operating system.

Build and run it with docker-compose:

1. Download / Clone the repository (preferably the selfhost branch)
2. Edit the `xenon.env` file and change the token
3. You might wanna change some values in `xenon/config.py` e.g. the prefix (maybe disable the templates cog aswell)
4. Create a `xenon/logs` directory for the log files
5. Run `docker-compose build`
6. Run `docker-compose up`

The database and the bot should start up.

## Without Docker

Download and run a [mongodb](https://www.mongodb.com/) server and make the port 27017 accessible by the python script.  
Install all dependencies, edit `xenon/config.py` and change the token, run `xenon/launcher.py`.
At least Python version 3.7 is required.
