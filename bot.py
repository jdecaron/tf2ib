#!/usr/bin/python2.6

import irclib
import math
import random
import re
import sqlite3
import string
import SRCDS
import thread
import threading
import time

#irclib.DEBUG = 1

def add(userName, userCommand):
    global state, userList
    print "State : " + state
    if state != 'idle':
        if state == 'captain' or state == 'normal':
            # Debug : 10
            if len(userList) == 10 and classCount('medic') == 0 and not re.search('medic', userCommand) and state == 'captain':
                stats(userName, "!stats " + userName)
                send("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join this round as this class.")
                return 0
            # Debug : 11
            if len(userList) == 11 and classCount('medic') <= 1 and not re.search('medic', userCommand) and state == 'captain':
                stats(userName, "!stats " + userName)
                send("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join as this class.")
                return 0
            # Debug : 12
            if len(userList) < 12:
                print "User add : " + userName + "  Command : " + userCommand
                userList[userName] = createUser(userName, userCommand)
                printUserList()
            # Debug : 12
            if len(userList) == 12:
                initGame()
        elif state == 'scrim':
            if len(userList) == 10 and classCount('medic') == 0 and not re.search('medic', userCommand):
                send("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join this round as this class.")
                return 0
            print "User add : " + userName + "  Command : " + userCommand
            userList[userName] = createUser(userName, userCommand)
            printUserList()
            if len(userList) >= 6 and classCount('medic') > 0:
                initGame()
        elif state == 'picking' and not isUserCountOverLimit():
            if isInATeam(userName):
                return 0
            userList[userName] = createUser(userName, userCommand)
            printUserList()
    else:
        send("PRIVMSG " + channel + " :\x030,01You can't \"!add\" until an admin has started a game.")

def addFriend(userName, userCommand):
    global userList
    # 2 friends limit.
    commandList = string.split(userCommand, ' ')
    if len(commandList) > 1 and userName in userList:
        for i in range(1, len(commandList)):
            userList[userName]['friends'] = commandList[i]

def addGame(userName, userCommand):
    resetVariables()
    global allowFriends, gameServer, lastGameType, state
    # Game server.
    if re.search("[0-9a-z]*\.[0-9a-z]*:[0-9][0-9][0-9][0-9][0-9]", userCommand):
        gameServer = re.findall("[0-9a-z]*\..*:[0-9][0-9][0-9][0-9][0-9]", userCommand)[0]
    else:
        send("NOTICE " + userName + " : You must set a server IP. Here is an example : \"!add 127.0.0.1:27015\".")
        return 0
    # Game type.
    if re.search('captain', userCommand):
        allowFriends = 0
        lastGameType = 'captain'
        state = 'captain'
    else:
        lastGameType = 'normal'
        state = 'normal'
    send("PRIVMSG " + channel + ' :\x030,01PUG started. Game type : ' + state + '. Type "!add" to join a game.')

def analyseCommand(connection, event):
    global lastCommand
    userName = extractUserName(event.source())
    userCommand = cleanUserCommand(event.arguments()[0])
    if re.match('^!', userCommand):
    # Check if the user is trying to pass a command to the bot.
        if isGamesurgeCommand(userCommand):
            return 1
        if isAdminCommand(userName, userCommand):
            if isAdmin(userName):
            #Execute the admin command.
                lastCommand = userCommand
                executeCommand(userName, userCommand)
                return 1
            else :
            # Exit and report an error.
                send("PRIVMSG " + channel + " :\x030,01Warning " + userName + ", you are trying an admin command as a normal user.")
                return 1
        else :
        #Execute the user command.
            if isUserCommand(userName, userCommand):
                lastCommand = userCommand
                executeCommand(userName, userCommand)
                return 1
    return 0

def assignCaptains(mode = 'captain'):
    global teamA, teamB
    if mode == 'captain':
        assignUserToTeam('medic', 0, 'a', userList[getAPlayer('medic')])
        assignUserToTeam('medic', 0, 'b', userList[getAPlayer('medic')])
        teamA[0]['status'] = 'captain'
        teamB[0]['status'] = 'captain'
        send("PRIVMSG " + channel + ' :\x030,01Captains are \x0311,01' + teamA[0]['nick'] + '\x030,01 and \x034,01' + teamB[0]['nick'] + "\x030,01.")
    elif mode == 'scrim':
        assignUserToTeam('medic', 0, 'a', userList[getAPlayer('medic')])
        teamA[0]['status'] = 'captain'
        send("PRIVMSG " + channel + ' :\x030,01Captain is \x0308,01' + teamA[0]['nick'] + '\x030,01.')
    printCaptainChoices()

