#
# Routines for writing out updated decks based on either the player piles or the shared piles
#
from datetime import datetime as dt
import collections
import sys
import clr
clr.AddReference('System.Web.Extensions')
from System.Web.Script.Serialization import JavaScriptSerializer as json #since .net 3.5?


#------------------------------------------------------------
# Save/load tracing
#------------------------------------------------------------
# A failed "Load Table State" leaves nothing to work from: OCTGN reports script
# errors in the chat window only, they scroll away with the game log, and
# nothing reaches the disk. When this switch is on, every step of saveTable()
# and loadTable() announces itself before it runs and is appended to a log file
# sitting next to the save file, so the step that failed can be identified
# afterwards instead of being guessed.
# Kept False here: the official module keeps its exact current behaviour. The
# beta build turns it on by rewriting this single line (tools/beta/build.py).
# The engine's own "Toggle Debug" menu (showDebug in actions.py) also turns it
# on, so a tester can trace a load without a dedicated build.
# Origine : Merlin - diagnostic du chargement de sauvegarde impossible (2026).
DEBUG_SAVELOAD = False

_traceFilePath = None

def traceEnabled():
    """
    Tracing is on for a beta build, or for anyone who turned the engine debug on.
    Origine : Merlin - instrumentation save/load.
    """
    return DEBUG_SAVELOAD or showDebug

def openTraceFile(saveFilePath):
    """
    Point the trace log at "<save file>.debug.log" for the operation to come.
    The log sits next to the save file, which is by construction a folder the
    player can write to and can find again.
    Origine : Merlin - instrumentation save/load.
    """
    global _traceFilePath
    _traceFilePath = None
    if not traceEnabled():
        return
    try:
        path = saveFilePath + ".debug.log"
        with open(path, 'a') as f:
            f.write("\n=== {} ===\n".format(dt.now().strftime("%Y-%m-%d %H:%M:%S")))
        _traceFilePath = path
    except:
        # A trace that cannot be written must never break the operation it watches.
        _traceFilePath = None

def traceSaveLoad(message):
    """
    Log one step of the save/load routines, when tracing is on.
    Whispering is not enough on its own: these routines run under mute(), and a
    crash takes the chat with it - hence the file.
    Origine : Merlin - instrumentation save/load.
    """
    if not traceEnabled():
        return
    line = "[save/load {}] {}".format(dt.now().strftime("%H:%M:%S"), message)
    whisper(line)
    if _traceFilePath is None:
        return
    try:
        with open(_traceFilePath, 'a') as f:
            f.write(line + "\n")
    except:
        pass

def traceFailure(step):
    """
    Report the exception being handled, naming the step that raised it.
    IronPython inside OCTGN ships only a handful of pure-python modules and the
    traceback module is not one of them, so the announced step name is what
    locates the error.
    Origine : Merlin - instrumentation save/load.
    """
    info = sys.exc_info()
    traceSaveLoad("FAILED during '{}' -> {}".format(step, repr(info[1])))
    notify("Save/load failed during '{}': {}".format(step, info[1]))


def saveManual(group, x=0, y=0):
    phase = ""
    if currentPhase()[1] == 1:
        saveTable(phase)
    if currentPhase()[1] != 1:
        notify("You can save only when current phase is \"Hero Phase\"")

def saveTable(phase):
    mute()
    if phase == "":
        if 1 != askChoice('You are about to SAVE the table states including the elements on the table, shared deck and each player\'s hand and piles.\nThis option should be execute on the a game host.'
            , ['I am the Host!', 'I am not...'], ['#dd3737', '#d0d0d0']):
            return

        if not getLock():
            whisper("Others players are saving, please try manual saving again")
            return

    try:
        tab = {"table":[], "shared": {}, 'counters': None, "players": None, "globalVariable": {}, "phase": None}

        # loop and retrieve cards from the table
        for card in table:
            tab['table'].append(serializeCard(card))

        # loop and retrieve item from the shared decks
        for p in shared.piles :
            if p == 'Trash':
                continue
            for card in shared.piles[p]:
                if p not in tab['shared']:
                    tab['shared'].update({p: []})
                tab['shared'][p].append(serializeCard(card))

        tab['counters'] = serializeCounters(shared.counters)

        # loop each player
        players = sorted(getPlayers(), key=lambda x: x._id, reverse=False)
        tab['players'] = [serializePlayer(pl) for pl in players]

        # Global Variable
        tab['globalVariable'] = serializeGlobalVariable()

        # Phase
        tab['phase'] = getGlobalVariable("phase")

        if phase == "":
            filename = saveFileDlg('', '', 'Json Files|*.json')
        else:
            with open("data.path", 'r') as f:
                dir = f.readline()
                filename = dir + "\\GameDatabase\\055c536f-adba-4bc2-acbf-9aefb9756046\\" + "AutoSave.json"

        if filename == None:
            return

        # Record what goes into the file, so a load that fails later can be
        # compared with it. The lock is reported on purpose: a manual save runs
        # while its author holds it, so it is written non-empty into the file
        # and restored as such by loadTable().
        # Origine : Merlin - diagnostic du chargement de sauvegarde impossible (2026).
        openTraceFile(filename)
        traceSaveLoad("save by {} (player id {}), mode '{}'".format(me, me._id, phase or "manual"))
        traceSaveLoad("file {}".format(filename))
        traceSaveLoad("{} card(s) on table, {} shared pile(s), {} player(s), phase '{}', lock '{}'".format(
            len(tab['table']), len(tab['shared']), len(tab['players']), tab['phase'], tab['globalVariable']['lock']))

        with open(filename, 'w+') as f:
            f.write(json().Serialize(tab))

        if phase == "":
            notify("Table state saves to {}".format(filename))

    finally:
        clearLock()

