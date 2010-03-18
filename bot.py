#!/usr/bin/python

import irclib
import math
import psycopg
import random
import re
import string
import SRCDS
import thread
import threading
import time

#irclib.DEBUG = 1

def add(userName, userCommand, ninjAdd = 0):
    global state, userList
    print "State : " + state
    if state != 'idle':
        if state == 'captain' or state == 'highlander' or state == 'normal':
            if state == 'highlander' or state == 'normal':
                if len(userCommand.split()) <= 1:
                    send("NOTICE " + userName + " : You must specify a class you want to play with. Example : \"!add scout\".")
                    return 0
                if len(userCommand.split()) > 2:
                    send("NOTICE " + userName + " : You can't add as multiple classes in this game mode.")
                    return 0
                if ninjAdd and userCommand.split()[1] in classList and not getNinjaddSpot(userCommand.split()[1]):
                    send("NOTICE " + userName + " : There was no ninjadd spot available for this class, try an other one.")
                    return 0
                availableClasses = getAvailableClasses()
                if userCommand.split()[1] not in availableClasses:
                    send("NOTICE " + userName + " : The class you specified is not in the available class list : " + ", ".join(availableClasses) + ".")
                    return 0
            if len(userList) == (userLimit -2) and classCount('medic') == 0 and not isMedic(userCommand):
                stats(userName, "!stats " + userName)
                send("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join this round as this class.")
                return 0
            if len(userList) == (userLimit -1) and classCount('medic') <= 1 and not isMedic(userCommand):
                stats(userName, "!stats " + userName)
                send("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join as this class.")
                return 0
            if len(userList) < userLimit:
                print "User add : " + userName + "  Command : " + userCommand
                userList[userName] = createUser(userName, userCommand)
                printUserList()
            if len(userList) >= (getTeamSize() * 2) and classCount('medic') > 1:
                if len(findAwayUsers()) == 0:
                    initGame()
                elif type(awayTimer).__name__ == 'float':
                    sendMessageToAwayPlayers()
        elif state == 'scrim':
            if len(userList) == (userLimit - 2) and classCount('medic') == 0 and not isMedic(userCommand):
                send("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join this round as this class.")
                return 0
            print "User add : " + userName + "  Command : " + userCommand
            userList[userName] = createUser(userName, userCommand)
            printUserList()
            if len(userList) >= 6 and classCount('medic') > 0:
                if len(findAwayUsers()) == 0:
                    initGame()
                elif type(awayTimer).__name__ == 'float':
                    sendMessageToAwayPlayers()
        elif state == 'picking' and not isUserCountOverLimit():
            if initTimer.isAlive():
                if isInATeam(userName):
                    return 0
                userList[userName] = createUser(userName, userCommand)
                printUserList()
            else:
                send("NOTICE " + userName + " : You can't add during the picking process.")
                return 0
    else:
        send("PRIVMSG " + channel + " :\x030,01You can't \"!add\" until an admin has started a game.")

def addFriend(userName, userCommand):
    global userList
    # 2 friends limit.
    friendList = []
    commandList = string.split(userCommand, ' ')
    if len(commandList) > 1 and userName in userList:
        for i in range(1, len(commandList)):
            friendList.append(commandList[i])
        userList[userName]['friends'] = friendList

def addGame(userName, userCommand):
    resetVariables()
    global allowFriends, classList, gameServer, lastGameType, state, userLimit
    # Game server.
    if re.search("[0-9a-z]*\.[0-9a-z]*:[0-9][0-9][0-9][0-9][0-9]", userCommand):
        gameServer = re.findall("[0-9a-z]*\..*:[0-9][0-9][0-9][0-9][0-9]", userCommand)[0]
    else:
        send("NOTICE " + userName + " : You must set a server IP. Here is an example : \"!add 127.0.0.1:27015\".")
        return 0
    # Game type.
    if re.search('captain', userCommand):
        allowFriends = 0
        classList = ['demo', 'medic', 'scout', 'soldier']
        lastGameType = 'captain'
        state = 'captain'
        userLimit = 15
    elif re.search('highlander', userCommand):
        allowFriends = 0
        classList = ['demo', 'engineer', 'heavy', 'medic', 'pyro', 'scout', 'sniper', 'soldier', 'spy']
        lastGameType = 'highlander'
        state = 'highlander'
        userLimit = 18
    else:
        allowFriends = 0
        classList = ['demo', 'medic', 'scout', 'soldier']
        lastGameType = 'normal'
        state = 'normal'
        userLimit = 12
    updateLast(gameServer.split(':')[0], gameServer.split(':')[1], -(time.time()))
    send("PRIVMSG " + channel + ' :\x030,01PUG started. Game type : ' + state + '. Type "!add" to join a game.')

def analyseCommand(connection, event):
    global userList
    userName = extractUserName(event.source())
    userCommand = event.arguments()[0]
    escapedUserCommand = cleanUserCommand(event.arguments()[0])
    if userName in userList:
        updateUserStatus(userName, escapedUserCommand)
    if re.match('^\\\\!', escapedUserCommand):
    # Check if the user is trying to pass a command to the bot.
        if isAdminCommand(userName, escapedUserCommand):
            if isAdmin(userName):
            #Execute the admin command.
                executeCommand(userName, escapedUserCommand, userCommand)
            else :
            # Exit and report an error.
                send("PRIVMSG " + channel + " :\x030,01Warning " + userName + ", you are trying an admin command as a normal user.")
        elif isUserCommand(userName, escapedUserCommand, userCommand):
                executeCommand(userName, escapedUserCommand, userCommand)

