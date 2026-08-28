import clr
clr.AddReference('System.Web.Extensions')
from System.Web.Script.Serialization import JavaScriptSerializer

#------------------------------------------------------------
# 'Load Hero' event
#------------------------------------------------------------

def loadFanmadeHero(group, x = 0, y = 0):
    mute()
    loadHero(group, x, y, True, 0, "fm_hero_setup")

def loadHero(group, x = 0, y = 0, askMethod = True, choice = 0, setupType = "hero_setup"):
    mute()
    if not deckNotLoaded(group, checkGroup = [c for c in me.Deck if not isEncounter([c])]):
        msg = """Cannot generate a deck: You already have cards loaded.\n
Reset the game in order to generate a new deck."""
        askChoice(msg, [], [], ["Close"])
        return

    if setupType == "fm_hero_setup":
        fanmade = True
        cardSelected = dialogBox_Setup(me.piles["Setup"], setupType, None, "Select your Hero", "Select your Hero :", min = 1, max = 1, isFanmade = fanmade)
        if cardSelected is None: return
        heroSet = cardSelected[0].Owner
        heroName = cardSelected[0].Name
        me.setGlobalVariable("heroPlayed", heroSet)
    else:
        fanmade = False
    update()

    # Choose where to take other aspect cards from
    if askMethod:
        if fanmade:
            choice = askChoice("Select source for other aspect cards:", ["A downloaded deck (.o8d file)", "A marvelcdb deck (URL)", "A Universal Pre-Built deck"])
            if choice != 0:
                choice = choice + 1
        else:
            choice = askChoice("Select source for other aspect cards:", ["An out of the box deck", "A downloaded deck (.o8d file)", "A marvelcdb deck (URL)", "A Universal Pre-Built deck"])

    if choice == 0: return

    if choice == 1:
        cardSelected = dialogBox_Setup(me.piles["Setup"], setupType, None, "Select your Hero", "Select your Hero :", min = 1, max = 1, isFanmade = fanmade)
        if cardSelected is None: return
        heroSet = cardSelected[0].Owner
        heroName = cardSelected[0].Name
        me.setGlobalVariable("heroPlayed", heroSet)
        aspectCardsList = createCards(me.Deck, pre_built[heroSet].keys(), pre_built[heroSet])
        deleteCards(me.piles["Setup"])

    if choice == 2:
        filename = openFileDlg('', '', 'o8d Files|*.o8d')
        if filename == "":
            whisper("No file chosen. Script will end here. Try to Load your hero again.")
            return

        aspectCardsList = o8dLoad(filename, fanmade)
        if not fanmade:
            cardSelected = me.piles["Setup"].top()
            heroSet = cardSelected.Owner
            heroName = cardSelected.Name
            me.setGlobalVariable("heroPlayed", heroSet)
        deleteCards(me.piles["Setup"])

    if choice == 3:
        url = askString("Please enter the URL of the deck you wish to load.", "")
        if url == None: return
        if not "view/" in url:
            whisper("Error: Invalid URL.")
            return

        aspectCardsList = RemoteCallBlocker.createAPICards(url, False)
        if not fanmade:
            cardSelected = me.piles["Setup"].top()
            heroSet = cardSelected.Owner
            heroName = cardSelected.Name
            me.setGlobalVariable("heroPlayed", heroSet)
        deleteCards(me.piles["Setup"])

    if choice == 4:
        if not fanmade:
            cardSelected = dialogBox_Setup(me.piles["Setup"], setupType, None, "Select your Hero", "Select your Hero :", min = 1, max = 1, isFanmade = fanmade)
            if cardSelected is None: return
            heroSet = cardSelected[0].Owner
            heroName = cardSelected[0].Name
            me.setGlobalVariable("heroPlayed", heroSet)
        universal_prebuilt_List = sorted(universal_prebuilt.keys())
        prebuilt_Choice = askChoice("What Universal Pre-Built deck do you want to load?", universal_prebuilt_List)
        aspectCardsList = RemoteCallBlocker.createAPICards("https://marvelcdb.com/deck/view/{}".format(universal_prebuilt[universal_prebuilt_List[prebuilt_Choice-1]]), True)

    # Set all player variables
    pList = list(JavaScriptSerializer().DeserializeObject(getGlobalVariable("playerList")))
    pList.append(me._id)
    setGlobalVariable("playerList", str(pList))
    heroesPlayed = list(JavaScriptSerializer().DeserializeObject(getGlobalVariable("heroesPlayed")))
    heroesPlayed.append(heroSet)
    setGlobalVariable("heroesPlayed", str(heroesPlayed))

    # Load hero cards
    heroCards = createCardsFromSet(me.Deck, heroSet, heroName, False)
    nemesisCards = createCardsFromSet(me.Nemesis, heroSet + "_nemesis", heroName + "'s Nemesis", False)

    # Change Owner for all cards
    changeOwner(heroCards, heroSet)
    changeOwner(aspectCardsList, heroSet)
    if nemesisCards is not None:
        changeOwner(nemesisCards, heroSet)

    # Check for linked cards  
    for c in me.piles["Deck"]:
        if c.CardNumber in linkedCard.keys():
            for lnkC in linkedCard[c.CardNumber]:
                cardModel = queryCard({"CardNumber":lnkC}, True)
                if len(cardModel) == 0:
                    notify("Card not found in octgn database. Code from marvelcdb url : {}.".format(cardid))
                    continue 
                cards = me.piles["Removed"].create(cardModel[0], 1)            

    heroSetup()
    checkSetup()

