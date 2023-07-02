######################################################################
# Project:    Sukajan Bot v0.1                                       #
# File Name:  member.py                                              #
# Author:     Sukajan One-Trick <tophuwo01@gmail.com>                #
# Description:                                                       #
#   a bot for the KirikoMains subreddit for advanced custom          #
#   features required by the moderation team                         #
#                                                                    #
# (C) 2023 Sukajan One-Trick. All rights reserved.                   #
######################################################################

# This file implements the 'member' module.

# imports
import logging
import discord
import discord.ext.commands as commands

import src.client as sj_client


# 'member' module class
class SukajanMemberModule(commands.Cog):
    def __init__(self, client: sj_client.SukajanClient):
        self._client = client


    # Overrides the event that is called whenever a member joins
    # the guild.
    #
    # Returns nothing.
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        # Check if welcome channel is configured and the setting is enabled.
        chanid = int(self._client.gcfg[member.guild.id].welcomechan)
        if chanid is None:
            logging.warning(f'Welcome channel for guild "{member.guild.name}" (id: {member.guild.id}) is not configured.')

            return

        # Get welcome channel by id and send welcome message.
        chan = member.guild.get_channel(chanid)
        user = self._client.get_user(member.id)
        await chan.send(f'Welcome to *{member.guild.name}*, **{user.name}**!')


# 'member' module setup method
async def setup(client: commands.Bot) -> None:
    await client.add_cog(SukajanMemberModule(client))


