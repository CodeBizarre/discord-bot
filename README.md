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
ping: Ping/pong test
info: Bot info
blacklist <User> [doom=True]:
  Aliases = bl, block
  Add or remove a user to/from the bot's blacklist
  Invoking with doom equal to false will remove the user, all true values will add the user to the blacklist
plugins [load | unload]:
    Aliases = pl, cogs
    Invoke without arguments to display currently loaded plugins

    load <Name>:
        Load the plugin with the given Name (Do not include the .py extension)

    unload <Name>:
        Unload the plugin with the given Name (Do not include the .py extension)

    reload <Name>:
        Shorthand for running `plugins unload` followed by `plugins load`

    enable <Name>:
        Enable the plugin with the given Name on your server (Name will be the same as it displays in the loaded plugins list)

    disable <Name>:
        Disable the plugin with the given Name on your server (Name will be the same as it displays in the loaded plugins list)
```
### Account plugin commands
```
accounts [search | add | remove | update | genesis]:
    Aliases = accs
    Invoke without arguments to display current level if available

    search <Member>:
        Aliases = lookup, find
        Display the account level for the chosen user on the current server

    add <Member> <Level>:
        Aliases = create, new
        Create a new account for the chosen user with the chosen level on the current server

    remove <Member>:
        Aliases = delete, destroy
        Remove the account of the chosen user on the current server

    update <Member> <Level>:
        Aliases = change, modify
        Update the level of the chosen user with the chosen level on the current server

    genesis:
        MUST HAVE DISCORD ADMINISTRATOR PERMISSION ON THE CURRENT SERVER
        Create yourself an account with the highest level (4) on the current server
```
### XKCD plugin commands
```
xkcd [random | number]:
    Invoke without arguments to display latest comic

    random:
        Random xkcd comic

    number <Number>:
        XKCD comic <Number>
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
        Get the role <Name> from the assignable roles list
    lose <Name>:
        Aliases = l
        Lose the role <Name> from the assignable roles list
    add <Role> <Description>:
        Aliases = a
        Add a Role with the Description to the assignable roles list, note that the bot cannot assign a role higher than its own highest role even with the administrator permission.
```
### Admin plugin commands
Note: For commands requiring length and span arguments, span will be the unit of time where length is the amount of those units.
Valid Span(s) are: second, seconds, minute, minutes, hour, hours, day, days, week, weeks, month, months, year, years
```
admin [log | role]:
    Invoke without arguments to display current server settings

    log <Enabled> [Channel]:
        Set whether to-channel logging is Enabled and set the log channel. If no channel is set the current channel will be used

    role <Role>:
        Set the mute role that the mute/unmute commands will use

    warn <Target> <Length> <Span> [Reason]:
        Warn Target for Length Span(s) for Reason

    warns <Member>
        List the currently active warnings for Member

    mute <Target> <Length> <Span> [Reason]:
        Mute Target for Length Span(s) for Reason

    unmute <Target>:
        Unmute Target early

    kick <Target> [Reason]:
        Kick Target from the server for Reason

    softban <Target> <Purge> [Reason]:
        Softban (Ban then unban) Target from the server and delete their messages for Purge days for Reason

    tempban <Target> <Length> <Span> [Reason]:
        Temporarily ban Target for Length Span(s) for Reason

    ban <Target> <Purge> [Reason]:
        Ban Target from the server and delete their messages for Purge days for Reason

    purge [self | bot | all | member | role]:
        Purge messages

        self <Count>:
            purge messages from yourself within the last Count messages

        bot <Count>:
            purge messages from the bot within the last Count messages

        all <Count>:
            purge all of the last <Count> messages

        member <Target> <Count>:
            purge messages from Target within the last Count messages

        role <Role> <Count>:
            purge messages from Role within the last Count messages
```