def heroSetup(group=table, x = 0, y = 0):

    id = myID() # This ensures we have a unique ID based on our position in the setup order
    heroCount = countHeros(me)
    heroPlayed = me.getGlobalVariable("heroPlayed")

    # Find any Permanent cards
    #permanents = filter(lambda card: "Permanent" in card.Keywords or "Permanent." in card.Text, me.deck)

    # Move Hero to the table
    newHero = False
    hero = filter(lambda card: card.Type == "hero", me.Deck)
    if hero:
        heroCount += 1
        newHero = True
        heroCard = hero[0]
        heroCard.moveToTable(playerX(id),tableLocations['hero'][1])
        heroCard.alternate = 'b'
        me.counters['Max HP'].value = num(heroCard.HP)
        me.counters['Default Card Draw'].value = num(heroCard.HandSize)
        notify("{} places his Hero on the table".format(me))

    if newHero:
        shuffle(me.deck)

        #------------------------------------------------------------
        # Specific Hero setup
        #------------------------------------------------------------

        # Doctor Strange
        if heroPlayed == 'doctor_strange':
            createCardsFromSet(me.piles['Special'], "invocation", "Invocation", False)
            showGroup(me.piles['Special'], True)
            showGroup(me.piles['Special Discard'], False)
            me.piles['Special'].visibility = "all"

        # Spectrum
        if heroPlayed == 'spectrum':
            for c in filter(lambda card: card.Type == "upgrade", me.Deck):
                if c.CardNumber == "21002" or c.CardNumber == "21003" or c.CardNumber == "21004":
                    c.moveTo(me.piles['Special'])
            showGroup(me.piles['Special'], False)
            me.piles['Special'].visibility = "all"

        # Valkyrie
        if heroPlayed == 'valk':
            for c in filter(lambda card: card.CardNumber == "25002", me.Deck):
                c.moveTo(me.piles['Special'])
            showGroup(me.piles['Special'], False)
            me.piles['Special'].visibility = "all"

        # Vision
        if heroPlayed == 'vision':
            # me.counters['Default Card Draw'].value += 1
            for c in filter(lambda card: card.CardNumber == "26002a", me.Deck):
                c.moveToTable(playerX(id)+70,tableLocations['hero'][1])

        # Ironheart
        if heroPlayed == 'ironheart':
            showGroup(me.piles['Special'], False)
            me.piles['Special'].visibility = "all"

        # SP//dr
        if heroPlayed == 'spdr':
            for c in me.piles['Special']:
                c.moveToTable(playerX(id)+70,tableLocations['hero'][1])

        # Shadowcat
        if heroPlayed == 'shadowcat':
            for c in filter(lambda card: card.CardNumber == "32031a", me.Deck):
                c.moveToTable(playerX(id)+70,tableLocations['hero'][1])

        # Phoenix
        if heroPlayed == 'phoenix':
            for c in filter(lambda card: card.CardNumber == "34002a", me.Deck):
                c.moveToTable(playerX(id)+70,tableLocations['hero'][1])
                c.markers[AllPurposeMarker] = 4

        # Wolverine
        if heroPlayed == 'wolverine':
            for c in filter(lambda card: card.CardNumber == "35002", me.Deck):
                c.moveToTable(playerX(id)+70,tableLocations['hero'][1])

        # Storm
        if heroPlayed == 'storm':
            createCardsFromSet(me.piles['Special'], "weather", "Weather", False)
            showGroup(me.piles['Special'], False)
            me.piles['Special'].visibility = "all"

        # Rogue
        if heroPlayed == 'rogue':
            for c in filter(lambda card: card.CardNumber == "38002", me.Deck):
                c.moveTo(me.piles['Special'])
            showGroup(me.piles['Special'], False)
            me.piles['Special'].visibility = "all"

        # Psylocke
        if heroPlayed == 'psylocke':
            i = 1
            for c in filter(lambda card: card.CardNumber == "41002a", me.Special):
                c.moveToTable(playerX(id)+(70*i),tableLocations['hero'][1])
                i += 1

        # X-23
        if heroPlayed == 'x23':
            for c in filter(lambda card: card.CardNumber == "43002", me.Deck):
                c.moveToTable(playerX(id)+70,tableLocations['hero'][1])

        # Iceman
        if heroPlayed == 'iceman':
            createCardsFromSet(me.piles['Special'], "frostbite", "Frostbite", False)
            showGroup(me.piles['Special'], True)
            me.piles['Special'].visibility = "all"

        # Nick Fury
        if heroPlayed == 'nick_fury':
            for c in filter(lambda card: card.CardNumber == "50035a", me.Deck):
                c.moveToTable(playerX(id)+70,tableLocations['hero'][1])

        # Wonder Man
        if heroPlayed == 'wonder_man':
            for c in filter(lambda card: card.CardNumber == "58002", me.Deck):
                c.moveToTable(playerX(id)+70,tableLocations['hero'][1])

        # Hercules
        if heroPlayed == 'hercules':
            createCardsFromSet(me.piles['Special'], "hercules_labor_deck", " Hercules Labor Deck", False)
            createCardsFromSet(me.piles['Special Discard'], "hercules_gift_deck", " Hercules Gift Deck", False)
            showGroup(me.piles['Special'], True)
            showGroup(me.piles['Special Discard'], True)
            me.piles['Special Discard'].visibility = "none"

        #------------------------------------------------------------
        # Specific Fanmade Hero setup
        #------------------------------------------------------------

        # Luke Cage (by Rainy)
        if heroPlayed == 'luke_cage_by_rainy':
            for c in filter(lambda card: card.CardNumber == "203601b", table):
                tough(c)

        #------------------------------------------------------------
        # moveToTable Hero setup cards
        #------------------------------------------------------------
        shift = 0
        for c in me.Deck:
            if lookForSetup(c):
                c.moveToTable(playerX(id)+70+shift,tableLocations['hero'][1])
                shift += 70

        #------------------------------------------------------------
        # Cards that declare their own setup location in the set xml
        #------------------------------------------------------------
        # Some cards must be put into play at setup even though their own text
        # holds no "Setup" keyword, because the instruction sits on the identity
        # instead: Jessica Jones' alter-ego reads "Setup: Put the Alias
        # Investigations support into play", while the support itself only reads
        # "Permanent.". lookForSetup() scans the deck and can never match those,
        # which is why every such hero so far needed its own hard-coded block
        # above, with the card number written in the engine.
        # Letting the card state its own intent - same spirit as the existing
        # DefaultSetupPile / DefaultDiscardPile properties - means a new pack
        # ships with its set.xml alone, without patching the engine.
        # The shift is shared with the "Setup" loop above so the cards line up
        # next to the hero instead of stacking on each other.
        # Heroes already covered by a hard-coded block must NOT carry the
        # property, or their card would be put into play twice.
        # Origine : Merlin - generic replacement for the per-hero permanent
        # setup blocks, introduced with the Jessica Jones pack.
        for c in me.Deck:
            if c.hasProperty("DefaultSetupLocation") and c.properties["DefaultSetupLocation"].strip().lower() == "table":
                c.moveToTable(playerX(id)+70+shift,tableLocations['hero'][1])
                shift += 70
                notify("{} puts {} into play (setup).".format(me, c))
        # "Starting." cards go to the player's hand
        #------------------------------------------------------------
        # Done here, during hero setup, so the cards are already in hand when
        # startGame() runs: it draws maxHandSize(p) - countHandSize(p), so the
        # player ends up at their normal hand size, holding these cards.
        # Origine : Merlin - keyword introduced with Fear No Evil.
        for c in me.Deck:
            if lookForStarting(c):
                c.moveTo(me.hand)
                notify("{} adds {} to their starting hand (Starting.)".format(me, c))
        # A few heroes start with a side deck of their own: Doctor Strange's
        # Invocation, Storm's Weather, Iceman's Frostbite, Hercules' Labor and
        # Gift decks, and now Daredevil's SENSE deck. Each needed a hard-coded
        # block above, although createCardsFromSet() is already generic - it
        # only takes an Owner. The identity can name it instead.
        # Value is a comma separated list of set Owners, each optionally
        # followed by ":<pile>" when it must not land in the Special pile:
        # Hercules needs that, having two side decks for one hero.
        # The deck is shuffled and the pile opened to everyone, as the five
        # hard-coded blocks do - a SENSE deck is played from the top, so its
        # cards have to be readable.
        # WARNING: keep this property ALONE. Declaring HeroSideDeckShuffle and
        # HeroSideDeckVisibility beside it, carried by no card, reproducibly
        # broke the card database: the game threw "object reference not set"
        # on any group iteration, so loadHero() died on an empty me.Deck
        # before any setup ran. Removing them fixed it, twice. The mechanism
        # is not understood - DefaultSetupPile has the same shape and is fine.
        # Origine : Merlin - generic replacement for the per-hero side deck
        # blocks, introduced with Daredevil's SENSE deck (Fear No Evil).
        if hero and heroCard.hasProperty("HeroSideDeck"):
            for entry in heroCard.properties["HeroSideDeck"].split(","):
                entry = entry.strip()
                if not entry:
                    continue
                if ":" in entry:
                    deckOwner, pileName = entry.split(":", 1)
                    deckOwner, pileName = deckOwner.strip(), pileName.strip()
                else:
                    deckOwner, pileName = entry, "Special"
                deckName = deckOwner.replace("_", " ").title()
                createCardsFromSet(me.piles[pileName], deckOwner, deckName, False)
                showGroup(me.piles[pileName], True)
                me.piles[pileName].visibility = "all"

