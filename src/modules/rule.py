################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################

# rule.py - (log) rule implementation and commands

# imports
import discord

import src.module        as kiyo_mod
import src.utils         as kiyo_utils
import src.error         as kiyo_error
import src.modules.guild as kiyo_guild



# rule module
class KiyokoModule_Rule(kiyo_mod.KiyokoModule_Base):
    # all implemented rules, disabled by default
    RULES = [
        'on_member_leave'
    ]    

    # This command configures rules. Requires administrator permissions.
    # 
    # Returns nothing.
    @discord.app_commands.command(name = 'rule', description = 'manages advanced logging event rules')
    @discord.app_commands.guild_only()
    @discord.app_commands.default_permissions(manage_guild = True)
    @discord.app_commands.describe(
        rule    = 'rule setting to update',
        enabled = 'whether or not to enable the rule' 
    )
    @discord.app_commands.choices(
        rule = [discord.app_commands.Choice(name = rule, value = rule) for rule in RULES]   
    )
    async def cmd_rule(self, inter: discord.Interaction, rule: discord.app_commands.Choice[str], enabled: bool) -> None:
        # If the rule does not exist, throw an error.
        r = rule.value.strip().lower()
        if r not in self.RULES:
            raise kiyo_error.AppCmd_InvalidParameter
        
        # Get guild config.
        gcfg = self._app.gcman.getgconfig(inter.guild.id)
        if gcfg is None:
            raise kiyo_error.CommandInvokeError
        
        # Update rule config.
        if gcfg.logrules.get(r, None) is None:
            gcfg.logrules[r] = False
        old = gcfg.logrules[r]
        gcfg.logrules[r] = enabled
        # Update guild config.
        await kiyo_guild.updgsettings(self._app, gcfg)
        
        # Format embed and send.
        (embed, file) = kiyo_utils.cfgupdembed(
            inter = inter,
            desc  = 'rule',
            upd   = [(r, old, enabled)]
        )
        await kiyo_utils.sendmsgsecure(inter, embed = embed, file = file)
        


# module entrypoint
async def setup(app) -> None:
    # Add 'rules' command to the tree.
    await app.add_cog(KiyokoModule_Rule(app))
    

