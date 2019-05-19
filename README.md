# Adventure!
Default prefix: `*`

Python `3.6.x` - `3.7.x`

Discord.py `1.1.1`

## All new PvP system!
After rigorous testing, v2 of the Player vs Player system has been released.

With the new system, you may choose a demon from your compendium and pit them in a
battle against another user.

Each demon has their own unique stats, weakness / resistances and move sets!
Try them all!

### Commands

Check the bottom of the page for a full list of commands.

# Yet another RPG based bot for Discord!
This bot is designed around the idea that you get to explore various regions around the world!

Travel to strange landmarks and explore the area...

Encounter strange and powerful enemies.

Fight to the death\* against your friends!

And fill in the Compendium! There are over 200\*\* enemies to record into the compendium!

### Support
You can join the support server via [this link](https://discord.gg/hkweDCD)

---

### Commands
Here is a reference of every command Adventure has.

`<>` - Required argument 

`[]` - Optional argument 

> `*help [command/module]`

Views help on a specific command or module.
Or shows a list of all modules if no args are present.

### Unsorted
Commands that don't have a category.
> `*fight <@user>`

Begins a battle against another user.
Choose a demon from your compendium and fight!
The winner of the battle will receive 5,000 G.
Each demon has a unique moveset, stats and type resistances.

NOTE: This command can and may break. If it does, please join the support server and we will try to help from there.


### Misc
Commands that don't fit into any other category.

> `*info`

Views basic information about Adventure!.

> `*epic`

Searches for the most epic message in the channel history.

> `*git`

Gives you the most recent commit to Adventure!'s source code.

> `*avatar [@user]`

Shows a users avatar, or your own if omitted.

> `*ping`

Checks my connection time to Discord's servers.

> `*say <message...>`

Repeats exactly what you say.

> `*source [command]`

Sends the link to my source code, or a snippet of a command if supplied.

> `*tip`

Gives you a random hint about something.

> `*invite`

Sends two links to invite me to your server.
One contains all recommended permissions for Adventure!,
the other is minimal (0) permissions.

> `*support`

Sends the instant invite link to the support server.

> `*prefix`

Base prefix command, will view all prefixes if no subcommand is specified.
Each command requires `Manage Server` permissions.
>> `*prefix add <prefixes...>`

Adds a valid prefix to the server, if not already used.
>> `*prefix remove <prefixes...>`

Removes the specified prefixes.
   
> `*vote`

Sends the link to vote for Adventure! on DiscordBots.org.
Voting gives free rewards, and even more on weekends!

> `*patreon`

Sends the link to my patreon, where you can donate to the development of Adventure!
Donating will give you special perks, be sure to DM me proof that you've donated so I can arrange the perks.

> `*recover`

If your player hasn't loaded, this command will try to force reload it.
If you do not have a player, this command will not work.

### Supporter
Commands that may only be used by people who have donated to my patreon.
You can donate to me at this link: https://www.patreon.com/xua_yraili

> `*customreset`

Resets your custom background and text colour to the default.

> `*custombg <url>`

Upload an image to be used as a background image in *profile.
The image will be resized to 499w x 370h

> `*textcol <colour>`

Colour can be a hexdigit, name or digit value.
Will change the colour of the text in *profile to your colour.

### Players
Commands that relate to general players, such as you!

> `*create`

Creates a new player. This won't work if you already own a player.
If you have created a player but it hasn't been loaded, try `*recover` instead.

> `*delete`

Deletes your player. You don't want to do that right? :'[

> `*travel <map>`

Tells your player to travel to the specified map.
You can view available maps with `*maps`
If you have already explored the map, the travel time will be decreased.

> `*explore`

Begins exploring the map you are on.
You cannot explore a map twice, but when you do explore a map, you may then start encountering enemies.

> `*status`

Checks your players current status, which could be Idling, Travelling or Exploring.
This will also tell you how long is left until 

> `*rename`

Renames your player. That's about it.

> `*give <@user> <amount>`

Gives the specified user some gold from your balance.
You cannot give negative amounts, nor can you give more than you have.

> `*profile [@user]`

Views information about you or a specified user.
This includes coins, current status, level and more.

> `*daily`

Claims your daily Experience reward.
This is one of two ways to gain free experience. The other is by voting for Adventure! on DiscordBots.org

> `*speedup`

Uses gold you have collected, speeds up your current action.
This is more costly if the time remaining is higher.

> `leaderboard [count=20]`

Views the top `count` players on the leaderboard in your server.
This is ordered by total demons recorded in the compendium.

>> `*leaderboard experience [count=20]`

Views the top `count` players on the leaderboard in your server.
This is ordered by total Experience points.

>> `*leaderboard global [count=20]`

Views the top `count` players on the leaderboard globally.
This is ordered by total demons recorded in the compendium.

> `*compendium`

Views all your captured demons so far.

### Enemies
All enemy related commands are in this category.

> `*megami <demon name>`

Returns a link to the Megami Tensei wiki for the demon specified.

> `*encounter`

Tries to find an encounter for your current map.
This will not work if there are no encounters in your area (it's a safe map),
or you have not explored the area yet.

### Maps
Mostly a helper module to make sure the maps are running properly.

> `*maps`

Views all maps that you can travel to from your position.
If you want to view all maps completely, use `*maps all`.

>> `*maps explored`

Views all maps that you have explored on your journey.

>> `*maps all`

Views every map regardless if you can travel to it.

> `*quicktravel <map>`

For a price, will quick travel your player to a specified map.
This can get quite expensive.