def countHeros(p):
    heros = 0
    for card in table:
        if card.controller == p and (card.Type == "hero" or card.Type == "alter_ego"):
            heros += 1
    return heros

#------------------------------------------------------------
# 'Load Hero' specific functions
#------------------------------------------------------------
def o8dLoadAsDict(o8d):
    """
    Load an .o8d file and build a global dict where keys are sections. It will then look like:
    {
        section_id_1: {
            "section": the section name,
            "shared": boolean True/False,
            "cards": {
                "card_id": qty,
                "card_id": qty,
            }
        },
        section_id_2: {
            "section": the section name,
            "shared": boolean True/False,
            "cards": {
                "card_id": qty,
            }
        },
        ...
    }
    where section_id is the concatenation of section name and value of shared (as we can have section
    with same names in both shared and not shared piles)
    """
    with open(o8d, "rt") as f:
        lines = f.readlines()

    full_dict = {}
    current_section = ""
    for line in lines:
        if line.strip().startswith("<section"):
            name_matches = re.search('name="([a-zA-Z_]+)"', line, re.IGNORECASE)
            shared_matches = re.search('shared="([a-zA-Z]+)"', line, re.IGNORECASE)
            shared = False
            if shared_matches:
                shared = shared_matches.group(1) == "True"
            if name_matches:
                section = name_matches.group(1)
                section_id = section + "_" + str(shared)
                full_dict[section_id] = {"section": section, "shared": shared, "cards": {}}
                current_section = section_id
        if line.strip().startswith("<card"):
            matches = re.search('<card qty="(\d+)" id="([a-zA-Z0-9-]+)"', line, re.IGNORECASE)
            if matches:
                if matches.group(1) is not None and matches.group(2) is not None:
                    qty = int(matches.group(1))
                    card_id = matches.group(2)
                    full_dict[current_section]["cards"][card_id] = qty
    return full_dict

