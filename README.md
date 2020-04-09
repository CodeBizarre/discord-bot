# Multipurpose Discord bot mainly made for my personal server

Coding standards:
  - 90 char line length limits
  - Double-quote for strings (Even single character strings)
  - Double-hash section header comments
  - No punctuation for single line comments
  - Punctuation in multi-line hash comments and all docstring comments
  - Imports in order of lowest to highest level, with a line break between stdlib and 3rd party

Filesystem standards:
  - Config files in JSON stored in /config
  - Database files stored in /db and backed up in /db/backup
  - All databases must use SQLite using SqliteDict and use .sql extension
  - All base extension cogs must go in the root folder
  - All addon plugins (cogs) must go in the /plugins folder
  - Any official plugin must add requirements to the requirements.txt file
    - All official plugins must only use resources provided in direct code or through pip

## Command reference:
### Base commands:
```
shutdown: Turn the bot off
    Botmaster required
ping: Ping/pong test
echo <Message>: Have the bot repeat Message
info: Bot info
status <Message>:
    Set the bot's "Playing" status to Message
blacklist <User> [blacklist=True]:
  Aliases = bl, block
  Botmaster required
  Add or remove User to/from the bot's blacklist
  Invoking with blacklist equal to false will remove User from blacklist, all true values will add User to the blacklist
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
### Account plugin commands
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
### Messages plugin commands
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
### XKCD plugin commands
```
xkcd [random | number]:
    Invoke without arguments to display latest comic

    random:
        Random xkcd comic

    number <Number>:
        XKCD comic Number
```
### Inspirobot plugin commands
```
inspirobot:
    Aliases = ib, inspire
    Generates a new inspirational quote
```
### Roles plugin commands
```
role [get | lose | add | remove]:
    Aliases = roles
    Invoke without arguments to display list of assignable roles

    get <Name>:
        Aliases = g
        Get the role Name from the assignable roles list
    lose <Name>:
        Aliases = l
        Lose the role Name from the assignable roles list
    add <Role> <Description>:
        Aliases = a
        Level 10 required
        Add Role with Description to the assignable roles list, note that the bot cannot assign a role higher than its own highest role even with the administrator permission.
    remove <Role>L
        Aliases = r
        Level 10 required
        Remove Role from the assignable roles list
```
### Admin plugin commands
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