def assignUserToTeam(gameClass, recursiveFriend, team, user):
    global allowFriends, teamA, teamB, userList
    if gameClass:
        user['class'] = [gameClass]
    else:
        user['class'] = []
    if not team:
        if random.randint(0,1):
            team = 'a'
        else:
            team = 'b'
    # Assign the user to the team if the team's not full.
    if len(getTeam(team)) < 6: # Debug : 6
        getTeam(team).append(user)
    else:
        getTeam(getOppositeTeam(team)).append(user)
    if allowFriends and recursiveFriend:
    # Add friends if allowed to.
        counter = 0
        for friend in userList[user['nick']]['friends']:
            if isUser(friend) and not firstChoiceMedic(friend):
                assignUserToTeam('', 0, team, friend)
                counter += 1
            if counter >= getNumberOfFriendsPerClass(userList[user['nick']]['class']):
                break
    del userList[user['nick']]
    return 0

def autoGameStart():
    global lastGameType, nick, startMode, state
    server = getAvailableServer()
    if state == 'idle' and server and startMode == 'automatic':
        addGame(nick, '!addgame ' + lastGameType + ' ' + server['ip'] + ':' + server['port'])

def buildTeams():
    global allowFriends, state, userList
    state = 'idle'
    assignUserToTeam('medic', 1, 'a', userList[getAPlayer('medic')])
    assignUserToTeam('medic', 1, 'b', userList[getAPlayer('medic')])
    for i in range(10): #Debug : 10
        assignUserToTeam('', 1, 0, userList[getAPlayer('')])
    startGame()

def captain():
    global teamA, teamB
    if len(teamA) > 0 and len(teamB) < 6:
        for user in getTeam(captainStageList[captainStage]):
            if user['status'] == 'captain':
                captainName = user['nick']
                break
        send("PRIVMSG " + channel + ' :\x030,01Captain picking turn is to ' + captainName + '.')
    else:
        send("PRIVMSG " + channel + ' :\x030,01Picking process has not been started yet.')

def checkConnection():
    global connectTimer
    if not server.is_connected():
        connect()

def classCount(gameClass):
    global userList
    counter = 0
    for i, j in userList.copy().iteritems():
        for userClass in userList[i]['class']:
            if userClass == gameClass:
                counter += 1
    return counter            

def cleanUserCommand(command):
    command = command.replace('[', '')
    command = command.replace('(', '')
    command = command.replace(')', '')
    return command

def confirm(userName):
    global confirmationList
    counter = 0
    for user in confirmationList:
        if user['nick'] == userName:
            print userName
            del confirmationList[counter]
            return 0
        counter += 1

def connect():
    global connectTimer, network, nick, name, port, server
    server.connect(network, port, nick, ircname = name)

def createUser(userName, userCommand):
    global classList, state
    commandList = string.split(userCommand, ' ')
    user = {'command':'', 'class':[], 'confirmed':0, 'friends':{}, 'id':0, 'late':0, 'nick':'', 'status':'', 'team':''}
    user['command'] = userCommand
    user['id'] = getNextPlayerID()
    if (getUserCount() + 1) > 12:
        user['late'] = 1
    classes = extractClasses(userCommand)
    if state != 'normal' or 'medic' in classes:
        user['class'] = classes
    user['nick'] = userName
    if state == 'captain' or state == 'picking':
        if len(user['class']) > 0:
            send("NOTICE " + userName + " : " + "You sucessfully subscribed to the picking process as : " + ", ".join(user['class']) + ".")
        else:
            send("NOTICE " + userName + " : " + "You sucessfully subscribed to the picking process but you did not specify any valid class. Please specify one to help the captains chosing you as the right one.")
    return user

def drop(connection, event):
    userName = ''
    if len(event.arguments()) > 1:
        userName = event.arguments()[0]
    else:
        userName = extractUserName(event.source())
    remove(userName)

def endGame():
    global initTimer, state
    initTimer.cancel()
    state = 'idle'
    print 'PUG stopped.'

def executeCommand(userName, userCommand):
    if re.search('^!add$', userCommand) or re.search('^!add ', userCommand):
        add(userName, userCommand)
        return 0
    if re.search('^!addfriends*', userCommand):
        addFriend(userName, userCommand)
        return 0
    if re.search('^!addgame', userCommand):
        addGame(userName, userCommand)
        return 0
    if re.search('^!automatic', userCommand):
        setStartMode('automatic')
        return 0
    if re.search('^!captain', userCommand):
        captain()
        return 0
    if re.search('^!confirm', userCommand):
        confirm(userName)
        return 0
    if re.search('^!endgame', userCommand):
        endGame()
        return 0
    if re.search('^!game', userCommand):
        game(userName, userCommand)
        return 0
    if re.search('^!ip', userCommand):
        ip()
        return 0
    if re.search('^!last', userCommand):
        last()
        return 0
    if re.search('^!limit', userCommand):
        limit(userName, userCommand)
        return 0
    if re.search('^!man$', userCommand):
        help()
        return 0
    if re.search('^!manual', userCommand):
        setStartMode('manual')
        return 0
    if re.search('^!mumble', userCommand):
        mumble()
        return 0
    if re.search('^!needsub', userCommand):
        needsub(userName, userCommand)
        return 0
    if re.search('^!notice', userCommand):
        notice(userName)
        return 0
    if re.search('^!pick', userCommand):
        pick(userName, userCommand)
        return 0
    if re.search('^!players', userCommand):
        players(userName)
        return 0
    if re.search('^!prototype*', userCommand):
        prototype()
        return 0
    if re.search('^!replace', userCommand):
        replace(userName, userCommand)
        return 0
    if re.search('^!remove', userCommand):
        remove(userName)
        return 0
    if re.search('^!restart', userCommand):
        restartBot()
        return 0
    if re.search('^!stats', userCommand):
        stats(userName, userCommand)
        return 0
    if re.search('^!sub', userCommand):
        sub(userName, userCommand)
        return 0
    if re.search('^!unconfirmeds*', userCommand):
        unconfirmed()
        return 0
    if re.search('^!votemap', userCommand):
        #votemap(userName, userCommand)
        return 0
    if re.search('^!whattimeisit', userCommand):
        send("PRIVMSG " + channel + " :\x038,01* \x039,01Hammertime \x038,01*")
        return 0