def o8dLoad(o8d, fanmade = False):
    """
    Load a local .o8d file
    Decks downloaded from marvelcdb have only one section named "Cards" with shared="False", so we can directly grab cards from this section
    """
    full_dict = o8dLoadAsDict(o8d)

    all_cards = []

    isAspectCard = False
    for card_id, qty in full_dict["Cards_False"]["cards"].items():
        cards = me.Deck.create(card_id, qty)
        if qty == 1:
            if cards is None:
                notify("{} card(s) not found in octgn database. Code from marvelcdb o8d : {}.".format(qty, card_id))
                continue            
            if cards.Type == 'hero':
                if not fanmade:
                    setupCardModel = queryCard({"Type":"hero_setup", "Owner":cards.Owner}, True)
                    setupCard = me.Setup.create(setupCardModel[0], 1)
            isAspectCard = cards.Owner == ""
            if isAspectCard:
                all_cards.append(cards)
            else:
                cards.delete()
        else:
            if len(cards) == 0:
                notify("{} card(s) not found in octgn database. Code from marvelcdb o8d : {}.".format(qty, card_id))
                continue   
            if cards[0].Type == 'hero':
                if not fanmade:
                    setupCardModel = queryCard({"Type":"hero_setup", "Owner":cards[0].Owner}, True)
                    setupCard = me.Setup.create(setupCardModel[0], 1)
            isAspectCard = cards[0].Owner == ""
            if isAspectCard:
                all_cards.extend(cards)
            else:
                [c.delete() for c in cards]
    return all_cards