def assignCaptains(mode = 'captain'):
    global teamA, teamB
    if mode == 'captain':
        captain1 = getAPlayer('captain')
        userList[captain1['nick']]['status'] = 'captain'
        assignUserToTeam(captain1['class'][0], 0, 'a', userList[captain1['nick']])
        captain2 = getAPlayer('captain')
        userList[captain2['nick']]['status'] = 'captain'
        assignUserToTeam(captain2['class'][0], 0, 'b', userList[captain2['nick']])
        send("PRIVMSG " + channel + ' :\x030,01Captains are \x0311,01' + teamA[0]['nick'] + '\x030,01 and \x034,01' + teamB[0]['nick'] + "\x030,01.")
    elif mode == 'scrim':
        captain1 = getAPlayer('captain')
        assignUserToTeam(captain1['class'][0], 0, 'a', userList[captain1['nick']])
        send("PRIVMSG " + channel + ' :\x030,01Captain is \x0308,01' + teamA[0]['nick'] + '\x030,01.')
    printCaptainChoices()

def assignUserToTeam(gameClass, recursiveFriend, team, user):
    global allowFriends, pastGames, teamA, teamB, userList
    if gameClass:
        user['class'] = [gameClass]
    else:
        user['class'] = []
    if not team:
        if random.randint(0,1):
            team = 'a'
        else:
            team = 'b'
    user['team'] = team
    # Assign the user to the team if the team's not full.
    if len(getTeam(team)) < getTeamSize(): # Debug : 6
        getTeam(team).append(user)
    else:
        getTeam(getOppositeTeam(team)).append(user)
    pastGames[len(pastGames) - 1]['players'].append(userList[user['nick']])
    del userList[user['nick']]
    return 0

def autoGameStart():
    global botID, connection, lastGameType, nick, startMode, state
    if state == 'idle':
        server = getAvailableServer()
    else:
        return 0
    cursor = connection.cursor()
    cursor.execute('UPDATE servers SET last = 0 WHERE last < 0 AND botID = %s', (botID,))
    cursor.execute('COMMIT;')
    if server and startMode == 'automatic':
        addGame(nick, '!addgame ' + lastGameType + ' ' + server['ip'] + ':' + server['port'])

def buildTeams():
    global allowFriends, userList
    fullClassList = classList
    if getTeamSize() == 6:
        fullClassList = formalTeam
    for team in ['a', 'b']:
        for gameClass in fullClassList:
            assignUserToTeam(gameClass, 0, team, userList[getAPlayer(gameClass)])
    printTeams()

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
    return re.escape(command)

def clearCaptainsFromTeam(team):
    for user in getTeam(team):
        if user['status'] == 'captain':
            user['status'] = ''

def clearSubstitutes(ip, port):
    global subList
    i = 0
    print subList
    while i < len(subList):
        if subList[i]['server'] == ip + ':' + port or subList[i]['server'] == getDNSFromIP(ip) + ':' + port:
            del subList[i]
        i = i + 1
        if i > 20:
            break

def connect():
    global connectTimer, network, nick, name, port, server
    server.connect(network, port, nick, ircname = name, localaddress = '69.164.199.15')

def createUser(userName, userCommand):
    global classList, state
    commandList = string.split(userCommand, ' ')
    user = {'command':'', 'class':[], 'friends':{}, 'id':0, 'last':0, 'late':0, 'nick':'', 'status':'', 'team':''}
    user['command'] = userCommand
    user['id'] = getNextPlayerID()
    user['last'] = time.time()
    if (getUserCount() + 1) > 12:
        user['late'] = 1
    user['class'] = extractClasses(userCommand)
    if re.search('captain', userCommand):
        stats = getWinStats(userName)
        authorized = 1
        if stats:
            gamesPlayed = stats[1]
            handicap = stats[2]
            if 'medic' not in user['class'] and (gamesPlayed < 20 or (gamesPlayed > 0 and float(handicap + gamesPlayed) / float(2 * gamesPlayed) <= 0.45)):
                authorized = 0
        else:
            authorized = 0
        if not authorized:
            send("NOTICE " + userName + " : " + "You don't meet the requirements to be a captain : minimum of 20 games played and a 45% win ratio.")
        else:
            user['status'] = 'captain'
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
    global gameServer, initTimer, state
    initTimer.cancel()
    updateLast(gameServer.split(':')[0], gameServer.split(':')[1], 0)
    state = 'idle'
    print 'PUG stopped.'

def executeCommand(userName, escapedUserCommand, userCommand):
    if re.search('^\\\\!add$', escapedUserCommand) or re.search('^\\\\!add\\\\ ', escapedUserCommand):
        add(userName, userCommand)
        return 0
    if re.search('^\\\\!addfriends*', escapedUserCommand):
        addFriend(userName, userCommand)
        return 0
    if re.search('^\\\\!addgame', escapedUserCommand):
        addGame(userName, userCommand)
        return 0
    if re.search('^\\\\!automatic', escapedUserCommand):
        setStartMode('automatic')
        return 0
    if re.search('^\\\\!captain', escapedUserCommand):
        captain()
        return 0
    if re.search('^\\\\!endgame', escapedUserCommand):
        endGame()
        return 0
    if re.search('^\\\\!force', escapedUserCommand):
        force(userName)
        return 0
    if re.search('^\\\\!game', escapedUserCommand):
        game(userName, userCommand)
        return 0
    if re.search('^\\\\!ip', escapedUserCommand):
        ip()
        return 0
    if re.search('^\\\\!last', escapedUserCommand):
        last()
        return 0
    if re.search('^\\\\!limit', escapedUserCommand):
        limit(userName, userCommand)
        return 0
    if re.search('^\\\\!man$', escapedUserCommand):
        help()
        return 0
    if re.search('^\\\\!manual', escapedUserCommand):
        setStartMode('manual')
        return 0
    if re.search('^\\\\!mumble', escapedUserCommand):
        mumble()
        return 0
    if re.search('^\\\\!needsub', escapedUserCommand):
        needsub(userName, userCommand)
        return 0
    if re.search('^\\\\!ninjadd', escapedUserCommand):
        ninjadd(userName, userCommand)
        return 0
    if re.search('^\\\\!notice', escapedUserCommand):
        notice(userName)
        return 0
    if re.search('^\\\\!pick', escapedUserCommand):
        pick(userName, userCommand)
        return 0
    if re.search('^\\\\!players', escapedUserCommand):
        players(userName)
        return 0
    if re.search('^\\\\!prototype*', escapedUserCommand):
        prototype()
        return 0
    if re.search('^\\\\!replace', escapedUserCommand):
        replace(userName, userCommand)
        return 0
    if re.search('^\\\\!remove', escapedUserCommand):
        remove(userName)
        return 0
    if re.search('^\\\\!restart', escapedUserCommand):
        restartBot()
        return 0
    if re.search('^\\\\!scramble', escapedUserCommand):
        scramble(userName)
        return 0
    if re.search('^\\\\!stats', escapedUserCommand):
        stats(userName, userCommand)
        return 0
    if re.search('^\\\\!sub', escapedUserCommand):
        sub(userName, userCommand)
        return 0
    if re.search('^\\\\!votemap', escapedUserCommand):
        #votemap(userName, escapedUserCommand)
        return 0
    if re.search('^\\\\!whattimeisit', escapedUserCommand):
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

