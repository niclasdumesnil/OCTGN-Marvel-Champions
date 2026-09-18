import clr
clr.AddReference('System.Web.Extensions')
from System.Web.Script.Serialization import JavaScriptSerializer

#!/usr/bin/python
# -*- coding: utf-8 -*-
#------------------------------------------------------------
# 'Load Villain' event
#------------------------------------------------------------

def loadFanmadeVillain(group, x = 0, y = 0, setupType = "fm_villain_setup"):
    mute()
    loadVillain(group, x = 0, y = 0, setupType = "fm_villain_setup")

def loadVillain(group, x = 0, y = 0, setupType = "villain_setup", mission = None):
    """
    mission: set codes read from an mc4db mission code (see loadScenarioByCode).
    When given, the three questions of the regular flow - which scenario, which
    difficulty, which modular sets - are answered by the code instead of by the
    player, and everything else below is unchanged.
    Origine : Merlin - chargement d'un scenario par code mission mc4db (2026).
    """
    mute()
    villainName = ''

    if me._id != 1:
        msg = """You're not the game host\n
Only the host is allowed to load a scenario."""
        askChoice(msg, [], [], ["Close"])
        return

    if not deckNotLoaded(group, 0, 0, villainDeck()):
        msg = """Cannot generate a deck: You already have cards loaded.\n
Reset the game in order to generate a new deck."""
        askChoice(msg, [], [], ["Close"])
        return

    # Choose Villain and set Villain global variables.
    if setupType == "fm_villain_setup":
        fanmade = True
    else:
        fanmade = False
    update()
    # A mission code names its scenario: the setup card is looked up by Owner
    # rather than picked in the dialog, and whether the pack is fan-made is read
    # on that card instead of on the menu entry the player came through.
    # Origine : Merlin - chargement par code mission (2026).
    if mission is not None:
        cardSelected = missionScenarioCard(mission)
        if cardSelected is None:
            return
        fanmade = (cardSelected[0].Type == "fm_villain_setup")
    else:
        cardSelected = dialogBox_Setup(setupPile(), setupType, None, "Which villain would you like to defeat ?", "Select Scenario :", min = 1, max = 1, isFanmade = fanmade)
        if cardSelected is None:
            return
    villainSet = cardSelected[0].Owner
    villainName = cardSelected[0].Name
    setGlobalVariable("villainSetup", villainName)
    # Read like the two properties just below, which already guard themselves.
    # A setup card that carries no nbModular handed an empty string to the
    # global variable, and the int() conversion below (loadEncounter call)
    # threw a raw ValueError in the player's face, with nothing set up. It
    # happens on any scenario whose setup card omits the property - a leader
    # has no main scheme to state one. Absent means "no modular set", which
    # loadEncounter() already treats as nothing to ask.
    # Origine : Merlin - constate en jeu sur les premiers sets de leader (2026).
    if cardSelected[0].hasProperty("nbModular"):
        nbModular = cardSelected[0].nbModular
    else:
        nbModular = 0
    setGlobalVariable("nbModular", nbModular)
    if cardSelected[0].hasProperty("recommendedModular"):
        setGlobalVariable("recommendedModular", cardSelected[0].recommendedModular)
    if cardSelected[0].hasProperty("CW_Side"):
        setGlobalVariable("CW_Side", cardSelected[0].CW_Side)

    #------------------------------------------------------------
    # Underling villain, asked for right after the scenario
    #------------------------------------------------------------
    # Fear No Evil splits the scenario from the villain: five scenarios carry the
    # main scheme but no villain, and are played against one of five 'underling'
    # villains, which have no main scheme of their own. The scenario says so in its
    # Contents: 'Chosen [[Underling]] villain (see rulebook p. 5).', which the set
    # xml carries as nbUnderling. A classic scenario brings its own villain, has no
    # such mention, and is left untouched.
    # Asked BEFORE the Setup pile is emptied below, and the chosen set is remembered
    # by name so it can be created once the villain cards are in.
    # isFanmade=True only skips the 'Release order / Alphabetical' question: five
    # names do not need a sorting choice.
    # Origine : Merlin - structure introduced with Fear No Evil.
    underlingSets = []
    if cardSelected[0].hasProperty("nbUnderling"):
        nbUnderling = num(cardSelected[0].nbUnderling)
        if nbUnderling > 0:
            underlingSelected = dialogBox_Setup(setupPile(), "underling_setup", None,
                                                "Which underling villain will you face ?",
                                                "Select your Underling villain :",
                                                min = nbUnderling, max = nbUnderling, isFanmade = True)
            if underlingSelected is None: return
            for c in underlingSelected:
                underlingSets.append([c.Owner, c.Name])

    # Delete cards in Setup pile, choose Difficulty and load villain Cards.
    deleteCards(setupPile())
    if not loadDifficulty(mission): return #Difficulty need 'villainSetup' GlobalVariable to be set.
    createCardsFromSet(encounterDeck(), villainSet, villainName, True)
    # The underling's own cards: they carry DefaultSetupPile, so createCardsFromSet
    # files them into the Villain pile by itself.
    for underlingSet in underlingSets:
        createCardsFromSet(encounterDeck(), underlingSet[0], underlingSet[1], True)
    update()

    # Load mandatory modulars for the scenario.
    if cardSelected[0].hasProperty("mandatoryModular"):
        mandatoryDict = cardSelected[0].mandatoryModular
        mandatoryDict = mandatoryDict.replace("True", "true").replace("False", "false")
        mandatoryDict = dict(JavaScriptSerializer().DeserializeObject(mandatoryDict))
        for k, i in mandatoryDict.items():
            setName = i[0]
            pile = shared.piles[i[1]]
            toShuffle = i[2]
            createCardsFromSet(pile, k, setName, True)
            showGroup(pile, toShuffle)

    # Load other modulars then setup Scenario.
    nbModular = int(getGlobalVariable("nbModular"))
    if not loadEncounter(encounterDeck(), nbModular, mission): return
    campaignEncounter(villainSet)
    update()

    # Setup Scenario
    if fanmade:
        scenarioSetup_fm()
    else:
        scenarioSetup()
    getSetupCards()
    notify('{} loaded {}, Good Luck!'.format(me, villainName))
    checkSetup()


