import discord
import typing
import asyncio
from discord.ext import commands

client = commands.Bot(command_prefix=">")
client.sandboxes = {}

TOKEN = open("token.txt", "r").read().decode("utf-8").strip()

sandbox = client.command_group("sandbox", "Commands to manage guild sand box creations.")

class Sandbox:
    def __init__(self, guild, owner_id, msg, invite):
        self.guild = guild
        self.owner_id = owner_id
        self.msg = msg
        self.invite = invite

class GenericSettings(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Delete Sandbox")
    async def delete(self, button, interaction):
        class ConfirmView(discord.ui.View):
            def __init__(self):
                self.con = None
                super().__init__(timeout=180)
            @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
            async def yes(self, button, interaction):
                self.con = True
                self.stop()
            @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
            async def no(self, button, interaction):
                self.con = False
                self.stop()
            async def on_timeout(self):
                for i in self.children:
                    i.disabled = True
                await self.msg.edit(view=self)
        
        view = ConfirmView()
        view.msg = await interaction.response.send_message("Are you sure you want to delete this sandbox?", view=view, ephemeral=True)
        await view.wait()
        if view.con == False:
            await view.msg.delete()
        elif view.con == True:
            await interaction.followup.send("@everyone This sandbox will be deleted in 10 seconds.")
            await asyncio.sleep(10)
            sandbox = client.sandboxes.pop(str(interaction.guild_id))
            await sandbox.guild.delete()

    async def interaction_check(self, interaction):
        if interaction.user.id != self.sandbox.owner_id:
            await interaction.response.pong()
            return False
        else:
            return True

@sandbox.command()
async def open(
    ctx,
    visibility: discord.commands.Option(str, description="Whether to send the sandbox invite into the channel or make a hidden message", required=False, choices=[discord.commands.OptionChoice(name="public", value="1"), discord.commands.OptionChoice(name="private", value="2")]),
    name: discord.commands.Option(str, description="Set the name of the sandbox", required=False),
    bot: discord.commands.Option(discord.Member, description="A bot you want to test in the sandbox.", required=False)
):
    # TODO: implment support for bot param
    if ctx.author.id not in [719980255942541362]:
        return await ctx.respond("no", ephemeral=True)
    if str(ctx.guild.id) in client.sandboxes:
        return await ctx.respond("Cannot create sandboxes from within sandboxes.", ephemeral=True)
    if bot.bot != True:
        return await ctx.respond("That's not a bot.", ephemeral=True)
    
    if name == None:
        name = f"Sandbox #{len(client.sandboxes)+1}"
    guild = client.get_guild((await client.create_guild(name=name, code="n5GsdsJdres4")).id)
    invite = await (await guild.fetch_channels())[0].create_invite()
    ch = discord.utils.get(guild.text_channels, name="settings")
    view = GenericSettings()
    view.msg = msg = await ch.send("Click a button to toggle settings:", view=view)
    sandbox = view.sandbox = Sandbox(guild, ctx.author.id, msg, invite)
    client.sandboxes[str(guild.id)] = sandbox
    if visibility == "1":
        await ctx.respond(f"Sandbox Created, permanent invite: {invite.url}")
    else:
        await ctx.respond(f"Sandbox Created, permanent invite: {invite.url}", ephemeral=True)

client.run(TOKEN)

