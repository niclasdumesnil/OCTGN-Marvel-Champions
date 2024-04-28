#!/usr/bin/python
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------
# Welcome screen
# Highly inspired from Card Fighters' Clash OCTGN implementation
#---------------------------------------------------------------------------

def showWelcomeScreen(group = None, x = 0, y = 0):
    # On program started
    changeLog()
    welcomeScreenSetting = getSetting("welcomeScreen", True)
    if group is None:
        if not welcomeScreenSetting:
            return

    choiceList = ["Load a scenario", "Load a scenario (Fanmade)", "Load a hero (pre-built deck)", "Load a hero (o8d deck)", "Load a hero (marvelcdb url deck)", "Load a hero (Fanmade)", "Rulebook  ->", "Download card images  ->", "What's new ?", "Report an issue  ->"]
    colorsList = ["#6300a8"] * 2 + ["#004d99"] * 4 + ["#636363"] * 4
    buttons = ["Close", "Do not show again", "Always show"]
    msg = """Welcome to Marvel Champions : The Card Game\n
Here you will find useful information to get started with the game.
With great power comes great responsibility!"""
    choice = askChoice(msg, choiceList, colorsList, buttons)

    if choice == 0: return

    elif choice == -1: return

    elif choice == -2:
        setSetting("welcomeScreen", False)

    elif choice == -3:
        setSetting("welcomeScreen", True)

    elif choice == 1:
        loadVillain(table, x = 0, y = 0, setupType = "villain_setup")
        if deckNotLoaded(group, checkGroup = [c for c in me.Deck if not isEncounter([c])]):
            showWelcomeScreen()

    elif choice == 2:
        loadVillain(table, x = 0, y = 0, setupType = "fm_villain_setup")
        if deckNotLoaded(group, checkGroup = [c for c in me.Deck if not isEncounter([c])]):
            showWelcomeScreen()

    elif choice == 3:
        loadHero(table, x = 0, y = 0, askMethod = False, choice = 1, setupType = "hero_setup")

    elif choice == 4:
        loadHero(table, x = 0, y = 0, askMethod = False, choice = 2, setupType = "hero_setup")

    elif choice == 5:
        loadHero(table, x = 0, y = 0, askMethod = False, choice = 3, setupType = "hero_setup")

    elif choice == 6:
        loadFanmadeHero(table, x = 0, y = 0)

    elif choice == 7:
        openUrl(Website + "/rules-reference")
        showWelcomeScreen()

    elif choice == 8:
        openUrl(Website + "/imagepacks")
        showWelcomeScreen()

    elif choice == 9:
        showChangeLog()
        showWelcomeScreen()

    elif choice == 10:
        openUrl(Github)
        showWelcomeScreen()


#---------------------------------------------------------------------------
# Changelog screen
#---------------------------------------------------------------------------

def changeLog():
    mute()
    #### LOAD CHANGELOG
    v1, v2, v3, v4 = gameVersion.split('.')  ## split apart the game's version number
    v1 = int(v1) * 1000000
    v2 = int(v2) * 10000
    v3 = int(v3) * 100
    v4 = int(v4)
    currentVersion = v1 + v2 + v3 + v4  ## An integer interpretation of the version number, for comparisons later
    lastVersion = getSetting("lastVersion", convertToString(currentVersion - 1))  ## -1 is for players experiencing the system for the first time
    lastVersion = int(lastVersion)
    for log in sorted(changelog):  ## Sort the dictionary numerically
        if lastVersion < int(log):  ## Trigger a changelog for each update they haven't seen yet.
            stringVersion, date, text = changelog[log]
            updates = '\n\n- '.join(text)
            msg = "What's new in {} ({}):\n\n-{}".format(stringVersion, date, updates)
            askChoice(msg, [], [], ["Close"])
    setSetting("lastVersion", convertToString(currentVersion))  ## Store's the current version to a setting

def showChangeLog():
    mute()
    #### LOAD CHANGELOG
    v1, v2, v3, v4 = gameVersion.split('.')  ## split apart the game's version number
    v1 = int(v1) * 1000000
    v2 = int(v2) * 10000
    v3 = int(v3) * 100
    v4 = int(v4)
    currentVersion = v1 + v2 + v3 + v4  ## An integer interpretation of the version number, for comparisons later
    lastVersion = getSetting("lastVersion", convertToString(currentVersion - 1))  ## -1 is for players experiencing the system for the first time
    lastVersion = int(lastVersion)
    for log in sorted(changelog):  ## Sort the dictionary numerically
        if lastVersion == int(log):  ## Trigger a changelog for each update they haven't seen yet.
            stringVersion, date, text = changelog[log]
            updates = '\n\n- '.join(text)
            msg = "What's new in {} ({}):\n\n-{}".format(stringVersion, date, updates)
            askChoice(msg, [], [], ["Close"])


