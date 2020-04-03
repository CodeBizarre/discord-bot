# Multipurpose Discord bot mainly made for my personal server

Coding standards:
  - 90 char line length limits
  - Double-quote for strings (Even single character strings)
  - Double-hash section header comments
  - No punctuation for single line comments
  - Punctuation in multi-line hash comments and all doctstring comments
  - Imports in order of lowest to highest level, with a line break between stdlib and 3rd party

Filesystem standards:
  - Config files in JSON stored in /config
  - Database files stored in /db and backed up in /db/backup
  - All databases must use UnQLite, SQL is a bannable offense
  - All base plugins (cogs) must go in the root folder
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