def extractClasses(userCommand):
    global classList
    classes = []
    commandList = string.split(userCommand, ' ')
    for i in commandList:
        for j in classList:
            if i == j:
                classes.append(j)
    return classes

def extractDBData(DBData):
    global cursor, srcdsData
    for row in DBData:
        srcdsData.append(row)
        cursor.execute('DELETE FROM srcds WHERE time = ?', (row[1],))
        connection.commit()
    return srcdsData

def extractUserName(user):
    return string.split(user, '!')[0]

def firstChoiceMedic(user):
    counter = 0
    for gameClass in userList[user]['class']:
        if gameClass == 'medic':
            break
        counter += 1
    if counter == 0:
        return 1
    return 0

def game(userName, userCommand):
    global captainStageList, state
    mode = userCommand.split(' ')
    if len(mode) <= 1:
        send("PRIVMSG " + channel + " :\x030,01The actual game mode is set to \"" + state + "\".")
        return 0
    elif not isAdmin(userName):
        send("PRIVMSG " + channel + " :\x030,01Warning " + userName + ", you are trying an admin command as a normal user.")
        return 0
    if mode[1] == 'captain':
        if state == 'scrim':
            captainStageList = ['a', 'b', 'a', 'b', 'a', 'b', 'a', 'b', 'a', 'b'] 
            state = 'captain'
        else:
            send("NOTICE " + userName + " :You can't switch the game mode in this bot state.")
    elif mode[1] == 'scrim':
        if state == 'captain':
            captainStageList = ['a', 'a', 'a', 'a', 'a'] 
            state = 'scrim'
        else:
            send("NOTICE " + userName + " :You can't switch the game mode in this bot state.")

def getAPlayer(gameClass):
    global userList
    for i in range(5):
        candidateList = []
        forcedList = []
        for user in userList.copy():
            if len(userList[user]['class']) > i and gameClass == userList[user]['class'][i]:
                candidateList.append(user)
            else:
                forcedList.append(user)
        if len(candidateList) != 0:
            if len(candidateList) > 1:
                return candidateList[random.randint(0,len(candidateList) - 1)]
            else:
                return candidateList[0]
    if len(forcedList) > 1:
        return forcedList[random.randint(0,len(forcedList) - 1)]
    else:
        return forcedList[0]

def getAvailableServer():
    global serverList
    for server in serverList:
        if (time.time() - server['last']) >= (60 * 60):
            return {'ip':server['dns'], 'port':server['port']}
    return 0

def getMap():
    global mapList
    return mapList[random.randint(0, (len(mapList) - 1))]

def getNextPlayerID():
    global userList
    largestID = 0
    for user in userList.copy():
        if userList[user]['id'] > largestID:
            largestID = userList[user]['id']
    return largestID + 1

def getNextSubID():
    global subList
    highestID = 0
    for sub in subList:
        if sub['id'] > highestID:
            highestID = sub['id']
    return highestID + 1

def getNumberOfFriendsPerClass(gameClass):
    if gameClass == 'medic':
        return 2
    else:
        return 1

def getOppositeTeam(team):
    if team == 'a':
        return 'b'
    else:
        return 'a'

def getPlayerName(userNumber):
    global userList
    for user in userList.copy():
        if userList[user]['id'] == userNumber:
            return userList[user]['nick']

def getPlayerNumber(userName):
    global userList
    for user in userList.copy():
        if user == userName:
            return userList[user]['id']

def getPlayerTeam(userName):
    for teamID in ['a', 'b']:
        team = getTeam(teamID)
        for user in team:
            if user['nick'] == userName:
                return teamID

def getRemainingClasses():
    global captainStage, captainStageList, formalTeam
    remainingClasses = formalTeam[:]
    team = getTeam(captainStageList[captainStage])
    for user in team:
        if user['class'][0] in remainingClasses:
            remainingClasses.remove(user['class'][0])
    uniqueRemainingClasses = {}
    for gameClass in remainingClasses:
        uniqueRemainingClasses[gameClass] = gameClass
    return uniqueRemainingClasses

def getSubIndex(id):
    global subList
    counter = 0
    for sub in subList:
        if sub['id'] == int(id):
            return counter
        counter += 1
    return -1

def getTeam(team):
    global teamA, teamB
    if team == 'a':
        return teamA
    else:
        return teamB