def extractUserName(user):
    return string.split(user, '!')[0]

def findAwayUsers():
    global awayList, userList
    if type(awayTimer).__name__ == 'float' and time.time() - awayTimer <= (5 * 60):
        awayList = {}
    elif len(awayList) == 0:
        for user in userList:
            if user in userList and userList[user]['last'] <= (time.time() - (7 * 60)):
                awayList[user] = userList[user]
    return awayList

def force(userName):
    scramble(userName, 1)

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
            captainStageList = ['a', 'b', 'b', 'a', 'a', 'b', 'b', 'a', 'a', 'b'] 
            state = 'captain'
        else:
            send("NOTICE " + userName + " :You can't switch the game mode in this bot state.")
    elif mode[1] == 'scrim':
        if state == 'captain':
            captainStageList = ['a', 'a', 'a', 'a', 'a'] 
            state = 'scrim'
        else:
            send("NOTICE " + userName + " :You can't switch the game mode in this bot state.")

def getAPlayer(playerType):
    global userList
    if playerType == 'captain':
        medics = []
        medicsCaptains = []
        otherCaptains = []
        userListCopy = userList.copy()
        for user in userListCopy:
            if re.search('medic', userListCopy[user]['command']):
                if userListCopy[user]['status'] == 'captain':
                    medicsCaptains.append(userListCopy[user])
                else:
                    medics.append(userListCopy[user])
            elif userListCopy[user]['status'] == 'captain':
                otherCaptains.append(userListCopy[user])
        if len(medicsCaptains) > 0:
            player = getRandomItemFromList(medicsCaptains)
            player['class'] = ['medic']
        elif len(otherCaptains) > 0:
            player = getRandomItemFromList(otherCaptains)
            if len(player['class']) > 0:
                player['class'] = [player['class'][0]]
            else:
                player['class'] = ['scout']
        else:
            player = getRandomItemFromList(medics)
            player['class'] = ['medic']
        return player
    else:
        forcedList = []
        candidateList = []
        for user in userList.copy():
            forcedList.append(user)
            if len(userList[user]['class']) > 0 and playerType == userList[user]['class'][0]:
                candidateList.append(user)
        if len(candidateList) > 0:
            return getRandomItemFromList(candidateList)
        else:
            return getRandomItemFromList(forcedList)

def getAvailableClasses():
    availableClasses = []
    numberOfPlayersPerClass = {'demo':2, 'medic':2, 'scout':4, 'soldier':4}
    if getTeamSize() == 9:
        numberOfPlayersPerClass = {'demo':2, 'engineer':2, 'heavy':2, 'medic':2, 'pyro':2, 'scout':2, 'sniper':2, 'soldier':2, 'spy':2}
    for gameClass in classList:
        if classCount(gameClass) < numberOfPlayersPerClass[gameClass]:
            availableClasses.append(gameClass)
    return availableClasses

def getAvailableServer():
    for server in getServerList():
        if server['last'] >= 0 and (time.time() - server['last']) >= (60 * 75):
            return {'ip':server['dns'], 'port':server['port']}
    return 0

def getCaptainNameFromTeam(team):
    for user in getTeam(team):
        if user['status'] == 'captain':
            return user['nick']

def getDNSFromIP(ip):
    for server in getServerList():
        if server['ip'] == ip:
            return server['dns']
    return ip

def getIPFromDNS(dns):
    for server in getServerList():
        if server['dns'] == dns:
            return server['ip']
    return dns

def getLastTimeMedic(userName):
    cursor = connection.cursor()
    cursor.execute('SELECT time FROM stats WHERE nick ILIKE %s AND class = \'medic\' ORDER BY time DESC LIMIT 1;', (userName,))
    for row in cursor.fetchall():
        return row[0]
    return 0

def getMap():
    global mapList
    return mapList[random.randint(0, (len(mapList) - 1))]

def getMedicRatioColor(medicRatio):
    if medicRatio >= 7:
        return "\x039,01"
    elif medicRatio >= 5:
        return "\x038,01"
    else:
        return "\x034,01"

def getMedicStats(userName):
    medicStats = {'totalGamesAsMedic':0, 'medicWinRatio':0}
    cursor = connection.cursor()
    cursor.execute('SELECT lower(nick), count(*), sum(result) FROM stats where nick ILIKE %s AND class = \'medic\' AND botID = %s GROUP BY lower(nick)', (userName, botID))
    for row in cursor.fetchall():
        medicStats['totalGamesAsMedic'] = row[1]
        medicStats['medicWinRatio'] = float(float(row[2]) + (medicStats['totalGamesAsMedic'] / 2)) / float(medicStats['totalGamesAsMedic'])
    return medicStats

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

