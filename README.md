# Multipurpose Discord bot extensible using Discord.py's cogs with extra custom features.

## Installation instructions:
Requires Python 3.8 or newer.
Coming soon(tm)!

## Command reference:
### Base commands:
```
shutdown: Turn the bot off
    Botmaster required

ping: Ping/pong test

info: Bot info

status <Message>:
    Botmaster required
    Set the bot's "Playing" status to Message

blocklist <User> [blocklist=True]:
  Aliases = bl, block
  Botmaster required
  Add or remove User to/from the bot's blocklist
  Invoking with blocklist equal to false will remove User from blocklist, all true values will add User to the blocklist

logs [edits | deletes | channel]:
    MUST HAVE DISCORD ADMINISTRATOR PERMISSION
    Invoke without arguments to display current server's settings

    channel <Channel>:
        MUST HAVE DISCORD ADMINISTRATOR PERMISSION
        Set the message logging channel to Channel (TextChannel)

    edits <Enabled>:
        MUST HAVE DISCORD ADMINISTRATOR PERMISSION
        Set logging message edits to the logs channel to Enabled

    deletes <Enabled>:
        MUST HAVE DISCORD ADMINISTRATOR PERMISSION
        Set logging message deletes to the logs channel to Enabled

ghosts [enabled=True]:
    MUST HAVE DISCORD ADMINISTRATOR PERMISSION
    Set reporting of ghost pings (A message containing the mention of a user was deleted) on your server.

whois [Member]:
    Displays basic information about a member, including their join date, roles, and avatar.
    Invoke without arguments to display information about yourself.

```
### Account plugin
###### Create and manager user accounts on a per-server basis to control access to moderation commands
```
accounts [search | add | remove | update | genesis]:
    Aliases = accs
    Invoke without arguments to display current level if available

    search <Member>:
        Aliases = lookup, find
        Display Member's account level for the the current server

    add <Member> <Level>:
        Aliases = create, new
        Level 10 required
        Create a new account for Member at Level on the current server

    remove <Member>:
        Aliases = delete, destroy
        Level 10 required
        Remove the account of Member on the current server

    update <Member> <Level>:
        Aliases = change, modify
        Level 10 required
        Update the level of Member to Level on the current server

    genesis:
        MUST HAVE DISCORD ADMINISTRATOR PERMISSION
        Create yourself an account with the highest level (10) on the current server
```
### Plugin manager
###### Manage loaded plugins, and enable/disable them on a per-server basis
```
plugins [load | unload | enable | disable]:
    Aliases = pl, cogs
    Invoke without arguments to display currently loaded plugins

    load <Name>:
        Botmaster required
        Load the plugin Name (Do not include the .py extension)

    unload <Name>:
        Botmaster required
        Unload the plugin Name (Do not include the .py extension)

    reload <Name>:
        Botmaster required
        Shorthand for running `plugins unload Name` followed by `plugins load Name`

    enable <Name>:
        Level 10 required
        Enable the plugin Name on your server (Name will be the same as it displays in the loaded plugins list)

    disable <Name>:
        Level 10 required
        Disable the plugin Name on your server (Name will be the same as it displays in the loaded plugins list)
```
### Messages plugin
###### Move or crosspost messages to other channels
```
crosspost <Message> <Target>:
    Aliases = xpost, x-post
    Must be message OP or level 5
    Cross-post a Message to Target channel

move <Message> <Target>:
    Aliases = mv, ->
    Must be message OP or level 5
    Move a Message to Target channel
```
### Xkcd plugin
###### Get comics from xkcd
```
xkcd [random | number]:
    Invoke without arguments to display latest comic

    random:
        Random xkcd comic

    number <Number>:
        XKCD comic Number
```
### Inspirobot plugin
###### Generate inspirobot images
```
inspirobot:
    Aliases = ib, inspire
    Generates a new inspirational quote
```
### Roles plugin
###### Add user-assignable roles to your server
```
role [add | remove | admin]:
    Aliases = roles
    Invoke without arguments to display list of assignable roles

    add <Name>:
        Aliases = a, get, give, +
        Give yourself the role Name from the assignable roles list

    remove <Name>:
        Aliases = r, lose, take, -
        Remove from yourself the role Name from the assignable roles list

    admin [add | remove | react]:
        Level 10 required
        Running the command without arguments will show all server roles, including command roles and react roles.

    admin add <Role> <Description>:
        Level 10 required
        Add or update <Role> on the command assignable roles list.

    admin remove <Role>:
        Level 10 required
        Remove <Role> from the comand assignable roles list.

    admin react [add | remove]:
        Level 10 required
        Running the command without arguments will display all current reaction roles.

    admin react add <Message> <Role> <Description>:
        Level 10 required
        Add a new reaction-based <Role> to <Message> with <Description>
        <Message> should be a Discord message link, it might not work otherwise
        This will start a very quick interaction where you react to a message from the bot to set the reaction

    admin react remove <Message> <Role>:
        Level 10 required
        Remove a reaction-based <Role> from <Message>
        <Message> should be a Discord message link, it might not work otherwise
```
### Admin plugin
###### Various administration features such as warn, mute, kick, ban, and more
Note: For commands requiring length and span arguments, span will be the unit of time where length is the amount of those units.
Valid Span(s) are: second, seconds, minute, minutes, hour, hours, day, days, week, weeks, month, months, year, years
```
admin [log | role]:
    MUST HAVE SERVER ADMINISTRATOR PERMISSION
    Invoke without arguments to display current server settings

    log <Enabled> [Channel]:
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        Set whether to-channel logging is Enabled and set the log channel. If no channel is set the current channel will be used

    role <Role>:
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        Set the mute role that the mute/unmute commands will use

    warn <Target> <Length> <Span> [Reason]:
        Level 4 required
        Warn Target for Length Span(s) for Reason

    warns [Member]
        Invoke without arguments to view your own warnings
        Level 4 required to view Member's warns
        If Member is provided, display their warns

    mute <Target> <Length> <Span> [Reason]:
        Level 4 required
        Mute Target for Length Span(s) for Reason

    unmute <Target>:
        Level 4 required
        Unmute Target early

    kick <Target> [Reason]:
        Level 6 required
        Kick Target from the server for Reason

    softban <Target> <Purge> [Reason]:
        Level 7 required
        Softban (Ban then unban) Target from the server and delete their messages for Purge days for Reason

    tempban <Target> <Length> <Span> [Reason]:
        Level 8 required
        Temporarily ban Target for Length Span(s) for Reason

    ban <Target> <Purge> [Reason]:
        Level 8 required
        Ban Target from the server and delete their messages for Purge days for Reason

    purge [self | bot | all | member | role]:
        Purge messages

        self <Count>:
            purge messages from yourself within the last Count messages

        bot <Count>:
            Level 5 required
            purge messages from the bot within the last Count messages

        all <Count>:
            Level 5 required
            purge all of the last <Count> messages

        member <Target> <Count>:
            Level 5 required
            purge messages from Target within the last Count messages

        role <Role> <Count>:
            Level 5 required
            purge messages from Role within the last Count messages
```
### Groups plugin
###### Create temporary private groups with a voice and text channel
```
groups [create | invite]:
    Aliases = group, gr
    Invoke without arguments to view the groups you are currently part of

    create <Name> <Description>:
        Aliases = c, cr, new
        Create a new group. <Name> must have no spaces or special characters, and <Description> may include any utf-8 symbols.

    invite <Target> <Group>:
        Aliases = i, inv
        Invite <Target> to a <Group> you are part of.
```
### Custom plugin
###### Create custom commands for your server
```
custom <prefix | text | script>:
    Base command for managing custom commands

custom prefix [prefix]
    Running the command without the prefix argument will display the server's current prefix
    Including the prefix argument will set the server's prefix (Level 10 required)

custom text [create | remove]:
    Running the command without arguments will display available text commands

custom text create <Name> <Text>:
    Aliases = c, new, make, add
    Level 8 required
    Create a new custom text command <Name> with response <Text>

custom text remove <Name>:
    Aliases = r, del, delete
    Remove the custom text command <Name>

custom script [create | remove]:
    Running the command without arguments will display available script commands

custom script create <Prefix> <Text>:
    Aliases = c, new, make, add
    Level 8 required
    Create a new script response to <Prefix> with response <Text>. Supports script replacers:
      - !{id}            - The Discord ID snowflake of the user running the command
      - !{name}          - The name of the user running the command
      - !{discriminator} - The discriminator of the user running the command
      - !{tag}           - The Name#tag (i.e. User#1141) of the user running the command
      - !{mention}       - A mention of the user running the command

custom script remove <Prefix>:
    Aliases = r, del, delete
    Level 8 required
    Remove the custom script response to <Prefix>
```

## Development

Coding standards:
  - 90 char line length limits
  - Double-quote for strings (Even single character strings)
  - Double-hash section header comments
  - No punctuation for single line comments
  - Punctuation in multi-line hash comments and all docstring comments
  - Imports in order of lowest to highest level

Filesystem standards:
  - Config files in JSON stored in /config
  - Database files stored in /db and backed up in /db/backup
  - All databases must use SQLite using SqliteDict and use .sql extension
  - All base extension cogs must go in the root folder
  - All addon plugins (cogs) must go in the /plugins folder
  - Any official plugin must add requirements to the requirements.txt file
    - All official plugins must only use resources provided in direct code or through pip