def getUserCount():
    global teamA, teamB, userList
    teams = [teamA, teamB]
    counter = len(userList)
    teamCounter = 0
    for team in teams:
        for user in teams[teamCounter]:
            counter += 1
        teamCounter += 1
    return counter

def help():
    send("PRIVMSG " + channel + " :\x030,01Visit \x0311,01http://communityfortress.com/tf2/news/tf2pugna-released.php\x030,01 to get help about the PUG process.")

def ip():
    global gameServer
    if gameServer != '':
        message = "\x030,01Server IP : connect " + gameServer + "; password " + password + ";"
        send("PRIVMSG " + channel + " :" + message)

def isAdmin(userName):
    whoisData = whois(userName)
    if len(whoisData) and (re.search('@' + channel + ' ', whoisData['channel']) or re.search('@' + channel + '$', whoisData['channel'])):
    # User is an admin.
        return 1
    else :
    # User is not an admin.
        return 0 #Debug : 0

def isAuthorizedCaptain(userName):
    global captainStage, captainStageList, teamA, teamB
    team = getTeam(captainStageList[captainStage])
    for user in team:
        if user['status'] == 'captain' and user['nick'] == userName:
            return 1
    return 0

def isCaptain(userName):
    teamList = ['a', 'b']
    for teamName in teamList:
        team = getTeam(teamName)
        for user in team:
            if user['status'] == 'captain' and user['nick'] == userName:
                return 1
    return 0

def isMatch():
    global serverList
    for server in serverList:
        if server['last'] != 0:
            return 1
    return 0

def isUserCountOverLimit():
    global teamA, teamB, userLimit, userList
    teams = [teamA, teamB]
    userCount = getUserCount()
    if userCount < userLimit:
        return 0
    else:
        return 1

def isGamesurgeCommand(userCommand):
    global gamesurgeCommands
    for command in gamesurgeCommands:
        if re.search("^" + command, userCommand):
            return 1
    return 0

def isUser(userName):
    if userName in userList:
        return 1
    else:
        return 0

def initGame():
    global gameServer, initTimer, nick, state, teamA, teamB
    print "Init game."
    if state == "normal":
        state = 'building'
        initTimer = threading.Timer(20, buildTeams)
        initTimer.start()
    elif state == "captain":
        send("PRIVMSG " + channel + " :\x030,01Teams are being drafted, please wait in the channel until this process's over.")
        state = 'picking'
        initTimer = threading.Timer(20, assignCaptains, ['captain'])
        initTimer.start()
        players(nick)
    elif state == "scrim":
        send("PRIVMSG " + channel + " :\x030,01Team is being drafted, please wait in the channel until this process's over.")
        state = 'picking'
        initTimer = threading.Timer(20, assignCaptains, ['scrim'])
        initTimer.start()
        players(nick)

def initServer():
    global gameServer, lastGame, rconPassword
    TF2Server = SRCDS.SRCDS(string.split(gameServer, ':')[0], int(string.split(gameServer, ':')[1]), rconPassword, 10)
    TF2Server.rcon_command('changelevel ' + getMap())
    lastGame = time.time()
    updateLast(string.split(gameServer, ':')[0], string.split(gameServer, ':')[1], time.time())

def isAdminCommand(userName, userCommand):
    global adminCommands
    userCommand = string.split(userCommand, ' ')[0]
    for i in adminCommands:
        if re.search('^' + userCommand + '$', i):
            return 1
    return 0

def isInATeam(userName):
    teamList = ['a', 'b']
    for teamName in teamList:
        team = getTeam(teamName)
        for user in team:
            if user['nick'] == userName:
                return 1
    return 0

def isUserCommand(userName, userCommand):
    global userCommands
    userCommand = string.split(userCommand, ' ')[0]
    for i in userCommands:
        if re.search('^' + userCommand + '$', i):
            return 1
    send("NOTICE " + userName + " : Invalid command : \"" + userCommand + "\". Type \"!man\" for usage commands.")
    return 0

def last():
    global lastGame, serverList
    if lastGame == 0:
        send("PRIVMSG " + channel + " :\x030,010 matches have been played since the bot got restarted.")
        return 0
    message = "PRIVMSG " + channel + " :\x030,01"
    if isMatch():
        message += "A game is currently being played. "
    lastTime = (time.time() - lastGame) / 3600
    hours = math.floor(lastTime)
    minutes = math.floor((lastTime - hours) * 60)
    if hours != 0:
        message += str(int(hours)) + " hour(s) "
    message += str(int(minutes)) + " minute(s) "
    send(message + "have elapsed since the last game started.")

def limit(userName, userCommand):
    global userLimit
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        send("PRIVMSG " + channel + " :\x030,01The PUG's user limit is set to \"" + str(userLimit) + "\".")
        return 0
    try:
        if not isAdmin(userName):
            send("PRIVMSG " + channel + " :\x030,01Warning " + userName + ", you are trying an admin command as a normal user.")
            return 0
        if int(commandList[1]) < 12:
            send("NOTICE " + userName + " : The limit value must be equal or above 12.")
            return 0
    except:
        return 0
    userLimit = int(commandList[1])

