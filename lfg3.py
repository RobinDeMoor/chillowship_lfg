import discord
import os
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timezone
from drawer import generate_image

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)
friend_codes = {}
muted_people = []
current_id = 0
PARTY_SIZE = 4  # fixed party size
CHANNEL_ID = 0

def construct_embed(
    description: str,
    difficulty: str,
    members: list[discord.User],
    heroes: list[str],
    creator: str,
    timer: str,
    id : int
):
    roles = ["🛡 Tank", "⚔ DPS1", "⚔ DPS2", "💚 Healer"]
    member_names = []
    member_count = 0

    # for i, role in enumerate(roles):
    #     if members[i] is not None:
    #         friend_code = "No friend code registered"
    #         if members[i].display_name in friend_codes:
    #             friend_code = friend_codes[members[i].display_name]
    #         members_text += f"{role}: {members[i].display_name} {friend_code}\n"
    #         member_count += 1
    #     else:
    #         members_text += f"{role}: open\n"

    # ait interaction.response.edit_message(content=f"Time set to <t:{timestamp}:f> (<t:{timestamp}:R>)")
    time_data = f"<t:{timer}:R>"
    for i, role in enumerate(roles):
        if members[i] is not None:
            member_count += 1
            member_names.append(members[i].display_name)
        else:
            member_names.append("Open")
    friend_code = "No friend code registered"
    if creator in friend_codes:
        friend_code = friend_codes[creator]
    embed = discord.Embed(
        title=f"{creator}'s LFG ({member_count}/{PARTY_SIZE})",
        # description=f"**{difficulty}**\n{description}\n\n**Members:**\n{members_text}",
        description=friend_code + "\n" + f"LFG in: {time_data}",
        color=discord.Color.blurple(),
    )
    time_left = round((timer - datetime.now(timezone.utc).timestamp()) / 3600)


    image = generate_image(member_names, heroes, difficulty, time_left)
    image.save('test.png')
    file = discord.File("test.png", filename="test.png")
    embed.set_image(url="attachment://test.png")
    return embed, file


# --- Public LFG View ---
class LFGView(discord.ui.View):
    def __init__(
        self,
        creator: discord.User,
        description: str,
        difficulty: str,
        role: int,
        timer: str,
    ):
        super().__init__(timeout=None)
        self.creator = creator
        self.description = description
        self.difficulty = difficulty
        self.members = [None, None, None, None]
        self.members[role] = creator
        self.message: discord.Message | None = None  # track the public message
        self.last_update_time = datetime.now()
        self.heroes = ["None", "None", "None", "None"]
        self.timer = timer
        global current_id
        self.id_m = current_id
        current_id += 1

    @discord.ui.button(label="Join Party", style=discord.ButtonStyle.green)
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if None not in self.members:
            await interaction.response.send_message(
                "The party is full!", ephemeral=True
            )
            return

        # Show ephemeral role selection
        await interaction.response.send_message(
            "Select your role:",
            view=RoleSelectView(self, interaction.user),
            ephemeral=True,
        )

    @discord.ui.button(label="Leave Party", style=discord.ButtonStyle.red)
    async def leave_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user not in self.members:
            await interaction.response.send_message(
                "You’re not in this party.", ephemeral=True
            )
            return

        for i, member in enumerate(self.members):
            if member == interaction.user:
                self.members[i] = None

        if all(member is None for member in self.members):
            if self.message:
                await self.message.delete()
            await interaction.response.send_message(
                "The party has been disbanded.", ephemeral=True
            )
            self.stop()  # stop the view so Discord can garbage-collect it
            return

        await self.update_public_message()
        await interaction.response.send_message("You left the party.", ephemeral=True)

    async def update_public_message(self):
        """Edits the public LFG message."""
        if not self.message:
            return
        embed, file = construct_embed(
            self.description,
            self.difficulty,
            self.members,
            self.heroes,
            self.creator.display_name,
            self.timer,
            self.id_m
        )
        await self.message.edit(embed=embed, view=self, attachments=[file])


open_lobbies = []
async def remove_lfg(lfg: LFGView):
    try:
        await lfg.message.delete()
    except:
        print(f'Could not delete message in {lfg}')

