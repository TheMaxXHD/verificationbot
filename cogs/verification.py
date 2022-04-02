import os
import os.path as osp
import smtplib
import ssl
import random

import discord
from discord.ext import commands

from util.email import is_valid_email


class Verification(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

		try:
			# bot_token = os.environ["token"]
			self.bot_key = os.environ["key"]
			self.used_emails = os.environ["used_emails"]
			self.warn_emails = os.environ["warn_emails"]
			self.moderator_email = os.environ["moderator_email"]

			self.sample_username = os.environ["sample"]
			self.verify_domain = os.environ["domain"]
			self.email_from = os.environ["from"]
			self.email_password = os.environ["password"]
			self.email_subject = os.environ["subject"]
			self.email_server = os.environ["server"]
			self.email_port = os.environ["port"]

			self.role = os.environ["server_role"]
			self.channel_id = os.environ["channel_id"]
			self.welcome_id = os.environ["welcome_id"]
			self.notify_id = os.environ["notify_id"]
			self.admin_id = os.environ["admin_id"]
			self.author_name = os.environ["author_name"]
			self.webmail_link = os.environ["webmail_link"]

			self.channel_id = int(self.channel_id)
			self.welcome_id = int(self.welcome_id)
			self.notify_id = int(self.notify_id)
			self.admin_id = int(self.admin_id)
			self.email_port = int(self.email_port)

			self.used_emails = osp.join(self.bot.current_dir, self.bot.data_path, self.used_emails)
			self.warn_emails = osp.join(self.bot.current_dir, self.bot.data_path, self.warn_emails)

		except KeyError as e:
			print(f"Config error.\n\tKey Not Loaded: {e}")

		# Create empty lists for currently active tokens, emails, and attempt rejection.
		self.token_list = {}
		self.email_list = {}
		self.email_attempts = {}
		self.verify_attempts = {}

	# Instructions on how to verify.
	# noinspection PyUnusedLocal
	@commands.command(name="vhelp", aliases=["helpme", "help_me", "verify_help", "Vhelp", "Helpme", "Help_me", "Verify_help"])
	async def verify_help(self, ctx, *args):
		"""
		Help on how to verify.
		"""
		verify_email = ctx.guild.get_channel(self.channel_id)
		# The line below contains the verify_help command text output.
		await ctx.send(
			f"To use this bot, please use `{self.bot_key}email {self.sample_username}@{self.verify_domain}` in {verify_email.mention} "
			f"to receive an email with a **6 digit verification token.** Replace `{self.sample_username}@{self.verify_domain}` with "
			f"your own email, keeping in mind that the bot only accepts email addresses with `@{self.verify_domain}` at the end. "
			f"**Wait for an email to be received**. If you don't receive an email after 5 minutes, try using the email "
			f"command again. **Send the command provided in the email** as a message in the {verify_email.mention} channel "
			f"to gain access to the rest of the server."
			f"\n\nYou can access your webmail at {self.webmail_link}"
			f"\n**Make sure to check your junk email folder for the message in case it gets sent there.**"
			f"\n\n**Send messages in the {verify_email.mention} channel to use this "
			f"bot's commands, not in a DM.**")

	# The email command handles all the checks done before an email is sent out alongside the actual email sending.
	# It's very complicated.
	@commands.command(name="email", aliases=["mail", "send", "Email", "Mail", "Send"])
	@commands.guild_only()
	async def _email(self, ctx, arg):
		"""
		Sends an email containing a token to verify the user
		Parameters
		------------
		email: str [Required]
			The email that the token will be sent to.
		"""

		if ctx.channel.id == self.channel_id:
			print(f'Emailing user {ctx.author.name}, email {arg}')  # This gets sent to the console only.
			await ctx.message.delete()  # delete their email from the channel, to prevent it leaking.

			try:
				dm = arg.split('@')[1]  # split the string based on the @ symbol
			except AttributeError:
				await ctx.send("Error! That is not a valid email!")  # no @ symbol = no email
				return

			if not is_valid_email(arg):
				return await ctx.send("Error! That is not a valid email!")

			blacklist_names = [self.sample_username]  # If any email begins with one of these, it's invalid

			if any(arg.lower().startswith(name.lower()) for name in blacklist_names):
				await ctx.send(
					f"{ctx.author.mention} Use your own email, not the sample one. Please try again with your own email.")
				return

			try:
				with open(self.used_emails, 'r') as file:  # Checks the used emails file to see if the email has been used.
					if any(self.bot.hashing.check_hash(str(arg.lower()), str(line).strip('\n')) for line in file):
						admin = await self.bot.fetch_user(self.admin_id)
						await ctx.send(
							f"Error! That email has already been used! If you believe this is an error or are trying to "
							f"re-verify, please contact {admin.mention} in this channel or through direct message. Thanks!")
						file.close()
						return
					file.close()
			except FileNotFoundError:
				print("Used emails file hasn't been created yet, continuing...")

			try:
				with open(self.warn_emails, 'r') as file:  # Checks the warning email file to notify moderators if an email on the list is used. For example, a list of professor emails could be loaded.
					if any(str(arg.lower()) == str(line).strip('\n').lower() for line in file):
						sendIn = ctx.guild.get_channel(self.notify_id)
						await sendIn.send(
							f"Alert! Email on warning list used. Discord ID: {ctx.author.mention}, email `{arg}`.")
					file.close()
			except FileNotFoundError:
				print("Warning list file not found, ignoring.")

			# This is a bit of a hacky way to do an email attempt checking system. If someone tries to repeatedly use the email command, they will be blacklisted from further attempts.
			maxedOut = False
			try:
				if self.email_attempts[ctx.author.id] >= 5:
					maxedOut = True
					await ctx.send(
						f"{ctx.author.mention}, you have exceeded the maximum number of command uses. Please contact a "
						f"moderator for assistance with verifying if this is in error. Thanks!")
					sendIn = ctx.guild.get_channel(self.notify_id)
					await sendIn.send(f"Alert! User {ctx.author.mention} has exceeded the amount of `!email` command uses.")
					return
			except:
				print("")

			if dm == self.verify_domain and not maxedOut:  # Send the actual email.
				await ctx.send("Sending verification email...")
				with smtplib.SMTP_SSL(self.email_server, self.email_port, context=ssl.create_default_context()) as server:
					server.login(self.email_from, self.email_password)
					token = random.randint(100000, 999999)
					self.token_list[ctx.author.id] = str(token)
					self.email_list[ctx.author.id] = arg
					verify_email = ctx.guild.get_channel(self.channel_id)

					message_text = f"Hello {self.author_name}! Thank you for joining the PSU Discord Server! \n\n" \
						f"The command to use in the #{verify_email.name} channel is: {self.bot_key}verify {token}\n\n" \
						f"You can copy and paste that command into the #{verify_email.name} channel to verify. \n\n" \
						f"This message was sent by the PSU Discord Email Bot. \n" \
						f"If you did not request to verify, please contact {self.moderator_email} to let us know."
					message = f"Subject: {self.email_subject}\n\n{message_text}"
					server.sendmail(self.email_from, arg, message)
					server.quit()

				await ctx.send(f"Verification email sent {ctx.author.mention}, do `{self.bot_key}verify ######`, where `######` is the token, to verify. " 
				f"\n**Please check your spam/junk email folder if you have not received an email!** "
				f"\nIf no email arrives within 5 minutes, try using `{self.bot_key}email` followed by your PSU email address again in "
				f"{verify_email.mention}, or DM <@575252669443211264> for help.")

				if self.email_attempts:
					if ctx.author.id in self.email_attempts:
						self.email_attempts[ctx.author.id] += 1
					else:
						self.email_attempts[ctx.author.id] = 1
				else:
					self.email_attempts[ctx.author.id] = 1

			else:
				await ctx.send(f"Invalid email {ctx.author.mention}!")

	@commands.command(name="verify", aliases=["token", "Verify", "Token"])
	@commands.guild_only()
	async def _verify(self, ctx, arg):
		"""
		Verifies a user with a token that was previously emailed.
		For use after the 'email' command.
		Parameters
		------------
		token: int [Required]
			The token that was sent to the user via email.
		"""
		if ctx.channel.id == self.channel_id:
			print(f'Verifying user {ctx.author.name}, token {arg}')
			await ctx.message.delete()

			# this is copied from above to avoid an issue where two people could use the same email before it was verified.
			try:
				with open(self.used_emails, 'r') as file:  # Checks the used emails file to see if the email has been used.
					if any(self.bot.hashing.check_hash(str(self.email_list[ctx.author.id]), str(line).strip('\n')) for line in file):
						await ctx.send(
							"Error! That email has already been used! If you believe this is an error or are trying to "
							"re-verify, please contact a moderator by DMing <@575252669443211264> or through direct message. Thanks!")
						file.close()
						return
					file.close()
			except FileNotFoundError:
				print("Used emails file hasn't been created yet, continuing...")

			try:
				if self.verify_attempts[ctx.author.id] >= 5:
					await ctx.send(
						f"{ctx.author.mention}, you have exceeded the maximum number of command uses. Please contact a "
						f"moderator for assistance with verifying if this is in error. Thanks!")
					sendIn = ctx.guild.get_channel(self.notify_id)
					await sendIn.send(
						f"Alert! User {ctx.author.mention} has exceeded the amount of `!verify` command uses.")
					return
			except:
				print("")

			if self.token_list:
				if self.token_list[ctx.author.id] == arg:
					sendIn = ctx.guild.get_channel(self.welcome_id) # Checks for dedicated verified welcome message channel.
					#Line below sends welcome message to dedicated welcome channel after successful verification.
					await sendIn.send(f"Welcome{ctx.author.mention},<:4WE:494721524654145536> <:3ARE:494721824505200640> "
					"glad to have you here! Please assign yourself some roles in <#778461097488810015>, hop right in to "
					"<#354465848729141250>, or introduce yourself in <#811815122124800012> on the way there. Enjoy your stay! "
					"<:were:637756006880772126>")
					
					# Line below is commented out, original implementation. Unused in current implementation. Sends verified message to same channel verified command is sent.
					"""await ctx.send(f"{ctx.author.mention}, you've been verified!")"""

					role = discord.utils.get(ctx.guild.roles, name=self.role)
					if not role:
						role = discord.utils.find(lambda r: str(r.id) == str(self.role), ctx.guild.roles)
					await ctx.author.add_roles(role)

					with open(self.used_emails, 'a') as file:  # Writes used emails to file for verification
						hashed = self.bot.hashing.hash(self.email_list[ctx.author.id])
						file.write(f"{hashed}\n")
						file.close()
				else:
					await ctx.send(f"Invalid token {ctx.author.mention}!")
					if self.verify_attempts:
						if ctx.author.id in self.verify_attempts:
							self.verify_attempts[ctx.author.id] += 1
						else:
							self.verify_attempts[ctx.author.id] = 1
					else:
						self.verify_attempts[ctx.author.id] = 1

			else:
				print("Array does not exist yet! Verify will return nothing!")

	@commands.command(name="mod_verify", aliases=["manual_verify", "modverify", "manualverify", "addemail", "verifyadd"])
	@commands.guild_only()
	@commands.has_permissions(manage_messages=True)
	async def _manual_verify(self, ctx, email: str, userid: int):
		"""Manually add a user's email to the verified emails list without going through the actual verification process.
		Useful if the main verification process is failing for other reasons, but you still want to blacklist the email from future use.
		Parameters
		-----------
		email: string [Required]
			The email to add to the used emails list.
		"""
		print(f"Manually adding {email} to the used emails list for user {userid}.")

		# Check if the email's already in the file.
		try:
			with open(self.used_emails, 'r') as file:  # Checks the used emails file to see if the email has been used.
				if any(self.bot.hashing.check_hash(str(email.lower()), str(line).strip('\n')) for line in file):
					print(f"{email} already present in the emails list!")
					await ctx.send(f"{ctx.author.mention}, the email {email} is already in the used emails list.")
					return
		except FileNotFoundError:
			print("Used emails file hasn't been created yet, continuing...")

		user = await self.bot.fetch_user(userid)
		if user is not None:
			print(f"User with id {userid} found")
			role = discord.utils.get(ctx.guild.roles, name=self.role)
			if not role:
				role = discord.utils.find(lambda r: str(r.id) == str(self.role), ctx.guild.roles)
			await user.add_roles(role)  # This *should* work according to stackoverflow. I sure hope it does.

			with open(self.used_emails, 'a') as file:  # Writes used emails to file for verification
				hashed = self.bot.hashing.hash(self.email_list[ctx.author.id])
				file.write(f"{hashed}\n")
				file.close()
			print(f"Manually verified user {userid} with email {email}")
			await ctx.send(f"{ctx.author.mention}, the user {user.mention} has been manually verified with the email {email}.")
		else:  # if user isn't found
			print(f"User with id {userid} not found")
			await ctx.send(f"{ctx.author.mention}, the user with id {userid} was not found.")


def setup(bot):
	bot.add_cog(Verification(bot))