#---------------------------------------------------------------------------
# Card info screen
#---------------------------------------------------------------------------

def cardInfo(card, x = 0, y = 0):
    offset = (60 - len(card.name)) / 2
    msg = "{}{}".format(" " * offset, card.name)

    keyword = card.properties["Text"]
    if keyword:

        if re.search("Alliance", keyword):
            msg += """

ALLIANCE
When a player declares their intention to play an alliance card, any player(s) may help pay the costs for that card."""

        if re.search("Guard", keyword, re.IGNORECASE):
            msg += """

GUARD
While a minion with guard is engaged with a player, that player cannot attack the villain."""

        if re.search("Hinder", keyword):
            msg += """

HINDER X
When a player reveals a card with hinder X, that player places X threat on that card."""

        if re.search("Incite", keyword, re.IGNORECASE):
            msg += """

INCITE X
When a player reveals a card with incite X, that player places X threat on the main scheme."""

        if re.search("Overkill", keyword, re.IGNORECASE):
            msg += """

OVERKILL
Excess damage from attacks with overkill are dealt to the identity or villain."""

        if re.search("Patrol", keyword, re.IGNORECASE):
            msg += """

PATROL
While a minion with patrol is engaged with a player, that player cannot thwart the main scheme. """

        if re.search("Peril", keyword):
            msg += """

PERIL
While a player is resolving a card with peril, other players cannot help that player."""

        if re.search("Permanent", keyword):
            msg += """

PERMANENT
Cards with permanent cannot leave play."""

        if re.search("Piercing", keyword, re.IGNORECASE):
            msg += """

PIERCING
Attacks with piercing discard tough status cards from the attacked character before damage is dealt."""

        if re.search("Quickstrike", keyword, re.IGNORECASE):
            msg += """

QUICKSTRIKE
After this enemy engages a player, it immediately attacks that player if they are in hero form. """

        if re.search("Ranged", keyword, re.IGNORECASE):
            msg += """

RANGED
Attacks with ranged ignore retaliate."""

        if re.search("Requirement", keyword):
            msg += """

REQUIREMENT(RESOURCES)
A card with the requirement keyword cannot be played unless each resource of the specified type is spent while paying for that card’s cost."""

        if re.search("Restricted", keyword, re.IGNORECASE):
            msg += """

RESTRICTED
A player cannot control more than two restricted cards at a given time."""

        if re.search("Retaliate", keyword, re.IGNORECASE):
            msg += """

RETALIATE X
After a character with retaliate X is attacked, deal X damage to the attacker."""

        if re.search("Setup", keyword):
            msg += """

SETUP
Cards with setup start the game in play."""

        if re.search("Stalwart", keyword, re.IGNORECASE):
            msg += """

STALWART
Characters with Stalwart cannot be stunned or confused."""

        if re.search("Steady", keyword, re.IGNORECASE):
            msg += """

STEADY
A character with the steady keyword is not stunned or confused unless it has two stunned or confused status cards, respectively."""

        if re.search("Surge", keyword, re.IGNORECASE):
            msg += """

SURGE
After a player reveals a card with surge, that player reveals an additional encounter card."""

        if re.search("Team-Up", keyword):
            msg += """

TEAM-UP
Cards with team-up cannot be played unless both characters listed by the keyword are in play."""

        if re.search("Teamwork", keyword, re.IGNORECASE):
            msg += """

TEAMWORK (Trait)
After a minion with teamwork enters play and engages a player, if there is at least one other minion that shares the specified trait in play, each minion that shares the teamwork keyword with the same specified trait activates against the player it is engaged with."""

        if re.search("Temporary", keyword):
            msg += """

TEMPORARY
A card with temporary must be discarded from play at the end of the round."""

        if re.search("Toughness", keyword, re.IGNORECASE):
            msg += """

TOUGHNESS
When a character with toughness enters play, place a tough status card on it."""

        if re.search("Uses", keyword):
            msg += """

USES (X type)
When a card with uses enters play, place X all-purpose counters from the token pool on that card.
After the last all-purpose counter is removed from a card with uses (and the effect resolves), discard that card. """

        if re.search("Victory", keyword):
            msg += """

VICTORY
When a card with victory X is defeated, add it to the victory display."""

        if re.search("Villainous", keyword):
            msg += """

VILLAINOUS
When a minion with villainous activates, give it a boost card."""

    askChoice(msg, [], [], ["Close"])