def changeOwner(cards, hero_id):
    """
    Change Owner property of a given list of cards if Owner is unknown (or aspect card).
    """
    for card in cards:
        if card.Owner is None or card.Owner in ["", "basic", "justice", "leadership", "protection", "aggression"]:
            card.Owner = hero_id

class RemoteCallBlocker:
    """Methods in this class cannot be remote called because calling them requires using the '.' character, which isn't allowed in remote calls."""
    @staticmethod
    def createAPICards(url, fanmade = False):
        """
        Create the deck by loading cards from a marvelcdb URL.
        This function can load the whole deck or only cards that do not belong to the Hero (in this case, parameters 'filter'
        and 'new_owner' must be specified)
        """
        notify("Looking {} for deck.".format(url))
        all_cards = []

        protocol = url.split("://")[0]
        if "marvelcdb.com/" in str(url):
            webadress = "marvelcdb.com"
        else:
            webadress = url.split("://")[1].split("/")[0]

        deckid = url.split("view/")[1].split("/")[0]
        if "decklist/" in str(url):
            data, code = webRead("{}://{}/api/public/decklist/{}".format(protocol, webadress, deckid))
        elif "deck/" in str(url):
            data, code = webRead("{}://{}/api/public/deck/{}".format(protocol, webadress, deckid))
        if code != 200:
            whisper("Error retrieving online deck data, please try again.")
            return
        try:
            deckname = JavaScriptSerializer().DeserializeObject(data)["hero_name"]
            deck = JavaScriptSerializer().DeserializeObject(data)["slots"]
            hero_id = JavaScriptSerializer().DeserializeObject(data)["hero_code"]
            if not fanmade:
                heroCards = queryCard({"Type":"hero", "CardNumber":hero_id}, True)
                heroCard = me.piles["Setup"].create(heroCards[0], 1)
                setupCardModel = queryCard({"Type":"hero_setup", "Owner":heroCard.Owner}, True)
                if len(setupCardModel) == 0:
                    setupCardModel = queryCard({"Type":"fm_hero_setup", "Owner":heroCard.Owner}, True)
                setupCard = me.Setup.create(setupCardModel[0], 1)
                heroCard.delete()
            chars_to_remove = ['[',']']
            rx = '[' + re.escape(''.join(chars_to_remove)) + ']'
            for id in deck:
                line = re.sub(rx,'',str(id))
                line = line.split(',')
                cardid = line[0]
                qty = int(line[1].strip())
                cardModel = queryCard({"CardNumber":cardid}, True)
                if len(cardModel) == 0:
                    notify("Card not found in octgn database. Code from marvelcdb url : {}.".format(cardid))
                    continue 
                cards = me.Deck.create(cardModel[0], qty)
                if qty == 1:
                    isAspectCard = cards.Owner == ""
                    if isAspectCard:
                        all_cards.append(cards)
                    else:
                        cards.delete()
                else:
                    isAspectCard = cards[0].Owner == ""
                    if isAspectCard:
                        all_cards.extend(cards)
                    else:
                        [c.delete() for c in cards]
            return all_cards
        except ValueError:
            whisper("Error retrieving online deck data, please try again. If you are trying to load a non published deck make sure you have edited your account to select 'Share Your Decks'")