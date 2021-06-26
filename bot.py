import os.path as osp
import os
# import smtplib
# import ssl
import random

import discord
from discord.ext import commands

from util.data.hashing import Hashing

print("Starting...")

current_dir = osp.dirname(__file__)  # grab the current system directory on an os-independent level
data_path = "data"  # folder name

# The extensions ("cogs") to load
extensions = ["errors", "misc", "reactor", "utility", "verification", "verify_wizard"]

# Load new intents system. This is required for the new reactors functionality.
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.reactions = True

# Start the bot functions.
do_run = True

# Set up variables
bot_token = None
used_emails = None
bot_key = None
hash_key = None

# Start config loading from disk.
try:
	print("Loading config...")

	bot_token = os.environ["token"]
	bot_key = os.environ["key"]
	used_emails = os.environ["used_emails"]
	hash_key = os.environ["hash_key"]

	do_run = True
except KeyError as e:
	print(f"Config error.\n\tKey Not Loaded: {e}")
	do_run = False

# Seed the random number generator from the bot token.
random.seed(bot_token)

# From the used_emails filename, load the data from the data folder. This can be commented out if not using a data folder.
used_emails = osp.join(current_dir, data_path, used_emails)


def prefix(bot, message):
	pfx = bot_key

	# If prefix has a space after it, try using it instead
	# 	Ex: `! email` is the same as `!email`
	if str(message.content).startswith(f"{pfx} "):
		pfx = f"{pfx} "

	return pfx


# Set up the bot based on the loaded bot prefix and load the intents system.
bot = commands.Bot(command_prefix=prefix, intents=intents)

# Set up hashing, salt (key) based on defined hash key
hashing = Hashing(hash_key)

# Set attributes to bot, used in other modules
setattr(bot, "current_dir", current_dir)
setattr(bot, "data_path", data_path)
setattr(bot, "hashing", hashing)

# By default, there's no help command other than vhelp. This is so that it doesn't interfere with other bots using the same prefix.
bot.remove_command('help')


# Update discord presence when everything is successfully loaded.
@bot.event
async def on_ready():
	await bot.change_presence(activity=discord.Activity(name="verifications", type=discord.ActivityType.watching))
	print(f'We have logged in as {bot.user}')


# Set up per-message checks.
@bot.event
async def on_message(message):
	if message.author == bot.user:
		return
	await bot.process_commands(message)


# Loads extensions before running bot
if __name__ == "__main__":

	count = 0
	for extension in extensions:
		try:
			bot.load_extension(f"cogs.{extension}")
			print(f"Cog | Loaded {extension}")
			count += 1
		except Exception as error:
			print(f"{extension} cannot be loaded. \n\t[{error}]")

	print(f"Loaded {count}/{len(extensions)} cogs")

if do_run:
	bot.run(bot_token)
else:
	print("Startup aborted.")