def getNinjaddSpot(userClass):
    if userClass in getAvailableClasses():
        return 1
    potentialNinjaddSpot = []
    for user in userList.copy():
        if userClass in userList[user]['class']:
            potentialNinjaddSpot.append({'nick':user, 'ratio':0})
    lowestRatio = 1
    for i in reversed(range(len(potentialNinjaddSpot))):
        if getLastTimeMedic(potentialNinjaddSpot[i]['nick']) > time.time() - (60 * 60 * 24):
            del potentialNinjaddSpot[i]
            continue
        userStats = getWinStats(potentialNinjaddSpot[i]['nick'])
        ratio = 0
        if userStats:
            ratio = float(getMedicStats(potentialNinjaddSpot[i]['nick'])['totalGamesAsMedic']) / float(userStats[1])
            potentialNinjaddSpot[i]['ratio'] = ratio
        if ratio < lowestRatio:
            lowestRatio = ratio
    for i in range(len(potentialNinjaddSpot)):
        if potentialNinjaddSpot[i]['ratio'] < 0.10 and potentialNinjaddSpot[i]['ratio'] == lowestRatio:
            send("PRIVMSG " + potentialNinjaddSpot[i]['nick'] + ' :You got removed from the PUG because somebody ninjadded and stole your spot. To protect yourself from a future similar situation you can increase your medic ratio at 10% or have played medic in the last 24 hours.')
            remove(potentialNinjaddSpot[i]['nick'])
            return 1
    return 0

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

def getRandomItemFromList(list):
    listLength = len(list)
    if listLength > 1:
        return list[random.randint(0, listLength - 1)]
    elif listLength == 1:
        return list[0]
    else:
        return []

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

def getServerList():
    serverList = []
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM servers')
    for row in cursor.fetchall():
        serverList.append({'dns':row[0], 'ip':row[1], 'last':row[2], 'port':row[3], 'botID':row[4]})
    return serverList

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

def getTeamSize():
    teamSize = 6
    if len(classList) == 9:
        teamSize = 9
    return teamSize

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

def getWinStats(userName):
    cursor = connection.cursor()
    cursor.execute('SELECT lower(nick), count(*), sum(result) FROM stats WHERE nick ILIKE %s AND botID = %s GROUP BY lower(nick)', (userName, botID))
    for row in cursor.fetchall():
        return row
    return 0

def help():
    send("PRIVMSG " + channel + " :\x030,01Visit \x0311,01http://communityfortress.com/tf2/news/tf2pugna-released.php\x030,01 to get help about the PUG process.")

def ip():
    global gameServer
    if gameServer != '':
        message = "\x030,01Server IP : connect " + gameServer + "; password " + password + ";"
        send("PRIVMSG " + channel + " :" + message)

def isAdmin(userName):
    whoisData = whois(userName)
    if (len(whoisData) and (re.search('@' + channel + ' ', whoisData['channel']) or re.search('@' + channel + '$', whoisData['channel']))) or (len(whoisData) and (re.search('\+' + channel + ' ', whoisData['channel']) or re.search('\+' + channel + '$', whoisData['channel']))):
    # User is an admin.
        return 1
    else :
    # User is not an admin.
        return 0

def isAdminCommand(userName, userCommand):
    global adminCommands
    userCommand = string.split(userCommand, ' ')[0]
    userCommand = removeLastEscapeCharacter(userCommand)
    for command in adminCommands:
        if command == userCommand:
            return 1
    return 0

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

def isGamesurgeCommand(userCommand):
    global gamesurgeCommands
    for command in gamesurgeCommands:
        if command == userCommand:
            return 1
    return 0

def isMatch():
    for server in getServerList():
        if server['last'] > 0 and server['botID'] == botID:
            return 1
    return 0

def isMedic(userCommand):
    if 'medic' in userCommand.split():
        return 1
    else:
        return 0

def isUserCommand(userName, escapedUserCommand, userCommand):
    global userCommands
    escapedUserCommand = string.split(escapedUserCommand, ' ')[0]
    escapedUserCommand = removeLastEscapeCharacter(escapedUserCommand)
    for command in userCommands:
        if command == escapedUserCommand:
            return 1
    send("NOTICE " + userName + " : Invalid command : \"" + userCommand + "\". Type \"!man\" for usage commands.")
    return 0

def isUserCountOverLimit():
    global teamA, teamB, userLimit, userList
    teams = [teamA, teamB]
    userCount = getUserCount()
    if userCount < userLimit:
        return 0
    else:
        return 1

def isUser(userName):
    if userName in userList:
        return 1
    else:
        return 0

def initGame():
    global gameServer, initTime, initTimer, nick, pastGames, scrambleList, startGameTimer, state, teamA, teamB
    if state == 'building' or state == 'picking':
        return 0
    initTime = int(time.time())
    pastGames.append({'players':[], 'server':gameServer, 'time':initTime})
    if state == "normal" or state == "highlander":
        scrambleList = []
        send("PRIVMSG " + channel + " :\x038,01Teams are being drafted, please wait in the channel until this process is over.")
        send("PRIVMSG " + channel + " :\x037,01If you find teams unfair you can type \"!scramble\" and they will be adjusted.")
        state = 'building'
        initTimer = threading.Timer(20, buildTeams)
        initTimer.start()
        startGameTimer = threading.Timer(100, startGame)
        startGameTimer.start()
    elif state == "captain":
        send("PRIVMSG " + channel + " :\x038,01Teams are being drafted, please wait in the channel until this process is over.")
        state = 'picking'
        initTimer = threading.Timer(60, assignCaptains, ['captain'])
        initTimer.start()
        players(nick)
    elif state == "scrim":
        send("PRIVMSG " + channel + " :\x038,01Team is being drafted, please wait in the channel until this process is over.")
        state = 'picking'
        initTimer = threading.Timer(60, assignCaptains, ['scrim'])
        initTimer.start()
        players(nick)

