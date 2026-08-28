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

def loadVillain(group, x = 0, y = 0, setupType = "villain_setup"):
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
    cardSelected = dialogBox_Setup(setupPile(), setupType, None, "Which villain would you like to defeat ?", "Select Scenario :", min = 1, max = 1, isFanmade = fanmade)
    if cardSelected is None:
        return
    villainSet = cardSelected[0].Owner
    villainName = cardSelected[0].Name
    setGlobalVariable("villainSetup", villainName)
    nbModular = cardSelected[0].nbModular
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
    if not loadDifficulty(): return #Difficulty need 'villainSetup' GlobalVariable to be set.
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
    if not loadEncounter(encounterDeck(), nbModular): return
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


def loadDifficulty():
    mute()
    vName = getGlobalVariable("villainSetup")
    gameDifficulty = getGlobalVariable("difficulty")

    x = tableLocations['environment'][0] - 90
    y = tableLocations['environment'][1]

    if vName == 'The Wrecking Crew':
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