def loadDifficulty(mission = None):
    mute()
    vName = getGlobalVariable("villainSetup")
    gameDifficulty = getGlobalVariable("difficulty")

    x = tableLocations['environment'][0] - 90
    y = tableLocations['environment'][1]

    if vName == 'The Wrecking Crew':
        # This scenario has no difficulty SET, only a question. A mission code
        # answers it by carrying an expert set code or not.
        # Origine : Merlin - chargement par code mission (2026).
        if mission is not None:
            if mission["expert"]:
                setGlobalVariable("difficulty", "1")
            return True
        choice = askChoice("What difficulty would you like to play at?", ["Standard", "Expert"])
        if choice == 0:
            deleteAllSharedCards()
            return
        if choice == 2:
            setGlobalVariable("difficulty", "1")
        return True

    else:
        if vName == 'Defense Tower' or vName == 'Sinister Six' or vName == 'Four Horsemen':
            x = 0
            y = 0

        # The mission code already says which difficulty sets are in play; the
        # loop below is left untouched, including its "exp" test that raises the
        # difficulty global. Origine : Merlin - chargement par code mission (2026).
        if mission is not None:
            cardsSelected = missionDifficultyCards(mission)
        else:
            cardsSelected = dialogBox_Setup(setupPile(), "difficulty_setup", None, "Difficulty selection", "Which set would you like to use ?", min = 0, max = 50, isFanmade = True)

        for card in cardsSelected:
            createCardsFromSet(encounterDeck(), card.Owner, card.Name, True)
            if card.Owner[0:3] == "exp":
                setGlobalVariable("difficulty", "1")
                gameDifficulty = getGlobalVariable("difficulty")
        update()
        
        EnvCard = sorted(filter(lambda card: card.CardNumber == "24049a", encounterDeck()))
        if len(EnvCard) != 0:
            EnvCard[0].moveToTable(x, y) # Do not override other environment cards from scenario (if any)
            x = x - 90
            if gameDifficulty == "1":
                EnvCard[0].alternate = 'b'

        EnvCard = sorted(filter(lambda card: card.CardNumber == "45075a", encounterDeck()))
        if len(EnvCard) != 0:
            EnvCard[0].moveToTable(x, y) # Do not override other environment cards from scenario (if any)

        deleteCards(setupPile())
        return True