def initServer():
    global gameServer, lastGame, rconPassword
    try:
        lastGame = time.time()
        TF2Server = SRCDS.SRCDS(string.split(gameServer, ':')[0], int(string.split(gameServer, ':')[1]), rconPassword, 10)
        TF2Server.rcon_command('changelevel ' + getMap())
    except:
        return 0

def isInATeam(userName):
    teamList = ['a', 'b']
    for teamName in teamList:
        team = getTeam(teamName)
        for user in team:
            if user['nick'] == userName:
                return 1
    return 0

def last():
    global lastGame
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
    global connection, pastGames
    cursor = connection.cursor()
    while 1:
        time.sleep(1)
        cursor.execute('SELECT * FROM srcds')
        try:
            queryData = cursor.fetchall()
        except:
            queryData = []
        for i in range(0, len(queryData)):
            srcdsData = queryData[i][0].split()
            server = srcdsData[len(srcdsData) - 1]
            ip = string.split(server, ':')[0]
            port = string.split(server, ':')[1]
            for pastGame in pastGames:
                if pastGame['server'] == server or pastGame['server'] == getDNSFromIP(ip) + ':' + port:
                    if re.search('^!needsub', srcdsData[0]):
                        needsub('', queryData[i][0])
                    if re.search('^!gameover', srcdsData[0]):
                        score = srcdsData[1]
                        clearSubstitutes(ip, port)
                        updateLast(ip, port, 0)
                        updateStats(ip, port, score)
                        send("PRIVMSG " + channel + " :\x030,01Game over on server \"" + getDNSFromIP(ip) + ":" + port + "\", final score is : \x0311,01" + score.split(':')[0] + "\x030,01 to \x034,01" + score.split(':')[1] + "\x030,01.")
                    cursor.execute('DELETE FROM srcds WHERE time = %s', (queryData[i][1],))
                    cursor.execute('COMMIT;')
            if time.time() - queryData[i][1] >= 20:
                cursor.execute('DELETE FROM srcds WHERE time = %s', (queryData[i][1],))
                cursor.execute('COMMIT;')

def mumble():
    global voiceServer
    message = "\x030,01Voice server IP : " + voiceServer['ip'] + ":" + voiceServer['port'] + "  Password : " + password + "  Download : http://downloads.sourceforge.net/project/mumble/Mumble/1.2.2/Mumble-1.2.2.exe"
    send("PRIVMSG " + channel + " :" + message)

def needsub(userName, userCommand):
    global classList, subList
    commandList = string.split(userCommand, ' ')
    sub = {'class':'unspecified', 'id':getNextSubID(), 'server':'', 'steamid':'', 'team':'unspecified'}
    for command in commandList:
        # Set the server IP.
        if re.search("[0-9a-z]*\.[0-9a-z]*:[0-9][0-9][0-9][0-9][0-9]$", command):
            sub['server'] = re.findall("[0-9a-z]*\..*:[0-9][0-9][0-9][0-9][0-9]", command)[0]
            sub['server'] = getDNSFromIP(sub['server'].split(':')[0]) + ':' + sub['server'].split(':')[1]
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

def ninjadd(userName, userCommand):
    """if time.time() - getLastTimeMedic(userName) >= (60 * 60 * 24):
        send("NOTICE " + userName + " : Error, you need to have played medic at least once in the last 24 hours to be able to \"!ninjadd\".") 
        #return 0"""
    medicStats = getMedicStats(userName)
    if medicStats['medicWinRatio'] < 0.40:
        send("NOTICE " + userName + " : Error, you need to have a win ratio above 40% as medic to be able to \"!ninjadd\".") 
        return 0
    winStats = getWinStats(userName)
    if not winStats or winStats[1] < 20:
        send("NOTICE " + userName + " : Error, you need to have played more than 20 games to be able to \"!ninjadd\".")
        return 0
    if not winStats or float(medicStats['totalGamesAsMedic']) / float(winStats[1]) < 0.16:
        send("NOTICE " + userName + " : Error, you need to have a medic ratio above 16% to be able to \"!ninjadd\".")
        return 0
    add(userName, userCommand, 1)

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
    assignToCaptain = 0
    commandsToDelete = []
    counter = 0
    gameClass = ''
    medicsRemaining = 0
    for command in commandList:
        if command in classList:
            gameClass = command
            commandsToDelete.append(counter)
        elif command == 'captain':
            assignToCaptain = 1
            commandsToDelete.append(counter)
        counter += 1
    for i in reversed(commandsToDelete):
        del commandList[i]
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
    team = getTeam(getOppositeTeam(captainStageList[captainStage]))
    oppositeTeamHasMedic = 0
    for i in range(len(team)):
        if 'medic' in team[i]['class']:
            oppositeTeamHasMedic = 1
    for user in userList.copy():
        if 'medic' in userList[user]['class']:
            medicsRemaining = medicsRemaining + 1
    if not assignToCaptain and counter == 3:
        send("NOTICE " + userName + " : Error, your command has 3 parameters but doesn't contain the word \"captain\". Did you try to set your pick as a captain?")
        return 0
    if lastGameType != 'scrim' and not oppositeTeamHasMedic and medicsRemaining == 1 and 'medic' in userList[commandList[0]]['class']:
        send("NOTICE " + userName + " : Error, you can't pick the last medic if you already have one.")
        return 0
    if not userFound:
        send("NOTICE " + userName + " : Error, this user doesn\'t exists.")
        return 0
    if gameClass == '':
        send("NOTICE " + userName + " : Error, you must specify a class from this list : " +  ', '.join(getRemainingClasses()) + ".")
        return 0
    if gameClass not in getRemainingClasses():
        send("NOTICE " + userName + " : This class is full, pick an other one from this list : " +  ', '.join(getRemainingClasses()))
        return 0
    if isAuthorizedCaptain(userName):
        send("NOTICE " + userName + " : You selected \"" + commandList[0] + "\" as \"" + gameClass + "\".")
        userList[commandList[0]]['status'] = ''
        if assignToCaptain:
            clearCaptainsFromTeam(getPlayerTeam(userName))
            userList[commandList[0]]['status'] = 'captain'
        assignUserToTeam(gameClass, 0, getPlayerTeam(userName), userList[commandList[0]])
        if captainStage < (len(captainStageList) - 1):
            captainStage += 1
            printCaptainChoices()
        else:
            startGame()
    else:
        send("NOTICE " + userName + " : It is not your turn, or you are not authorized to pick a player.") 