def listeningTF2Servers():
    while 1:
        time.sleep(1)
        for i in range(0, len(srcdsData)):
            if re.search('^!needsub', srcdsData[i][0]):
                needsub('', srcdsData[i][0])
            if re.search('^!gameover', srcdsData[i][0]):
                server = string.split(srcdsData[i][0], ' ')[1]
                updateLast(string.split(server, ':')[0], string.split(server, ':')[1], 0)
            del srcdsData[i]

def mumble():
    global voiceServer
    message = "\x030,01Voice server IP : " + voiceServer['ip'] + ":" + voiceServer['port'] + "  Password : " + password + "  Download : http://internap.dl.sourceforge.net/sourceforge/mumble/Mumble-1.1.8.exe"
    send("PRIVMSG " + channel + " :" + message)

def needsub(userName, userCommand):
    global classList, subList
    commandList = string.split(userCommand, ' ')
    sub = {'class':'unspecified', 'id':getNextSubID(), 'server':'', 'steamid':'', 'team':'unspecified'}
    for command in commandList:
        # Set the server IP.
        if re.search("[0-9a-z]*\.[0-9a-z]*:[0-9][0-9][0-9][0-9][0-9]$", command):
            sub['server'] = re.findall("[0-9a-z]*\..*:[0-9][0-9][0-9][0-9][0-9]", command)[0]
        # Set the Steam ID.
        if re.search("STEAM", command):
            sub['steamid'] = command
    if sub['server'] == '':
        send("NOTICE " + userName + " : You must set a server IP. Here is an example : \"!needsub 127.0.0.1:27015\".")
        return 0
    # Set the team.
    if 'blue' in commandList:
        sub['team'] = '\x0311,01Blue\x030,01'
    elif 'red' in commandList:
        sub['team'] = '\x034,01Red\x030,01'
    # Set the class.
    for argument in commandList:
        if argument in classList:
            sub['class'] = argument
    subList.append(sub)
    printSubs()

def nickchange(connection, event):
    global userList
    oldUserName = extractUserName(event.source())
    newUserName = event.target()
    if oldUserName in userList:
        userList[newUserName] = userList[oldUserName]
        userList[newUserName]['nick'] = newUserName
        del userList[oldUserName]

def notice(userName):
    send("NOTICE " + userName + " : Notice!!!!")

def pick(userName, userCommand):
    global captainStage, captainStageList, classList, state, teamA, teamB, userList
    if (len(captainStageList) >= 10 and (not len(teamA) or not len(teamB))) or (len(captainStageList) == 5 and not len(teamA)):
        send("NOTICE " + userName + " : The selection is not started yet.") 
        return 0
    commandList = string.split(userCommand, ' ')
    if len(commandList) <= 2:
        send("NOTICE " + userName + " : Error, your command has too few arguments. Here is an example of a valid \"!pick\" command : \"!pick nick scout\".") 
        return 0
    del commandList[0]
    gameClass = ''
    counter = 0
    for command in commandList:
        if command in classList:
            gameClass = command
            del commandList[counter]
        counter += 1
    userFound = 0
    if re.search('^[0-9][0-9]*$', commandList[0]) and getPlayerName(int(commandList[0])):
        commandList[0] = getPlayerName(int(commandList[0]))
        userFound = 1
    else:
        # Check if this nickname exists in the player list.
        for user in userList.copy():
            if userList[user]['nick'] == commandList[0]:
                userFound = 1
                break
    if not userFound:
        send("NOTICE " + userName + " : Error, this user doesn\'t exists.")
        return 0
    # Check if the captain specified a class.
    if gameClass == '':
        send("NOTICE " + userName + " : Error, you must specify a class from this list : " +  ', '.join(getRemainingClasses()) + ".")
        return 0
    if gameClass not in getRemainingClasses():
        send("NOTICE " + userName + " : This class is full, pick an other one from this list : " +  ', '.join(getRemainingClasses()))
        return 0
    if isAuthorizedCaptain(userName):
        send("NOTICE " + userName + " : You selected \"" + commandList[0] + "\" as \"" + gameClass + "\".")
        assignUserToTeam(gameClass, 0, getPlayerTeam(userName), userList[commandList[0]])
        # Debug : (len(captainStageList) - 1)
        if captainStage < (len(captainStageList) - 1):
            captainStage += 1
            printCaptainChoices()
        else:
            state = 'idle'
            startGame()
    else:
        send("NOTICE " + userName + " : It is not your turn, or you are not authorized to pick a player.") 

def players(userName):
    printCaptainChoices('channel')

def privmsg(connection, event):
    userName = extractUserName(event.source())
    userCommand = cleanUserCommand(event.arguments()[0])
    if re.search('^!confirm', userCommand):
        confirm(userName)

def pubmsg(connection, event):
    analyseCommand(connection, event)