def loadManual(group, x=0, y=0):
    phase = ""
    loadTable(phase)

def restoreSave(group, x=0, y=0):
    phase = "restore"
    loadTable(phase)

def loadTable(phase):
    mute()

    if 1 != askChoice('You are about to LOAD the table states including the elements on the table, shared deck and each player\'s hand and piles.\nThis option should be execute on the a game host.'
        , ['I am the Host!', 'I am not...'], ['#dd3737', '#d0d0d0']):
        return

    if not getLock():
        whisper("Others players are locking the table, please try again")
        return

    try:
        if phase == "":
            filename = openFileDlg('', '', 'Json Files|*.json')
        else:
            with open("data.path", 'r') as f:
                dir = f.readline()
                filename = dir + "\\GameDatabase\\055c536f-adba-4bc2-acbf-9aefb9756046\\" + "AutoSave.json"
                notify("Restore Table state saves to last phase")

        if not filename:
            return

        # deleteChoice = askChoice("Do you want to delete all cards on table and in each piles ?", ["Yes", "No"])
        # if deleteChoice == 1:
            # for pl in players:
                # for p in pl.piles:
                    # [c.delete() for c in pl.piles[p]]
                    # [c.delete() for c in pl.hand]
            # [c.delete() for c in table]
            # for p in shared.piles:
                # [c.delete() for c in shared.piles[p]]

        #------------------------------------------------------------
        # Traced load
        #------------------------------------------------------------
        # Every step names itself before it runs and the whole body is guarded,
        # so the last line written to the trace is the step that failed. The
        # state read before starting (turn number, phase, player count) is what
        # tells a restored save apart from the game it is restored into.
        # Origine : Merlin - diagnostic du chargement de sauvegarde impossible (2026).
        openTraceFile(filename)
        traceSaveLoad("load by {} (player id {}), mode '{}'".format(me, me._id, phase or "manual"))
        traceSaveLoad("file {}".format(filename))
        traceSaveLoad("state before load: turn {}, phase {}, {} player(s), lock '{}'".format(
            turnNumber(), currentPhase(), len(getPlayers()), getGlobalVariable("lock")))

        step = "reading the save file"
        try:
            with open(filename, 'r') as f:
                tab = json().DeserializeObject(f.read())
            traceSaveLoad("file parsed, sections: {}".format(", ".join([k for k in tab.Keys])))

            step = "table cards"
            traceSaveLoad("1/6 table: {} card(s)".format(len(tab['table'])))
            deserializeTable(tab['table'])

            step = "shared piles"
            if tab['shared'] is not None and len(tab['shared']) > 0:
                for k in tab['shared'].Keys:
                    if k not in shared.piles:
                        traceSaveLoad("2/6 shared pile '{}' unknown to this version, skipped".format(k))
                        continue
                    traceSaveLoad("2/6 shared pile '{}': {} card(s)".format(k, len(tab['shared'][k])))
                    deserializePile(tab['shared'][k], shared.piles[k])

            step = "shared counters"
            if tab['counters'] is not None and len(tab['counters']) > 0:
                traceSaveLoad("3/6 shared counters: {}".format(", ".join([k for k in tab['counters'].Keys])))
                deserializeCounters(tab['counters'], shared)

            step = "players"
            if tab['players'] is not None and len(tab['players']) > 0:
                # deserializePlayer() drops a saved player whose id is absent
                # from the current game without a word: say it instead, it means
                # the save is being restored into a differently seated game.
                # Origine : Merlin - instrumentation save/load.
                currentIds = [p._id for p in getPlayers()]
                for player in tab['players']:
                    traceSaveLoad("4/6 player id {} ('{}'){}".format(
                        player['_id'], player['name'],
                        "" if player['_id'] in currentIds else " -> ABSENT from this game, will be skipped"))
                    deserializePlayer(player)

            step = "global variables"
            if tab['globalVariable'] is not None and len(tab['globalVariable']) > 0:
                for k in tab['globalVariable'].Keys:
                    traceSaveLoad("5/6 global '{}' = '{}'".format(k, tab['globalVariable'][k]))
                    deserializeGlobalVariable(k, tab['globalVariable'][k])

            step = "phase"
            if tab['phase'] is not None and len(tab['phase']) > 0:
                # advanceGame() branches on turnNumber(), and on a game that was
                # only just created it is still 0 - which is not the branch a
                # restored game needs. Report the values it is about to read.
                # Origine : Merlin - instrumentation save/load.
                traceSaveLoad("6/6 phase '{}', turnNumber {}, firstPlayer '{}', playerList '{}'".format(
                    tab['phase'], turnNumber(), getGlobalVariable("firstPlayer"), getGlobalVariable("playerList")))
                advanceGame()
                if tab['phase'] == "Villain Phase":
                    traceSaveLoad("6/6 setPhase(2) asked by {} (active player is {})".format(me, getActivePlayer()))
                    setPhase(2)

            traceSaveLoad("load completed")

        except:
            traceFailure(step)
            raise

    finally:
        clearLock()