def players(userName):
    printCaptainChoices('channel')

def pubmsg(connection, event):
    analyseCommand(connection, event)

def printCaptainChoices(printType = 'private'):
    global classList, captainStage, captainStageList, userList
    if printType == 'private':
        captainName = getCaptainNameFromTeam(captainStageList[captainStage])
        color = '\x0312'
        followingColor = '\x035'
        dataPrefix = "NOTICE " + captainName + " : "
        send(dataPrefix + captainName + ", you are captain of a team and it's your turn to pick a player. Type \"!pick nick class\" to add somebody in your team.") 
        send(dataPrefix + "Remaining classes : " +  ', '.join(getRemainingClasses())) 
    else:
        color = '\x038,01'
        followingColor = '\x030,01'
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
        captain = ''
        if userList[userName]['status'] == 'captain':
            captain = color + 'C' + followingColor
        choiceList.append("(" + str(getPlayerNumber(userName)) + captain + ")" + userName)
    send(dataPrefix +  str(len(choiceList))+ " user(s) : " + ', '.join(choiceList)) 

def printSubs():
    global subList
    if len(subList):
        send("PRIVMSG " + channel + " :" + "\x037,01Substitute(s) needed:")
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
    printTeamsHandicaps()

def printTeamsHandicaps():
    if len(pastGames[len(pastGames) - 1]['players']) <= 6:
        return 0
    gamesPlayedCounter = [0, 0]
    handicapTotal = [0, 0]
    for user in pastGames[len(pastGames) - 1]['players']:
        stats = getWinStats(user['nick'])
        if stats:
            gamesPlayed = stats[1]
            handicap = stats[2]
            if gamesPlayed > 20:
                handicap = (handicap * 20) / gamesPlayed
                gamesPlayed = 20
            if user['team'] == 'a':
                teamIndex = 0
            else:
                teamIndex = 1
            gamesPlayedCounter[teamIndex] = gamesPlayedCounter[teamIndex] + gamesPlayed
            handicapTotal[teamIndex] = handicapTotal[teamIndex] + handicap
    winRatioOverall = [0, 0]
    for teamIndex in range(2):
        if gamesPlayedCounter[teamIndex] == 0:
            winRatioOverall[teamIndex] = 0
        else:
            winRatioOverall[teamIndex] = 100 * (float(handicapTotal[teamIndex] + gamesPlayedCounter[teamIndex]) / float(2 * gamesPlayedCounter[teamIndex]))
    print "Teams wins ratios : \x0311,01" + str(int(winRatioOverall[0])) + "%\x030,01 / \x034,01" + str(int(winRatioOverall[1])) + "%"

def printUserList():
    global lastUserPrint, printTimer, state, userList
    if (time.time() - lastUserPrint) > 5:
        message = "\x030,01" + str(len(userList)) + " user(s) subscribed :"
        for i, user in userList.copy().iteritems():
            captain = ''
            if user['status'] == 'captain':
                captain = '(\x038,01' + 'C' + '\x030,01)'
            message += ' "' + captain + user['nick'] + '"'
        send("PRIVMSG " + channel + " :" + message + ".")
    else:
        printTimer.cancel()
        printTimer = threading.Timer(5, printUserList)
        printTimer.start()
    lastUserPrint = time.time()

def prototype():
    print initTimer.isAlive()

def readPasswords():
    global rconPassword, tf2pbPassword
    passwordFile = open("passwords.txt")
    try:
        passwords = passwordFile.readline().replace('\n', '').split(':')
        rconPassword = passwords[1]
        tf2pbPassword = passwords[0]
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

def removeAwayUsers():
    global awayList, awayTimer
    for user in awayList:
        remove(user)
    awayList = {}
    awayTimer = time.time()
    updateUserStatus('', '')

def removeLastEscapeCharacter(userCommand):
    if userCommand[len(userCommand) - 1] == '\\':
        userCommand = userCommand[0:len(userCommand) - 1]
    return userCommand

def resetUserVariables():
    global userAuth, userInfo, userName
    userAuth = []
    userChannel = []
    userInfo = []

def resetVariables():
    global allowFriends, captainStage, captainStageList, gameServer, teamA, teamB, userLimit, userList
    allowFriends = 1
    captainStage = 0
    captainStageList = ['a', 'b', 'b', 'a', 'a', 'b', 'b', 'a', 'a', 'b'] 
    gameServer = ''
    teamA = []
    teamB = []
    userList = {}
    print 'Reset variables.'

def restartBot():
    global restart
    restart = 1

def saveStats():
    global connection, initTime
    teamName = ['\x0312blue\x031', '\x034red\x031']
    for teamID in ['a', 'b']:
        team = getTeam(teamID)
        for user in team:
            if len(user['class']) == 0:
                user['class'] = ['']
            cursor = connection.cursor()
            cursor.execute('INSERT INTO stats VALUES (%s, %s, %s, %s, %s)', (user['class'][0], user['nick'], "0", initTime, botID))
            cursor.execute('COMMIT;')

