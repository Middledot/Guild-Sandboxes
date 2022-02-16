import discord
import asyncio
import re
from discord.ext import commands

client = commands.Bot(command_prefix=">", intents=discord.Intents.all())
client.sandboxes = dict()
client.whitelisted_guilds = [...]  # Guilds that aren't sandboxes basically

MENTION_REGEX = f"<@!*&*[0-9]+>"
TOKEN = open("token.txt", "r").read().decode("utf-8").strip()

# client.load_extension("jishaku")  # for testing :O

@client.event
async def on_ready():
    sandbox_guilds = [g for g in client.guilds if g.id not in client.whitelisted_guilds]
    for guild in sandbox_guilds:
        ch = discord.utils.get(guild.text_channels, name="settings")
        messages = await ch.history(limit=20).flatten()
        for e in messages:
            if e.author.id == client.user.id and "Click a button to toggle settings:" in e.content:
                view = GenericSettings.from_message(e, timeout=None)
                owner_id = re.findall(MENTION_REGEX, e.content)[0].lstrip("<@!").rstrip(">")
                client.sandboxes[str(guild.id)] = sandbox = Sandbox(guild, int(owner_id), e, None)
                view.sandbox = sandbox
                view.msg = e
                client.add_view(view, message_id=e.id)

@client.event
async def on_member_join(member: discord.Member):
    if member.guild.id in client.whitelisted_guilds:
        return
    if str(member.guild.id) in client.sandboxes:
        sandbox = client.sandboxes[str(member.guild.id)]
        if member.id == sandbox.owner_id:
            role = discord.utils.get(member.guild.roles, name="Admin")
            if role == None:
                return
            await member.add_roles(role)


class Sandbox:
    def __init__(self, guild, owner_id, msg, invite):
        self.guild = guild
        self.owner_id = owner_id
        self.msg = msg
        self.invite = invite

class GenericSettings(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @classmethod
    def from_message(cls, message, timeout):
        view = GenericSettings()
        for component in discord.ui.view._walk_all_components(message.components):
            view.add_item(discord.ui.view._component_to_item(component))
        return view

    @discord.ui.button(label="Delete Sandbox", style=discord.ButtonStyle.danger, custom_id="delete_sandbox")
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
            box = client.sandboxes.pop(str(interaction.guild_id))
            await box.guild.delete()

    @discord.ui.button(label="Invite Test Bot", style=discord.ButtonStyle.blurple, custom_id="invite_bot")
    async def invite(self, button, interaction):
        e = self
        class InviteTestBotThing(discord.ui.View):
            def __init__(self):
                super().__init__()
                self.add_item(discord.ui.Button(label="Quick Link", url=f"https://discord.com/api/oauth2/authorize?client_id={e.bot}&permissions=8&scope=bot%20applications.commands&disable_guild_select=true&guild_id={e.guild_id}", style=discord.ButtonStyle.link))
        await interaction.response.send_message("Here", view=InviteTestBotThing(), ephemeral=True)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.sandbox.owner_id:
            await interaction.response.pong()
            return False
        else:
            return True

sandbox = client.create_group("sandbox", "Commands to manage guild sand box creations.")


@sandbox.command()
async def open(
    ctx,
    visibility: discord.commands.Option(str, description="Whether to send the sandbox invite into the channel or make a hidden message", required=False, choices=[discord.commands.OptionChoice(name="public", value="1"), discord.commands.OptionChoice(name="private", value="2")]),
    name: discord.commands.Option(str, description="Set the name of the sandbox", required=False),
    bot: discord.commands.Option(discord.Member, description="A bot you want to test in the sandbox.", required=False)
):
    if ctx.author.id not in [719980255942541362]:
        return await ctx.respond("no", ephemeral=True)
    if str(ctx.guild.id) in client.sandboxes:
        return await ctx.respond("Cannot create sandboxes from within sandboxes.", ephemeral=True)
    if bot.bot != True:
        return await ctx.respond("That's not a bot.", ephemeral=True)

    if name == None:
        name = f"Sandbox #{len(client.sandboxes)+1}"
    guild = await client.fetch_guild((await client.create_guild(name=name, code="GN9R7E5CWkfJ")).id)
    invite = await (await guild.fetch_channels())[0].create_invite()
    ch = discord.utils.get((await guild.fetch_channels()), name="settings")
    await guild.create_role(reason="Gib Admin to Person pls", name="Admin", permissions=discord.Permissions.all())
    view = GenericSettings()
    view.msg = msg = await ch.send(f"Hello {ctx.author.mention}\nClick a button to toggle settings:", view=view)
    view.guild_id = guild.id
    view.bot = bot.id
    sandbox = view.sandbox = Sandbox(guild, ctx.author.id, msg, invite)
    client.sandboxes[str(guild.id)] = sandbox
    if visibility == "1":
        await ctx.respond(f"Sandbox Created, permanent invite: {invite.url}")
    else:
        await ctx.respond(f"Sandbox Created, permanent invite: {invite.url}", ephemeral=True)


client.run(TOKEN)