# --- Description Modal ---
class DescriptionModal(discord.ui.Modal, title="Set Party Description"):
    description = discord.ui.TextInput(
        label="Description",
        style=discord.TextStyle.paragraph,
        placeholder="Enter a brief description",
        required=False,
        max_length=200,
    )

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.description = (
            self.description.value or "No description provided."
        )
        await self.parent_view.update_setup_message(interaction)


# --- Setup View (ephemeral) ---
class LFGSetupView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=180)
        self.user = user
        self.description = "No description provided."
        self.difficulty = None
        self.role = None
        self.add_item(DifficultySelect(self))
        self.add_item(RoleSelect(self))
        self.add_item(LFGTimeSelect(self))
        self.timer = ""

    async def update_setup_message(self, interaction: discord.Interaction):
        text = (
            f"**Difficulty:** {self.difficulty}\n"
            f"**Description:** {self.description}\n"
            f"**Role:** {self.role}\n"
            f"**When?:** <t:{self.timer}:R>\n\n"
            "Press **Set Description** to edit or **Create Party** when ready."
        )
        await interaction.response.edit_message(content=text, view=self)

    # @discord.ui.button(label="Set Description ✏️", style=discord.ButtonStyle.secondary)
    # async def set_description_button(
    #     self, interaction: discord.Interaction, button: discord.ui.Button
    # ):
        # await interaction.response.send_modal(DescriptionModal(self))

    # @discord.ui.button(label="Create Party 🚀", style=discord.ButtonStyle.success)
    # async def create_party_button(
    #     self, interaction: discord.Interaction, button: discord.ui.Button
    # ):
    #     if not self.difficulty:
    #         await interaction.response.send_message(
    #             "Please select a difficulty.", ephemeral=True
    #         )
    #         return
    #     if not self.role:
    #         await interaction.response.send_message(
    #             "Please select your role.", ephemeral=True
    #         )
    #         return

    #     role_index = {"🛡 Tank": 0, "⚔ DPS1": 1, "⚔ DPS2": 2, "💚 Healer": 3}[self.role]
    #     view = LFGView(
    #         self.user, self.description, self.difficulty, role_index, self.mode
    #     )
    #     embed = construct_embed(
    #         self.description, self.difficulty, view.members, self.mode
    #     )

    #     await interaction.response.send_message(embed=embed, view=view)
    #     view.message = (
    #         await interaction.original_response()
    #     )  # store public message reference
    #     self.stop()


    @discord.ui.button(label="Create Party 🚀", style=discord.ButtonStyle.success)
    async def create_party_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        global current_id
        if not self.difficulty:
            await interaction.response.send_message(
                "Please select a difficulty.", ephemeral=True
            )
            return
        if not self.role:
            await interaction.response.send_message(
                "Please select your role.", ephemeral=True
            )
            return
        
        for i in range(0, len(open_lobbies)):
            if open_lobbies[i] != None and open_lobbies[i].creator == self.user:
                await remove_lfg(open_lobbies[i])
                open_lobbies[i] = None

        role_index = 0
        if "🛡" in self.role:
            role_index = 0
        elif "⚔" in self.role:
            role_index = 1
        else:
            role_index = 3
        
        hero = self.role[self.role.find(" "):].lower().strip()
        heroes = []
        for i in range(0, 4):
            heroes.append("None")
        heroes[role_index] = hero

        if self.timer == "":
            self.timer = int(datetime.now(timezone.utc).timestamp())
    
        view = LFGView(
            self.user, self.description, self.difficulty, role_index, self.timer
        )
        embed, file = construct_embed(
            self.description,
            self.difficulty,
            view.members,
            heroes,
            self.user.display_name,
            self.timer,
            current_id
        )

        message = await interaction.channel.send(embed=embed, view=view, file=file)
        view.message = message  # store the reference
        open_lobbies.append(view)
        self.stop()