def scramble(userName, force = 0):
    global scrambleList, teamA, teamB, userList
    if len(teamA) == 0:
        send("NOTICE " + userName + " :Wait until the teams are drafted to use this command.")
        return 0
    if not startGameTimer.isAlive():
        send("NOTICE " + userName + " :You have a maximum of 1 minute after the teams got originally drafted to use this command.")
        return 0
    if (len(scrambleList) == 2 and userName not in scrambleList) or force:
        scrambleList = []
        teamA = []
        teamB = []
        pastGameIndex = len(pastGames) - 1
        for i in pastGames[pastGameIndex]['players']:
            userList[i['nick']] = i
        buildTeams()
        send("PRIVMSG " + channel + " :\x037,01Teams got scrambled.")
    elif userName not in scrambleList:
        scrambleList.append(userName)

def send(message, delay = 0):
    global connection
    cursor = connection.cursor()
    cursor.execute('INSERT INTO messages (message) VALUES (%s)', (message,))
    cursor.execute('COMMIT;')

def sendMessageToAwayPlayers():
    global awayList, awayTimer
    awayTimer = threading.Timer(60, removeAwayUsers).start()
    if len(awayList) > 1:
        words = ['These players are', 'they don\'t', 'they']
    else:
        words = ['This player is', 'he doesn\'t', 'he']
    nickList = []
    for nick in awayList:
        nickList.append(nick)
    send("PRIVMSG " + channel + " :\x037,01Warning!\x030,01 " + words[0] + " considered as inactive by the bot : " + ", ".join(nickList) + ". If " + words[1] +" show any activity in the next minute " + words[2] + " will automatically be removed from the player list.")
    for user in awayList:
        send("PRIVMSG " + user + ' :Warning, you are considered as inactive by the bot and a game you subscribed is starting. If you still want to play this game you have to type anything in the channel, suggestion "\x034!ready\x031". If you don\'t want to play anymore you can remove by typing "!remove". Notice that after 60 seconds you will be automatically removed.')

def sendStartPrivateMessages():
    color = ['\x0312', '\x034']
    teamName = ['\x0312blue\x031', '\x034red\x031']
    teamCounter = 0
    userCounter = 0
    for teamID in ['a', 'b']:
        team = getTeam(teamID)
        for user in team:
            send("PRIVMSG " + user['nick'] + " :You have been assigned to the " + teamName[teamCounter] + " team. Connect as soon as possible to this TF2 server : \"connect " + gameServer + "; password " + password + ";\". Connect as well to the voIP server, for more information type \"!mumble\" in \"#tf2.pug.na\". \x0307SteamLinker \x0301: tf://" + gameServer + "/" + password)
            userCounter += 1
        teamCounter += 1

def setStartMode(mode):
    global startMode
    startMode = mode

def startGame():
    global gameServer, initTime, state
    state = 'idle'
    if lastGameType != 'normal' and lastGameType != 'highlander':
        printTeams()
    initServer()
    saveStats()
    sendStartPrivateMessages()
    updateLast(string.split(gameServer, ':')[0], string.split(gameServer, ':')[1], initTime)

def stats(userName, userCommand):
    commandList = string.split(userCommand, ' ')
    cursor = connection.cursor()
    if len(commandList) < 2:
        if len(userList) == 0:
            send("PRIVMSG " + channel + ' :\x030,01There is no players added up at the moment.')
            return 0
        maximum = 0
        sorted = []
        stats = {}
        for player in userList.copy():
            print player
            cursor.execute('select lower(nick), count(*) from stats where nick ILIKE %s group by lower(nick);', (player,))
            result = cursor.fetchall()
            stats[player] = []
            if len(result) > 0:
                stats[player].append(result[0][1])
            else:
                stats[player].append(0)
            cursor.execute('select lower(nick), count(*) from stats where nick ILIKE %s and class = \'medic\' group by lower(nick);', (player,))
            result = cursor.fetchall()
            if len(result) > 0:
                stats[player].append(result[0][1])
            else:
                stats[player].append(0)
            if stats[player][1] > 0:
                stats[player][1] = int(float(stats[player][1]) / float(stats[player][0]) * float(100))
                if stats[player][1] > maximum:
                    maximum = stats[player][1]
            if stats[player][1] == maximum:
                sorted.insert(0, player)
            else:
                if len(sorted) > 0:
                    j = 0
                    sorted.reverse()
                    for i in sorted:
                        if stats[player][1] <= stats[i][1]:
                            sorted.insert(j, player)
                            break
                        j = j + 1
                    sorted.reverse()
        j = 0
        sorted.reverse()
        for i in sorted:
            sorted[j] = i + ' = ' + getMedicRatioColor(stats[i][1]) + str(stats[i][0]) + '/' + str(stats[i][1]) + '%\x030,01'
            j = j + 1
        send("PRIVMSG " + channel + ' :\x030,01Medic stats : ' + ", ".join(sorted) + '.')
        return 0
    cursor.execute('SELECT * FROM stats WHERE nick ILIKE %s AND botID = %s', (commandList[1], botID))
    counter = 0
    medicCounter = 0
    winCounter = 0
    for row in cursor.fetchall():
        last = row[3]
        if row[2] == 0:
            winCounter += .5
        elif row[2] == 1:
            winCounter += 1
        if row[0] == 'medic':
            medicCounter += 1
        counter += 1
    if counter == 0:
        send("PRIVMSG " + channel + ' :\x030,01No stats are available for the user "' + commandList[1] + '".')
        return 0
    medicRatio = int(float(medicCounter) / float(counter) * 100)
    winRatio = int(float(winCounter) / float(counter) * 100)
    color = getMedicRatioColor(medicRatio)
    print commandList[1] + ' played a total of ' + str(counter) + ' game(s), has a win ratio of ' + str(winRatio) +'% and has a medic ratio of ' + color + str(medicRatio) + '%\x030,01.'
    send("PRIVMSG " + channel + ' :\x030,01' + commandList[1] + ' played a total of ' + str(counter) + ' game(s) and has a medic ratio of ' + color + str(medicRatio) + '%\x030,01.')