def getSetupCards():
    shift = 0
    for c in encounterAndDiscardDeck():
        if lookForSetup(c):
            # A campaign REWARD carrying "Setup." is not a scenario setup
            # card: it belongs to the player who earned it in an earlier
            # scenario, and only if the table plays the campaign at all.
            # Posing it here would hand it out in every game, campaign or not.
            # File it in the Campaign pile instead, next to the other campaign
            # cards (campaignEncounter() in loadModular.py) - so it also leaves
            # the encounter deck, where it could otherwise be drawn as an
            # encounter card mid-game.
            # Safety net only: a correctly tagged pack carries
            # DefaultSetupPile="Campaign" on such a card, which files it before
            # this function ever sees it. It still catches the packs that
            # predate that rule - Fantastic Four and Web of Deceit both keep
            # campaign rewards inside a MODULAR set, so those do reach the
            # encounter deck today.
            # Both factions are checked because the corpus uses both: campaign
            # rewards are tagged "campaign" (33 cards over 6 packs, the
            # convention), and a pack may still mistag one as "hero" - which is
            # exactly how Fear No Evil's Typhoid Mary ally was found in play.
            # Never fires on an encounter-faction card, so the scenario setup
            # cards this function exists for are untouched. Checked over the
            # 122 sets of the repo: no card outside those campaign rewards
            # matches - Stop the Presses!' Daily Bugle supports are hero
            # faction too, but carry no "Setup." and stay in the encounter deck
            # where the scenario code filters them.
            # Origine : Merlin - cartes de campagne de Fear No Evil (2026).
            if c.Faction == "campaign" or c.Faction == "hero":
                c.moveTo(campaignDeck())
                continue
            c.moveToTable(0 + shift, tableLocations['villain'][1] + 100)
            shift += 20

def deleteAllSharedCards():
    for pl in shared.piles:
        deleteCards(shared.piles[pl])

#------------------------------------------------------------
# 'Load Scenario (mc4db mission code)' event
#------------------------------------------------------------
# mc4db gives every scenario configuration a 12-character mission code, already
# used by its own free-play tab and by the Tabletop Simulator importer. That code
# is enough to set a table up here: it names the villain set, the modular sets
# and the difficulty sets - exactly what the three questions of loadVillain()
# ask the player for.
#
# The endpoint is the LIGHT lookup (set codes, no cards), and those codes ARE the
# OCTGN set Owners: the generator derives Owner from set_code, so there is no
# translation table to write and none to keep in sync.
#
# Nothing is loaded before every set has been checked against the installed
# collection: a half-built table would leave the host guessing which pack is
# missing.
# Origine : Merlin - chargement d'un scenario par code mission mc4db (2026).
#
# The live site comes first; the development instance is tried next, exactly as
# FANMADE_DECK_HOSTS does for fan-made decks. A mission code only exists once
# someone has opened that scenario on the site that issued it, so a code minted
# on a local instance is a 404 on the live one - which is what a code typed
# during development looks like, and it cost a test run to find out.
MC4DB_MISSION_HOSTS = [
    "https://mc4db.merlindumesnil.net",
    "http://localhost:4000",
    "http://127.0.0.1:4000",
]