def printCaptainChoices(printType = 'private'):
    global classList, captainStage, captainStageList, userList
    if printType == 'private':
        captainName = getTeam(captainStageList[captainStage])[0]['nick']
        dataPrefix = "NOTICE " + captainName + " : "
        send(dataPrefix + captainName + ", you are captain of a team and it's your turn to pick a player. Type \"!pick nick class\" to add somebody in your team.") 
        send(dataPrefix + "Remaining classes : " +  ', '.join(getRemainingClasses())) 
    else:
        dataPrefix = "PRIVMSG " + channel + " :\x030,01"
    for gameClass in classList:
        choiceList = []
        for userName in userList.copy():
            if gameClass in userList[userName]['class']:
                late = ''
                if userList[userName]['late'] == 1:
                    late = 'L'
                choiceList.append("(" + str(getPlayerNumber(userName)) + late + ")" + userName)
        if len(choiceList):
            send(dataPrefix + gameClass.capitalize() + "s: " + ', '.join(choiceList)) 
    choiceList = []
    for userName in userList.copy():
        late = ''
        if userList[userName]['late'] == 1:
            late = 'L'
        choiceList.append("(" + str(getPlayerNumber(userName)) + late + ")" + userName)
    send(dataPrefix + "All players : " + ', '.join(choiceList)) 

def printSubs():
    global subList
    if len(subList):
        send("PRIVMSG " + channel + " :" + "\x030,01Substitute(s) needed:")
        for sub in subList:
            by = ''
            if sub['steamid'] != '':
                by = ", User = \"" + sub['steamid'] + "\""
            send("PRIVMSG " + channel + " :" + "\x030,01ID = \"" + str(sub['id']) + "\", Class = \"" + sub['class'].capitalize() + "\", Server = \"" + sub['server'] + "\", Team = \"" + sub['team'] + "\"" + by)

def printTeams():
    global captainStageList, state, teamA, teamB
    if len(captainStageList) >= 10:
        teamNames = ['Blue', 'Red']
        colors = ['\x0311,01', '\x034,01']
        teams = [teamA, teamB]
    else:
        teamNames = ['Scrim']
        colors = ['\x0308,01']
        teams = [teamA]
    counter = 0
    for i in teams:
        message = colors[counter] + teamNames[counter] + "\x030,01 : "
        for user in teams[counter]:
            gameClass = ''
            if user['class']:
                gameClass = " as " + colors[counter] + user['class'][0] + "\x030,01"
            message += '"' + user['nick'] + gameClass + '" '
        send("PRIVMSG " + channel + " :" + message)
        counter += 1
    send("PRIVMSG " + channel + " :\x030,01Please confirm your presence by typing \"\x038,01!confirm\x030,01\" in the channel or directly to the bot.")

def printUserList():
    global lastUserPrint, printTimer, state, userList
    if (time.time() - lastUserPrint) > 5:
        message = "\x030,01" + str(len(userList)) + " user(s) subscribed :"
        for i, user in userList.copy().iteritems():
            message += ' "' + user['nick'] + '"'
        send("PRIVMSG " + channel + " :" + message + ".")
    else:
        printTimer.cancel()
        printTimer = threading.Timer(5, printUserList)
        printTimer.start()
    lastUserPrint = time.time()

def prototype():
    print saveStats()

def readPasswords():
    global authPassword, rconPassword
    passwordFile = open("passwords.txt")
    try:
        passwords = passwordFile.readline().replace('\n', '').split(':')
        authPassword = passwords[0]
        rconPassword = passwords[1]
    finally:
        passwordFile.close()

def replace(userName, userCommand):
    global userList
    teamList = ['a', 'b']
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        send("NOTICE " + userName + " : Error, there is not enough arguments in your \"!replace\" command. Example : \"!replace toreplace substitute\".")
        return 0
    toReplace = commandList[1]
    substitute = commandList[2]
    for teamName in teamList:
        if type(toReplace) == type({}):
            break
        counter = 0
        team = getTeam(teamName)
        for user in team:
            if user['nick'] == toReplace:
                toReplace = user
                toReplaceTeam = teamName
                break
            counter += 1
    if type(toReplace) == type({}):
        gameClass = toReplace['class']
        toReplace['class'] = extractClasses(toReplace['command'])
    else:
        send("NOTICE " + userName + " : Error, the user you specified to replace is not listed in a team.")
        return 0
    if substitute in userList:
        userList[substitute]['status'] = 'captain'
        assignUserToTeam('medic', 0, toReplaceTeam, userList[substitute])
        team[counter]['status'] = ''
        userList[team[counter]['nick']] = team[counter]
        del team[counter]
    else:
        send("NOTICE " + userName + " : Error, the substitute you specified is not in the subscribed list.")
    return 0

def remove(userName):
    global initTimer, state, userList
    if(isUser(userName)) and (state != 'picking' and state != 'building'):
        del userList[userName]
        initTimer.cancel()
        printUserList()

def resetUserVariables():
    global userAuth, userInfo, userName
    userAuth = []
    userChannel = []
    userInfo = []

def resetVariables():
    global allowFriends, captainStage, captainStageList, gameServer, teamA, teamB, userLimit, userList
    allowFriends = 1
    captainStage = 0
    captainStageList = ['a', 'b', 'a', 'b', 'a', 'b', 'a', 'b', 'a', 'b'] 
    gameServer = ''
    teamA = []
    teamB = []
    userList = {}
    print 'Reset variables.'