class LFGTimeSelect(discord.ui.Select):
    def __init__(self, lfg_view: LFGSetupView):
        self.parent_view = lfg_view
        options = [
            discord.SelectOption(label="Right now", value="now"),
            discord.SelectOption(label="In ~1 hour", value="1h"),
            discord.SelectOption(label="In ~3 hours", value="3h"),
            discord.SelectOption(label="In ~6 hours", value="6h"),
            discord.SelectOption(label="Tomorrow", value="24h"),
            # discord.SelectOption(label="Custom date/time", value="custom"),
        ]
        super().__init__(placeholder="Select time...", options=options)

    async def callback(self, interaction: discord.Interaction):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)

        if self.values[0] == "now":
            timestamp = int(now.timestamp())
        elif self.values[0].endswith("h"):
            hours = int(self.values[0].replace("h", ""))
            timestamp = int((now + timedelta(hours=hours)).timestamp())
        # else:
        #     # You’ll need another modal for custom entry
        #     ...
        
        # Store the timestamp in your LFG object
        # self.parent_view.start_time = timestamp
        self.parent_view.timer = timestamp
        await self.parent_view.update_setup_message(interaction)
        await interaction.response.edit_message(content=f"Time set to <t:{timestamp}:f> (<t:{timestamp}:R>)")