def sub(userName, userCommand):
    global subList
    commandList = string.split(userCommand)
    id = ''
    for argument in commandList:
        if re.search('^[0-9]$', argument):
            id = argument
    if id == '' or getSubIndex(id) == -1:
        send("NOTICE " + userName + " :You must supply a valid substitute ID. Example : \"!sub 1\".")
        return 0
    subIndex = getSubIndex(id)
    send("PRIVMSG " + userName + " :You are the substitute for a game that is about to start or that has already started. Connect as soon as possible to this TF2 server : \"connect " + subList[subIndex]['server'] + "; password " + password + ";\". Connect as well to the voIP server, for more information type \"!mumble\" in \"#tf2.pug\".")
    del(subList[subIndex])
    return 0

def updateLast(ip, port, last):
    global botID, connection
    ip = getIPFromDNS(ip)
    cursor = connection.cursor()
    cursor.execute('UPDATE servers SET last = %s, botID = %s WHERE ip = %s and port = %s', (last, botID, ip, port))
    cursor.execute('COMMIT;')

def updateStats(address, port, score):
    global connection, pastGames
    cursor = connection.cursor()
    for i in reversed(range(len(pastGames))):
        if pastGames[i]['server'] == getIPFromDNS(address) + ':' + port or pastGames[i]['server'] == getDNSFromIP(address) + ':' + port:
            scoreList = score.split(':')
            scoreDict = {'a':0, 'b':1}
            if int(scoreList[0]) == int(scoreList[1]):
                scoreDict['a'] = 0
                scoreDict['b'] = 0
            elif int(scoreList[0]) > int(scoreList[1]):
                scoreDict['a'] = 1
                scoreDict['b'] = -1
            else:
                scoreDict['a'] = -1
                scoreDict['b'] = 1
            for player in pastGames[i]['players']:
                cursor.execute('UPDATE stats SET result = %s WHERE nick = %s AND time = %s', (str(scoreDict[player['team']]), player['nick'], pastGames[i]['time']))
            cursor.execute('COMMIT;')
            del(pastGames[i])

def updateUserStatus(nick, escapedUserCommand):
    global awayList, userList
    numberOfMedics = 2
    numberOfPlayers = 12
    if len(captainStageList) == 5:
        numberOfMedics = 1
        numberOfPlayers = 6
    elif getTeamSize() == 9:
        numberOfPlayers = 18
    if re.search('^\\\\!away', escapedUserCommand) and nick in userList:
        userList[nick]['last'] = time.time() - (10 * 60)
    else:
        if nick in userList:
            userList[nick]['last'] = time.time()
        if nick in awayList:
            del awayList[nick]
        if len(userList) >= numberOfPlayers and len(awayList) == 0 and classCount('medic') >= numberOfMedics:
            initGame()

def welcome(connection, event):
    global tf2pbPassword
    server.send_raw("authserv auth " + nick + " " + tf2pbPassword)
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
network = 'Gameservers.NJ.US.GameSurge.net'
port = 6667
channel = '#tf2.pug.na'
nick = 'PUG-BOT'
name = 'BOT'

adminCommands = ["\\!addgame", "\\!automatic", "\\!endgame", "\\!force", "\\!manual", "\\!needsub", "\\!prototype", "\\!replace", "\\!restart"]
allowFriends = 1
awayList = {}
awayTimer = 0.0
botID = 0
captainStage = 0
captainStageList = ['a', 'b', 'b', 'a', 'a', 'b', 'b', 'a', 'a', 'b'] 
classList = ['demo', 'medic', 'scout', 'soldier']
connectTimer = threading.Timer(0, None)
formalTeam = ['demo', 'medic', 'scout', 'scout', 'soldier', 'soldier']
gameServer = ''
gamesurgeCommands = ["\\!access", "\\!addcoowner", "\\!addmaster", "\\!addop", "\\!addpeon", "\\!adduser", "\\!clvl", "\\!delcoowner", "\\!deleteme", "\\!delmaster", "\\!delop", "\\!delpeon", "\\!deluser", "\\!deop", "\\!down", "\\!downall", "\\!devoice", "\\!giveownership", "\\!resync", "\\!trim", "\\!unsuspend", "\\!upall", "\\!uset", "\\!voice", "\\!wipeinfo"]
initTime = int(time.time())
initTimer = threading.Timer(0, None)
lastGame = 0
lastGameType = "captain"
lastLargeOutput = time.time()
lastUserPrint = time.time()
mapList = ["cp_badlands", "cp_granary", "cp_freight"]
minuteTimer = time.time()
nominatedCaptains = []
password = 'tf2pug'
pastGames = []
printTimer = threading.Timer(0, None)
rconPassword = ''
startMode = 'automatic'
state = 'idle'
teamA = []
teamB = []
restart = 0
scrambleList = []
startGameTimer = threading.Timer(0, None)
subList = []
tf2pbPassword = ''
userCommands = ["\\!add", "\\!addfriend", "\\!addfriends", "\\!away", "\\!captain", "\\!game", "\\!ip", "\\!last", "\\!limit", "\\!man", "\\!mumble", "\\!ninjadd", "\\!notice", "\\!pick", "\\!players", "\\!ready", "\\!remove", "\\!scramble", "\\!stats", "\\!sub", "\\!votemap", "\\!whattimeisit"]
userAuth = []
userChannel = []
userInfo = []
userLimit = 15
userList = {}
voiceServer = {'ip':'mumble.tf2pug.org', 'port':'64738'}
whoisEnded = 0

readPasswords()

#CREATE TABLE servers (dns varchar(255), ip varchar(255), last integer, port varchar(10), botID integer);
#CREATE TABLE stats (class varchar(255), nick varchar(255), result integer, time integer, botID integer);
connection = psycopg.connect('dbname=tf2pb host=localhost user=tf2pb password=' + tf2pbPassword)

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
    if time.time() - minuteTimer > 60:
        minuteTimer = time.time()
        checkConnection()
        printSubs()
        autoGameStart()

connectTimer.cancel()