def restartBot():
    global restart
    restart = 1

def saveConfirmationList():
    global confirmationList
    confirmationList = []
    teamName = ['blue', 'red']
    teamCounter = 0
    userCounter = 0
    for teamID in ['a', 'b']:
        team = getTeam(teamID)
        for user in team:
            confirmationList.append(user)
            userCounter += 1
        teamCounter += 1
    print confirmationList

def saveStats():
    global connection, cursor
    teamName = ['\x0312blue\x031', '\x034red\x031']
    for teamID in ['a', 'b']:
        team = getTeam(teamID)
        for user in team:
            if len(user['class']) == 0:
                queryData = '', user['nick'], int(time.time())
            else:
                queryData = user['class'][0], user['nick'], int(time.time())
            cursor.execute('INSERT INTO stats VALUES (?, ?, ?)', queryData)
            connection.commit()

def send(message, delay = 2):
    global nextAvailableTimeSpot
    # Flood protection.
    actualTime = time.time()
    nextAvailableTimeSpot += delay
    if nextAvailableTimeSpot - actualTime < 0:
        nextAvailableTimeSpot = actualTime + delay
    printInterval = nextAvailableTimeSpot - actualTime
    threading.Timer(printInterval, server.send_raw, [message]).start()

def sendStartPrivateMessages():
    teamName = ['\x0312blue\x031', '\x034red\x031']
    teamCounter = 0
    userCounter = 0
    for teamID in ['a', 'b']:
        team = getTeam(teamID)
        for user in team:
            send("PRIVMSG " + user['nick'] + " :You have been assigned to the " + teamName[teamCounter] + " team. Connect as soon as possible to this TF2 server : \"\x034connect " + gameServer + "; password " + password + ";\x031\". Connect as well to the voIP server, for more information type \"!mumble\" in \"#tf2.pug.na\". Don't forget to confirm your presence by typing \"\x034!confirm\x031\" in the channel or directly to the bot.", 3.5)
            userCounter += 1
        teamCounter += 1

def setStartMode(mode):
    global startMode
    startMode = mode

def startGame():
    printTeams()
    # Debug.
    initServer()
    saveConfirmationList()
    saveStats()
    sendStartPrivateMessages()
    threading.Timer(60, unconfirmed).start()
    threading.Timer(120, unconfirmed).start()
    threading.Timer(180, unconfirmed).start()

def stats(userName, userCommand):
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        send("NOTICE " + userName + " : Error, there is not enough arguments in your \"!stats\" command. Example : \"!stats nick\".")
        return 0
    queryData = commandList[1],
    cursor.execute('SELECT * FROM stats WHERE nick LIKE ?', queryData)
    counter = 0
    medicCounter = 0
    for row in cursor:
        last = row[2]
        if row[0] == 'medic':
            medicCounter += 1
        counter += 1
    if counter == 0:
        send("PRIVMSG " + channel + ' :\x030,01No stats are available for the user "' + commandList[1] + '".')
        return 0
    medicRatio = float(medicCounter) / float(counter) * 100
    if medicRatio >= 15:
        color = "\x039,01"
    elif medicRatio >= 5:
        color = "\x038,01"
    else:
        color = "\x034,01"
    send("PRIVMSG " + channel + ' :\x030,01' + commandList[1] + ' played a total of ' + str(counter) + ' game(s) and has a medic ratio of ' + color + str(int(medicRatio)) + '%\x030,01.')

def sub(userName, userCommand):
    global subList
    commandList = string.split(userCommand)
    id = ''
    for argument in commandList:
        if re.search('[0-9]', argument):
            id = argument
    if id == '' or getSubIndex(id) == -1:
        send("NOTICE " + userName + " :You must supply a valid substitute ID. Example : \"!sub 1\".")
        return 0
    subIndex = getSubIndex(id)
    send("PRIVMSG " + userName + " :You are the substitute for a game that is about to start or that has already started. Connect as soon as possible to this TF2 server : \"connect " + subList[subIndex]['server'] + "; password " + password + ";\". Connect as well to the voIP server, for more information type \"!mumble\" in \"#tf2.pug.na\".")
    del(subList[subIndex])
    return 0

def updateLast(ip, port, last):
    global gameServer, serverList
    for i in range(0, len(serverList)):
        if (ip == serverList[i]['ip'] or ip == serverList[i]['dns']) and port == serverList[i]['port']:
            serverList[i]['last'] = last
            return 0

def unconfirmed():
    global confirmationList
    unconfirmedList = []
    for user in confirmationList:
        unconfirmedList.append(user['nick'])
    if len(unconfirmedList) > 0:
        send("PRIVMSG " + channel + " :\x037,01Warning!\x030,01 These players did not confirm their presence : " + ", ".join(unconfirmedList) + ".")

def welcome(connection, event):
    global authPassword
    server.send_raw("authserv auth " + nick + " " + authPassword)
    server.send_raw("MODE " + nick + " +x")
    server.join(channel)