# --- Difficulty Dropdown ---
class DifficultySelect(discord.ui.Select):
    def __init__(self, parent_view: LFGSetupView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label="🟢 Contender"),
            discord.SelectOption(label="🔵 Adept"),
            discord.SelectOption(label="🟣 Champion"),
            discord.SelectOption(label="🟡 Paragon"),
            discord.SelectOption(label="🔴 Eternal"),
        ]
        super().__init__(placeholder="Select Difficulty", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.difficulty = self.values[0]
        await self.parent_view.update_setup_message(interaction)


# --- Role Select for Setup ---
class RoleSelect(discord.ui.Select):
    def __init__(self, parent_view: LFGSetupView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label="🛡 Helena"),
            discord.SelectOption(label="🛡 Meiko"),
            discord.SelectOption(label="⚔ Tariq"),
            discord.SelectOption(label="⚔ Ardeos"),
            discord.SelectOption(label="⚔ Mara"),
            discord.SelectOption(label="⚔ Elarion"),
            discord.SelectOption(label="⚔ Rime"),
            discord.SelectOption(label="💚 Sylvie"),
            discord.SelectOption(label="💚 Vigour"),
        ]
        super().__init__(placeholder="Select Role", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.role = self.values[0]
        await self.parent_view.update_setup_message(interaction)


# --- Role Select View (for joining) ---
class RoleSelectView(discord.ui.View):
    def __init__(self, parent_view: LFGView, user: discord.User):
        super().__init__(timeout=60)
        self.parent_view = parent_view
        self.user = user
        self.add_item(RoleSelect2(self))

    async def finalize_selection(
        self, interaction: discord.Interaction, role_name: str
    ):
        for i, member in enumerate(self.parent_view.members):
            if member == interaction.user:
                self.parent_view.members[i] = None
                self.parent_view.heroes[i] = "None"

        role_index = 0
        if "🛡" in role_name:
            role_index = 0
        elif "⚔" in role_name:
            role_index = 1
            if self.parent_view.members[1] is not None:
                role_index = 2
        else:
            role_index = 3
        
        if self.parent_view.members[role_index] is not None:
            await interaction.response.edit_message(
                content="That role is already taken.", view=None
            )
            return

        self.parent_view.members[role_index] = self.user
        hero = role_name[role_name.find(" "):].lower().strip()
        self.parent_view.heroes[role_index] = hero
        await self.parent_view.update_public_message()

        await interaction.response.edit_message(
            content=f"You joined as **{role_name}**!", view=None
        )
        self.parent_view.last_update_time = datetime.now()
        if self.parent_view.creator != self.user:
            await notify_user(self.parent_view.creator, self.parent_view, f"{self.user.display_name} joined your party as {role_name}.")
        self.stop()


class RoleSelect2(discord.ui.Select):
    def __init__(self, parent_view: RoleSelectView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label="🛡 Helena"),
            discord.SelectOption(label="🛡 Meiko"),
            discord.SelectOption(label="⚔ Tariq"),
            discord.SelectOption(label="⚔ Ardeos"),
            discord.SelectOption(label="⚔ Mara"),
            discord.SelectOption(label="⚔ Elarion"),
            discord.SelectOption(label="⚔ Rime"),
            discord.SelectOption(label="💚 Sylvie"),
            discord.SelectOption(label="💚 Vigour"),
        ]
        super().__init__(placeholder="Select Role", options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.finalize_selection(interaction, self.values[0])


# --- Slash Command ---
@bot.tree.command(name="lfg", description="Create a Looking For Group party")
async def lfg(interaction: discord.Interaction):
    view = LFGSetupView(interaction.user)
    await interaction.response.send_message(
        "Configure your LFG party below:", view=view, ephemeral=True
    )

@bot.tree.command(name="lfg_mute", description="Mute LFG bot DMs")
async def lfg_mute(interaction: discord.Interaction):
    if interaction.user.display_name.strip() not in muted_people:
        muted_people.append(interaction.user.display_name.strip())
        with open("ignored.txt", "a+") as file:
            file.write(interaction.user.display_name.strip())
    
    
    await interaction.response.send_message("LFG bot will no longer send you DMs!", ephemeral=True)

@bot.tree.command(name="lfg_unmute", description="Enable DMs from the LFG bot")
async def lfg_unmute(interaction:discord.Interaction):
    if interaction.user.display_name.strip() in muted_people:
        muted_people.remove(interaction.user.display_name.strip())
        with open("ignored.txt", "r") as file:
            lines = file.readlines()
        with open("ignored.txt", "w") as file:
            for line in lines:
                if line.strip() != interaction.user.display_name.strip():
                    file.write(line)

    await interaction.response.send_message("LFG bot will send DMs again!", ephemeral=True)
    

# @bot.tree.command(
#     name="lfg_register", description="registers friend code for the lfg bot."
# )
# @app_commands.describe(friend_code="Friend code")
# async def lfg_register(interaction: discord.Interaction, friend_code: str):
#     user: discord.User = interaction.user
#     friend_codes[user.display_name] = friend_code
#     await interaction.response.send_message(
#         "Friend code registered, use command again to overwrite.", ephemeral=True
#     )

async def notify_user(user: discord.User, LFGView: LFGView, message: str):
    if user.display_name.strip() in muted_people:
        return

    try:
        await user.send(message)
    except Exception as err:
        print(f"Failed to send message {message}, to user {user.display_name}. {err}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.channel.id != CHANNEL_ID:
        return
    
    fellow_index = message.content.find("FELLOW")
    if fellow_index == -1:
        return
    end_index = message.content.find(" ", fellow_index)
    if end_index == -1:
        code = message.content[fellow_index:]
    else:
        code = message.content[fellow_index:end_index]
    friend_codes[message.author.display_name] = code
    print(f"{message.author.display_name}: {message.content}")

async def read_friend_code_history():
    channel = await bot.fetch_channel(CHANNEL_ID)
    if channel is None:
        print("Could not find the friend code channel")
        return

    messages = []
    async for message in channel.history(limit=None, oldest_first=True):
        fellow_index = message.content.find("FELLOW")
        if fellow_index == -1:
            continue
        end_index = message.content.find(" ", fellow_index)
        if end_index == -1:
            code = message.content[fellow_index:]
        else:
            code = message.content[fellow_index:end_index]
        friend_codes[message.author.display_name] = code
        print(f"{message.author.display_name}: {code}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synced.")
    await read_friend_code_history()
    hourly_task.start()

@tasks.loop(seconds=10)
async def hourly_task():
    now = datetime.now()
    for i in range(0, len(open_lobbies)):
        if open_lobbies[i] != None and (now - open_lobbies[i].last_update_time).total_seconds() / 3600 > 3:
            await remove_lfg(open_lobbies[i])
            open_lobbies[i] = None

bot_token = ""
with open(".env") as f:
    bot_token = f.readline().strip()
    CHANNEL_ID = int(f.readline().strip())

if not os.path.exists("ignored.txt"):
    open("ignored.txt", "w").close()  # create empty file

with open("ignored.txt", "r+") as f:
    for line in f:
        muted_people.append(line.strip())

bot.run(bot_token)