def loadScenarioByCode(group, x = 0, y = 0):
    mute()
    if me._id != 1:
        msg = """You're not the game host\n
Only the host is allowed to load a scenario."""
        askChoice(msg, [], [], ["Close"])
        return

    code = askString("Enter the mc4db mission code of the scenario:", "")
    if code is None:
        return
    code = code.strip()
    if code == "":
        return

    mission = fetchMissionSets(code)
    if mission is None:
        return

    missing = missionMissingSets(mission)
    if len(missing) > 0:
        whisper("This mission needs {} set(s) that are not installed: {}.".format(len(missing), ", ".join(missing)))
        whisper("Nothing was loaded. Install the missing pack(s), then try the code again.")
        return

    loadVillain(group, x, y, mission = mission)

def fetchMissionSets(code):
    """
    Reads the set codes of a mission code. Returns a dict, or None with a
    message to the host when the code is unknown or the site unreachable.
    Origine : Merlin - chargement par code mission (2026).
    """
    notify("Looking up mission code {}.".format(code))
    data = None
    lastStatus = 0
    for host in MC4DB_MISSION_HOSTS:
        data, status = webRead("{}/api/public/scenario-uuid/{}".format(host, code))
        if status == 200:
            break
        lastStatus = status
        data = None
    if data is None:
        if lastStatus == 404:
            whisper("Mission code {} is unknown on mc4db.".format(code))
        else:
            whisper("Could not reach mc4db to read the mission code (status {}).".format(lastStatus))
        return None
    try:
        apiData = JavaScriptSerializer().DeserializeObject(data)
        mission = {
            "code": code,
            "villain": missionValue(apiData, "villain_set_code"),
            "modulars": [],
            "standard": missionValue(apiData, "standard_set_code"),
            "expert": missionValue(apiData, "expert_set_code"),
            "setCards": {},
            "missing": [],
        }
        # One card code per set, used to find a set again when this collection
        # names it differently (see resolveMissionOwners).
        try:
            probes = apiData["set_cards"]
            # The deserializer hands back a .NET dictionary, which does not
            # iterate like a Python one; both forms are tried rather than
            # assumed.
            try:
                probeKeys = list(probes.Keys)
            except:
                probeKeys = list(probes.keys())
            for setCode in probeKeys:
                mission["setCards"][str(setCode)] = str(probes[setCode])
        except:
            pass
        rawModulars = []
        if "modular_set_codes" in apiData and apiData["modular_set_codes"] is not None:
            for setCode in apiData["modular_set_codes"]:
                if setCode:
                    rawModulars.append(str(setCode))
        # The API lists the difficulty sets among the modular codes AS WELL as in
        # their own fields: loading both lists as-is would create those cards
        # twice. They are taken out of the modular list here, and recognised by
        # their code when the site does not name them separately - the same
        # reading loadDifficulty() already does on Owner ("exp...").
        # Origine : Merlin - constate sur le code mission de Klaw (2026).
        for setCode in rawModulars:
            if not isDifficultySetCode(setCode):
                mission["modulars"].append(setCode)
            elif setCode[0:6] == "expert" and mission["expert"] == "":
                mission["expert"] = setCode
            elif setCode[0:8] == "standard" and mission["standard"] == "":
                mission["standard"] = setCode
    except:
        whisper("Unexpected answer from mc4db for mission code {}.".format(code))
        return None

    if mission["villain"] == "":
        whisper("Mission code {} carries no scenario.".format(code))
        return None
    resolveMissionOwners(mission)
    return mission