def whois(userName):
    resetUserVariables()
    global userAuth, userChannel, userInfo, whoisEnded
    counter = 0
    whoisEnded = 0
    server.whois([userName])
    while not whoisEnded and counter < 20:
        irc.process_once(0.2)
        counter += 1
    if whoisEnded and len(userInfo):
        whoisData = {'auth':userAuth, 'channel':userChannel, 'info':userInfo}
    else:
        whoisData = {}
    print whoisData
    return whoisData

def whoisauth(connection, event):
    global userAuth
    print 'Whois Auth'
    print event.arguments()
    for i in event.arguments():
        userAuth.append(i)

def whoischannels(connection, event):
    global userChannel
    print 'Whois Channel'
    print event.arguments()
    if re.search('#', event.arguments()[1]):
        userChannel = event.arguments()[1]
        return 0

def whoisend(connection, event):
    global whoisEnded
    print 'Whois End'
    whoisEnded = 1

def whoisuser(connection, event):
    global userInfo
    print 'Whois Info'
    print event.arguments()
    for i in event.arguments():
        userInfo.append(i)

# Connection information
network = '127.0.0.1'
port = 6667
channel = '#tf2.pug.na'
nick = 'PUG-BOT'
name = 'BOT'

adminCommands = ["!addgame", "!automatic", "!endgame", "!manual", "!needsub", "!prototype", "!replace", "!restart"]
allowFriends = 1
authPassword = ''
captainStage = 0
captainStageList = ['a', 'b', 'a', 'b', 'a', 'b', 'a', 'b', 'a', 'b'] 
classList = ['demo', 'medic', 'scout', 'soldier']
confirmationList = []
connectTimer = threading.Timer(0, None)
formalTeam = ['demo', 'medic', 'scout', 'scout', 'soldier', 'soldier']
gameServer = ''
gamesurgeCommands = ["!access", "!addcoowner", "!addmaster", "!addop", "!addpeon", "!adduser", "!clvl", "!delcoowner", "!deleteme", "!delmaster", "!delop", "!delpeon", "!deluser", "!deop", "!down", "!downall", "!devoice", "!giveownership", "!resync", "!trim", "!unsuspend", "!upall", "!uset", "!voice", "!wipeinfo"]
initTimer = threading.Timer(0, None)
lastCommand = ""
lastGame = 0
lastGameType = "captain"
lastLargeOutput = time.time()
lastUserPrint = time.time()
mapList = ["cp_badlands", "cp_freight", "cp_granary", "cp_yukon_final"]
minuteTimer = time.time()
nextAvailableTimeSpot = time.time()
nominatedCaptains = []
password = 'tf2pug'
printTimer = threading.Timer(0, None)
rconPassword = ''
startMode = 'automatic'
state = 'idle'
teamA = []
teamB = []
restart = 0
serverList = [{'dns':'dallas.tf2pug.org', 'ip':'72.14.177.61', 'last':0, 'port':'27015'}, {'dns':'dallas.tf2pug.org', 'ip':'72.14.177.61', 'last':0, 'port':'27016'}]
srcdsData = []
subList = []
userCommands = ["!add", "!addfriend", "!addfriends", "!captain", "!confirm", "!game", "!ip", "!last", "!limit", "!man", "!mumble", "!notice", "!pick", "!players", "!remove", "!stats", "!sub", "!unconfirmed", "!votemap", "!whattimeisit"]
userAuth = []
userChannel = []
userInfo = []
userLimit = 13
userList = {}
voiceServer = {'ip':'mumble.tf2pug.org', 'port':'64738'}
whoisEnded = 0

readPasswords()

#CREATE TABLE stats (class varchar(255), nick varchar(255), time int)
connection = sqlite3.connect('./tf2pb.sqlite')
cursor = connection.cursor()
srcdsData = extractDBData(cursor.execute('SELECT * FROM srcds'))

# Create an IRC object
irc = irclib.IRC()

# Create a server object, connect and join the channel
server = irc.server()
connect()

irc.add_global_handler('dcc_disconnect', drop)
irc.add_global_handler('disconnect', drop)
irc.add_global_handler('endofwhois', whoisend)
irc.add_global_handler('kick', drop)
irc.add_global_handler('nick', nickchange)
irc.add_global_handler('part', drop)
irc.add_global_handler('privmsg', privmsg)
irc.add_global_handler('pubmsg', pubmsg)
irc.add_global_handler('quit', drop)
irc.add_global_handler('welcome', welcome)
irc.add_global_handler('whoisauth', whoisauth)
irc.add_global_handler('whoischannels',whoischannels)
irc.add_global_handler('whoisuser',whoisuser)

# Start the server listening.
thread.start_new_thread(listeningTF2Servers, ())

# Jump into an infinite loop
while not restart:
    irc.process_once(0.2)
    srcdsData = extractDBData(cursor.execute('SELECT * FROM srcds'))
    if time.time() - minuteTimer > 60:
        minuteTimer = time.time()
        checkConnection()
        printSubs()
        autoGameStart()

connectTimer.cancel()