def resolveMissionOwners(mission):
    """
    Turns mc4db set codes into the Owners this collection actually uses.

    They are the same for everything the generator produces - Owner is derived
    from set_code - but a handful of official sets predate that and kept
    historical names: mc4db's `infiltrate_the_museum` is `collector1` here. So
    rather than maintaining a table of aliases, a set that answers nothing by
    Owner is looked up again through ONE OF ITS CARDS: card numbers are the same
    on both sides (verified on 16070-16074), and the card carries the Owner this
    collection wants.
    Origine : Merlin - chargement par code mission (2026).
    """
    mission["villain"] = resolveSetOwner(mission["villain"], mission)
    for key in ("standard", "expert"):
        if mission[key] != "":
            mission[key] = resolveSetOwner(mission[key], mission)
    resolved = []
    for setCode in mission["modulars"]:
        resolved.append(resolveSetOwner(setCode, mission))
    mission["modulars"] = resolved

def resolveSetOwner(setCode, mission):
    """
    The Owner to use for a set code, unchanged when it already matches one.
    Notes down the codes this collection knows nothing about as it goes, so the
    availability check does not have to ask the same questions all over again.
    """
    if setCode == "":
        return setCode
    if len(queryCard({"Owner": setCode}, True)) > 0:
        return setCode
    if setCode not in mission["setCards"]:
        mission["missing"].append(setCode)
        return setCode
    cards = queryCard({"CardNumber": mission["setCards"][setCode]}, True)
    if len(cards) == 0:
        mission["missing"].append(setCode)
        return setCode
    owner = ""
    tempPile(True).create(cards[0], 1)
    update()
    for c in tempPile(True):
        owner = c.Owner
    deleteCards(tempPile(True))
    if owner == "" or owner == setCode:
        mission["missing"].append(setCode)
        return setCode
    notify("Set {} is known here as {}.".format(setCode, owner))
    return owner

def isDifficultySetCode(setCode):
    """
    A standard/expert set, told from its code. Same convention loadDifficulty()
    relies on when it raises the difficulty global on an Owner starting with
    "exp". Origine : Merlin - chargement par code mission (2026).
    """
    return setCode[0:8] == "standard" or setCode[0:6] == "expert"

def missionValue(apiData, key):
    """A field the API may not carry yet reads as an empty string, not a crash."""
    try:
        if key in apiData and apiData[key] is not None:
            return str(apiData[key])
    except:
        pass
    return ""

def missionMissingSets(mission):
    """
    Set codes the installed collection knows nothing about, collected while the
    Owners were being resolved - asking again would repeat the same queryCard
    calls for every set of the mission.
    Origine : Merlin - chargement par code mission (2026).
    """
    return mission["missing"]

def missionSetupCards(setCodes, setupTypes):
    """
    Setup cards of the given sets, as card objects ready to be read.

    The Setup pile is NOT a standing list of every setup card: dialogBox_Setup()
    fills it from queryCard() when it opens and empties it when it closes, so
    reading the pile outside a dialog finds nothing - which is what made a set
    that was perfectly installed look like it carried no setup card. The two
    steps it does are repeated here, minus the dialog.
    Origine : Merlin - chargement par code mission (2026).
    """
    for setCode in setCodes:
        for setupType in setupTypes:
            for model in queryCard({"Type": setupType, "Owner": setCode}, True):
                setupPile().create(model, 1)
    update()
    return filter(lambda c: c.Owner in setCodes, setupPile())

def missionScenarioCard(mission):
    """
    The scenario's own setup card, the one the dialog would have returned. Both
    the official and the fan-made type are accepted: a mission code does not say
    which flow it belongs to, and loadVillain() reads it back off this card.
    Origine : Merlin - chargement par code mission (2026).
    """
    cards = missionSetupCards([mission["villain"]], ("villain_setup", "fm_villain_setup"))
    if len(cards) == 0:
        whisper("The scenario set {} is installed but carries no setup card.".format(mission["villain"]))
        return None
    return [cards[0]]

def missionDifficultyCards(mission):
    """The difficulty setup cards named by the mission code, standard and expert."""
    codes = []
    for key in ("standard", "expert"):
        if mission[key] != "":
            codes.append(mission[key])
    if len(codes) == 0:
        whisper("This mission code carries no difficulty set; none was loaded.")
    return missionSetupCards(codes, ("difficulty_setup",))
