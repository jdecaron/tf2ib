#!/usr/bin/python

import config
import cookielib
import irclib
import json
import math
import psycopg2
import random
import re
import subprocess
import string
import SRCDS
import thread
import threading
import time
import urllib
import urllib2

def add(userName, userCommand, force=0):
    global state, userLimit, userList
    print "State : " + state
    if state != 'idle':
        authorizationStatus = getAuthorizationStatus(userName)
        if re.search('captain', userCommand):
            if authorizationStatus[1] == 0 and authorizationStatus[2] != 0:
                send("NOTICE " + userName + " : " + "You are restricted and may not captain.")
                return 0
        if state == 'captain' or state == 'normal':
            remove(userName, 0)
            if not classValidation(userName, userCommand):
                return 0
            if len(userList) == (userLimit -1) and classCount('medic') <= 1 and not isMedic(userCommand) and not isUser(userName):
                stats(userName, "!stats " + userName)
                send("NOTICE " + userName + " : Only class available is medic. Type \"!add medic\" to join this round.")
                return 0
            if len(userList) < userLimit:
                print "User add : " + userName + "  Command : " + userCommand
                userList[userName] = createUser(userName, userCommand, authorizationStatus[1], force)
                printUserList()
            if len(userList) >= (getTeamSize() * 2) and classCount('medic') > 1:
                if classCount('demo') < 2 or classCount('scout') < 4 or classCount('roamer') < 2 or classCount('pocket') < 2:
                    return 0
                if state == 'captain' and countCaptains() < 2:
                    send("PRIVMSG " + config.channel + " :\x037,01Warning!\x030,01 PUG needs 2 captains to start.")
                    return 0
                if len(findAwayUsers()) == 0:
                    initGame()
                elif type(awayTimer).__name__ == 'float':
                    sendMessageToAwayPlayers()
        elif state == 'picking':
            if initTimer.isAlive() or force:
                if not classValidation(userName, userCommand):
                    return 0
                if isInATeam(userName):
                    return 0
                if isUser(userName):
                    if (classCount('demo') < 3 or classCount('medic') < 3 or classCount('scout') < 5 or classCount('pocket') < 3 or classCount('roamer') < 3):
                        return 0
                userList[userName] = createUser(userName, userCommand, authorizationStatus[1], force)
                printUserList()
            else:
                send("NOTICE " + userName + " : You can't add during the picking process.")
                return 0
    else:
        send("PRIVMSG " + config.channel + " :\x030,01You can't \"!add\" until an admin has started a game.")

def addGame(userName, userCommand):
    resetVariables()
    global classList, gameServer, lastGameType, state, surferList, userLimit
    if not setIP(userName, userCommand):
        return 0
    classList = ['demo', 'medic', 'scout', 'pocket', 'roamer']
    if re.search('captain', userCommand):
        lastGameType = 'captain'
        state = 'captain'
        userLimit = 24
        surferListCopy = surferList.copy()
        for surfer in surferListCopy:
            add(surfer, surferListCopy[surfer]['command'])
        surferList = {}
    else:
        lastGameType = 'normal'
        state = 'normal'
        userLimit = 12
    updateLast(gameServer.split(':')[0], gameServer.split(':')[1], -(time.time()))
    send("PRIVMSG " + config.channel + ' :\x030,01PUG started. Game type : ' + state + '. Type "!add" to join a game.')

def analyseIRCText(connection, event):
    global adminList, userList
    userName = extractUserName(event.source())
    userCommand = event.arguments()[0]
    escapedChannel = cleanUserCommand(config.channel).replace('\\.', '\\\\.')
    escapedUserCommand = cleanUserCommand(event.arguments()[0])
    saveToLogs("[" + time.ctime() + "] <" + userName + "> " + userCommand + "\n")
    if isUser(userName):
        updateUserStatus(userName, escapedUserCommand)
    if re.match('^.*\\\\ \\\\\(.*\\\\\)\\\\ has\\\\ access\\\\ \\\\\x02\d*\\\\\x02\\\\ in\\\\ \\\\' + escapedChannel + '\\\\.$', escapedUserCommand):
        lvl = int(userCommand.split()[4].replace('\x02', ''))
        if lvl > 199:
            adminList[userCommand.split()[0]] = lvl
    if re.match('^\\\\!', escapedUserCommand):
        if isAdminCommand(userName, escapedUserCommand):
            if isAdmin(userName):
                executeCommand(userName, escapedUserCommand, userCommand)
            else:
                send("PRIVMSG " + config.channel + " :\x030,01Warning " + userName + ", you are trying an admin command as a normal user.")
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
        send("PRIVMSG " + config.channel + ' :\x030,01Captains are \x0311,01' + teamA[0]['nick'] + '\x030,01 and \x034,01' + teamB[0]['nick'] + "\x030,01.")
    printCaptainChoices()

def assignUserToTeam(gameClass, recursiveFriend, team, user):
    global pastGames, teamA, teamB, userList
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
    if len(getTeam(team)) < getTeamSize():
        getTeam(team).append(user)
    else:
        getTeam(getOppositeTeam(team)).append(user)
    pastGames[len(pastGames) - 1]['players'].append(userList[user['nick']])
    del userList[user['nick']]
    return 0

def authorize(userName, userCommand, userLevel = 1):
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        send("NOTICE " + userName + " : Error, your command has too few arguments. Here is an example of a valid \"!authorize\" command : \"!authorize nick\".")
        return 0
    adminLevel = isAdmin(userName)
    if userLevel > 1 and adminLevel < 300:
        send("NOTICE " + userName + " : Error, you lack access to this command.") 
        return 0
    if len(commandList) == 3 and commandList[2] != '' and re.match('^\d*$', commandList[2]) and int(commandList[2]) <= adminLevel:
        adminLevel = int(commandList[2])
    elif adminLevel > 200:
        adminLevel = 200
    authorizationStatus = getAuthorizationStatus(commandList[1])
    authorizationText = ''
    if userLevel == 0:
        authorizationText = 'restricted'
    elif userLevel == 1:
        authorizationText = 'authorized'
    else:
        authorizationText = 'invited'
    if(authorizationStatus[2] > adminLevel):
        send("NOTICE " + userName + " : Error. Another admin with a higher level already authorized or restricted him. Please, don't authorize this user under another alias, respect the level system.") 
        return 0
    else:
        cursor = connection.cursor()
        if authorizationStatus[4] != '':
            cursor.execute('UPDATE authorizations SET authorized=%s, level=%s, time=%s, admin=%s WHERE nick=lower(%s)', (userLevel, adminLevel, time.time(), userName, commandList[1]))
        else:
            cursor.execute('INSERT INTO authorizations VALUES (lower(%s), %s, %s, %s, %s)', (commandList[1], userLevel, adminLevel, time.time(), userName))
        cursor.execute('COMMIT;')
        send("NOTICE " + userName + " : You successfully " + authorizationText + " \"" + commandList[1] + "\" to play in \"" + config.channel + "\".") 

def autoGameStart():
    global lastGameType
    if state == 'idle':
        server = getAvailableServer()
        print server
    else:
        return 0
    cursor = connection.cursor()
    cursor.execute('UPDATE servers SET last = 0 WHERE last < 0 AND botID = %s', (botID,))
    cursor.execute('COMMIT;')
    if server and startMode == 'automatic':
        if lastGameType == 'captain':
            lastGameType = 'normal'
        elif lastGameType == 'normal':
            lastGameType = 'captain'
        addGame(nick, '!addgame ' + lastGameType + ' ' + server['ip'] + ':' + server['port'])
    
def buildTeams():
    global userList
    fullClassList = classList
    if getTeamSize() == 6:
        fullClassList = formalTeam
    totalAStats = 0.0
    totalBStats = 0.0
    for gameClass in fullClassList:
        playerA = getAPlayer(gameClass)
        playerB = getAPlayer(gameClass)
        while playerA == playerB:
            playerB = getAPlayer(gameClass)
        AStats = getWinStats(playerA)
        BStats = getWinStats(playerB)
        
        if AStats[4] < 50:
            AStats[3] = 0.375
        if BStats[4] < 50: 
            BStats[3] = 0.375
        
        if AStats == BStats:
            assignUserToTeam(gameClass, 0, 'a', userList[playerA])
            assignUserToTeam(gameClass, 0, 'b', userList[playerB])
        elif AStats > BStats:
            if totalAStats > totalBStats:
                assignUserToTeam(gameClass, 0, 'b', userList[playerA])
                assignUserToTeam(gameClass, 0, 'a', userList[playerB])
                totalAStats = totalAStats + BStats[3]
                totalBStats = totalBStats + AStats[3]
            else: 
                assignUserToTeam(gameClass, 0, 'a', userList[playerA])
                assignUserToTeam(gameClass, 0, 'b', userList[playerB])
                totalAStats = totalAStats + AStats[3]
                totalBStats = totalBStats + BStats[3]
        else:
            if totalAStats > totalBStats:
                assignUserToTeam(gameClass, 0, 'a', userList[playerA])
                assignUserToTeam(gameClass, 0, 'b', userList[playerB])
                totalAStats = totalAStats + AStats[3]
                totalBStats = totalBStats + BStats[3]
            else: 
                assignUserToTeam(gameClass, 0, 'b', userList[playerA])
                assignUserToTeam(gameClass, 0, 'a', userList[playerB])
                totalAStats = totalAStats + BStats[3]
                totalBStats = totalBStats + AStats[3]    
    printTeams()

def captain():
    global teamA, teamB
    if len(teamA) > 0 and len(teamA) < 6:
        for user in getTeam(captainStageList[captainStage]):
            if user['status'] == 'captain':
                captainName = user['nick']
                break
        send("PRIVMSG " + config.channel + ' :\x030,01Captain picking turn is to ' + captainName + '.')
    else:
        send("PRIVMSG " + config.channel + ' :\x030,01Picking process has not started yet.')

def checkConnection():
    global connectTimer
    if not server.is_connected():
        connect()
    server.join(config.channel)

def classCount(gameClass, listToUse = 'userList'):
    global surferList, userList
    if listToUse == 'userList':
        listToUse = userList
    else:
        listToUse = surferList
    counter = 0
    for i, j in listToUse.copy().iteritems():
        for userClass in listToUse[i]['class']:
            if userClass == gameClass:
                counter += 1
    return counter            

def classValidation(userName, userCommand, listToUse = 'userList'):
    userClass = extractClasses(userCommand)
    if len(userClass) == 0:
        send("NOTICE " + userName + " : " + "Error! You need to specify a class. Example : \"!add scout\".")
        return 0
    availableClasses = getAvailableClasses(listToUse)
    if userClass[0] not in availableClasses:
        send("NOTICE " + userName + " : The class you specified is not in the available class list : " + ", ".join(availableClasses) + ".")
        return 0
    else:
        return 1

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

def countCaptains():
    userListCopy = userList.copy()
    counter = 0
    for user in userListCopy:
        if userListCopy[user]['status'] == 'captain':
            counter = counter + 1
    return counter

def connect():
    print [config.network, config.port, nick, name]
    server.connect(config.network, config.port, nick, ircname = name)

def createUser(userName, userCommand, userAuthorizationLevel, force=0):
    commandList = string.split(userCommand, ' ')
    user = {'authorization': userAuthorizationLevel, 'command':'', 'class':[], 'friends':{}, 'id':0, 'last':0, 'nick':'', 'remove':0, 'status':'', 'team':''}
    user['command'] = userCommand
    user['id'] = getNextPlayerID()
    user['last'] = time.time()
    user['class'] = extractClasses(userCommand)
    if re.search('captain', userCommand):
        if 'medic' not in user['class'] and getWinStats(userName)[4] < 50 and not force and userAuthorizationLevel < 2:
            send("NOTICE " + userName + " : " + "You need a minimum of 50 games played to captain.")
        else:
            user['status'] = 'captain'
    user['nick'] = userName
    if len(user['class']) > 0:
        send("NOTICE " + userName + " : " + "You successfully added as : " + ", ".join(user['class']) + ".")
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
    global startMode, ownerList
    if re.search('^\\\\!add$', escapedUserCommand) or re.search('^\\\\!add\\\\ ', escapedUserCommand):
        add(userName, userCommand)
        return 0
    elif re.search('^\\\\!addgame', escapedUserCommand):
        addGame(userName, userCommand)
        return 0
    elif re.search('^\\\\!admin', escapedUserCommand):
        report(userName, userCommand)
        return 0
    elif re.search('^\\\\!authorize', escapedUserCommand):
        authorize(userName, userCommand)
        return 0
    elif re.search('^\\\\!automatic', escapedUserCommand):
        setStartMode('automatic')
        send("NOTICE " + userName + " : " + "Mode set to Automatic.")
        return 0
    elif re.search('^\\\\!captain', escapedUserCommand):
        captain()
        return 0
    elif re.search('^\\\\!endgame', escapedUserCommand):
        send("NOTICE " + userName + " : " + "Current game ended.")
        endGame()
        return 0
    elif re.search('^\\\\!fadd', escapedUserCommand):
        if userName in ownerList:
            fadd(userName, userCommand)
        return 0
    elif re.search('^\\\\!force', escapedUserCommand):
        force(userName)
        return 0
    elif re.search('^\\\\!fremove', escapedUserCommand):
        fremove(userName, userCommand)
        return 0
    elif re.search('^\\\\!game', escapedUserCommand):
        game()
        return 0
    elif re.search('^\\\\!help$', escapedUserCommand):
        help()
        return 0
    elif re.search('^\\\\!invite', escapedUserCommand):
        invite(userName, userCommand)
        return 0
    elif re.search('^\\\\!ip', escapedUserCommand):
        ip(userName, userCommand)
        return 0
    elif re.search('^\\\\!last', escapedUserCommand):
        last()
        return 0
    elif re.search('^\\\\!limit', escapedUserCommand):
        limit(userName, userCommand)
        return 0
    elif re.search('^\\\\!list', escapedUserCommand):
        players(userName)
        return 0
    elif re.search('^\\\\!map$', escapedUserCommand):
        map()
        return 0
    elif re.search('^\\\\!man$', escapedUserCommand):
        help()
        return 0
    elif re.search('^\\\\!manual', escapedUserCommand):
        setStartMode('manual')
        send("NOTICE " + userName + " : " + "Mode set to Manual.")
        return 0
    elif re.search('^\\\\!mode', escapedUserCommand):
        send("NOTICE " + userName + " : " + "The current mode is " + startMode)
        return 0
    elif re.search('^\\\\!mumble', escapedUserCommand):
        mumble()
        return 0
    elif re.search('^\\\\!need$', escapedUserCommand) or re.search('^\\\\!need\\\\ ', escapedUserCommand):
        need(userName, userCommand)
        return 0
    elif re.search('^\\\\!needsub', escapedUserCommand):
        needsub(userName, userCommand)
        return 0
    elif re.search('^\\\\!pick', escapedUserCommand):
        pick(userName, userCommand)
        return 0
    elif re.search('^\\\\!players', escapedUserCommand):
        players(userName)
        return 0
    elif re.search('^\\\\!remove', escapedUserCommand):
        remove(userName)
        return 0
    elif re.search('^\\\\!report', escapedUserCommand):
        report(userName, userCommand)
        return 0
    elif re.search('^\\\\!restart', escapedUserCommand):
        restartBot(userName)
        return 0
    elif re.search('^\\\\!restrict', escapedUserCommand):
        restrict(userName, userCommand)
        return 0
    elif re.search('^\\\\!say', escapedUserCommand):
        if userName in ownerList:
            say(userCommand)
        return 0
    elif re.search('^\\\\!scramble', escapedUserCommand):
        scramble(userName)
        return 0
    elif re.search('^\\\\!stats', escapedUserCommand):
        stats(userName, escapedUserCommand)
        return 0
    elif re.search('^\\\\!status', escapedUserCommand):
        thread.start_new_thread(status, ())
        return 0
    elif re.search('^\\\\!sub', escapedUserCommand):
        sub(userName, userCommand)
        return 0
    elif re.search('^\\\\!surf$', escapedUserCommand) or re.search('^\\\\!surf\\\\ ', escapedUserCommand):
        surf(userName, userCommand)
        return 0
    elif re.search('^\\\\!surfer', escapedUserCommand):
        surfer(userName, userCommand)
        return 0
    elif re.search('^\\\\!update', escapedUserCommand):
        updateName(userName, userCommand)
        return 0
    elif re.search('^\\\\!updateforce', escapedUserCommand):
        updateName(userName, userCommand, 1)
        return 0
    elif re.search('^\\\\!whattimeisit', escapedUserCommand):
        send("PRIVMSG " + config.channel + " :\x038,01* \x039,01Hammertime \x038,01*")
        return 0
    elif re.search('^\\\\!who', escapedUserCommand):
        adminLevel = isAdmin(userName)
        if adminLevel < 300:
            rint = random.randint(0, 100)
            if rint < 53:
                send("PRIVMSG " + config.channel + " :\x038,01* \x039,01" + userName + " is a noob \x038,01*")
            elif rint < 60:
                send("PRIVMSG " + config.channel + " :\x038,01* \x039,01" + userName + " is a pro \x038,01*")
            elif rint < 80:
                send("PRIVMSG " + config.channel + " :\x038,01* \x039,01" + userName + " needs to be kicked \x038,01*")
            else:
                send("PRIVMSG " + config.channel + " :\x038,01* \x039,01" + userName + " needs to play medic more \x038,01*")
            return 0
        else:
            send("PRIVMSG " + config.channel + " :\x038,01* \x039,01" + userName + " is awesome \x038,01*")
            return 0

def extractClasses(userCommand):
    global classList
    classes = []
    commandList = string.split(userCommand, ' ')
    try:
        classes.append(list(set(commandList) & set(classList))[0])
    except IndexError:
        return classes
    return classes

def extractUserName(user):
    if user:
        return string.split(user, '!')[0]
    else:
        return ''

def fadd(userName, userCommand):
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        return 0
    commandList[1] = commandList[1].replace("\\", "")
    add(commandList[1], userCommand, 1)
 
def findAwayUsers():
    global awayList, userList
    if type(awayTimer).__name__ == 'float' and time.time() - awayTimer <= (3 * 60):
        awayList = {}
    elif len(awayList) == 0:
        for user in userList:
            if userList[user]['status'] == 'captain':
                if userList[user]['last'] <= (time.time() - (5 * 60)):
                    awayList[user] = userList[user]
            elif userList[user]['last'] <= (time.time() - (20 * 60)):
                awayList[user] = userList[user]
    return awayList
    
def force(userName):
    scramble(userName, 1)

def fremove(userName, userCommand):
    commandList = string.split(userCommand, ' ')
    adminLevel = isAdmin(userName)
    if adminLevel < 250:
        return 0
    if len(commandList) < 2:
        send("NOTICE " + userName + " : Error, your command has too few arguments. Here is an example of a valid \"!fremove\" command : \"!fremove nick \".")
        return 0
    commandList[1] = commandList[1].replace("\\", "")
    print 'fremove triggered on ' + commandList[1]
    remove(commandList[1], 1, 1)
    
def game():
    send("PRIVMSG " + config.channel + " :\x030,01The game mode is set to \"" + state + "\".")
    return 0

def getAPlayer(playerType):
    global userList
    if playerType == 'captain':
        medicsCaptains = {}
        otherCaptains = {}
        statusCaptains = {}
        statusMedicsCaptains = {}
        userListCopy = userList.copy()
        for user in userListCopy:
            authorizationStatus = getAuthorizationStatus(user)
            print user
            print authorizationStatus
            print ''
            winStats = getWinStats(user)
            if userListCopy[user]['status'] == 'captain':
                otherCaptains[user] = winStats[4]
                if authorizationStatus[1] >= 2:
                    statusCaptains[user] = winStats[4]
                    if re.search('medic', userListCopy[user]['command']):
                        statusMedicsCaptains[user] = winStats[4]
                elif re.search('medic', userListCopy[user]['command']):
                    medicsCaptains[user] = winStats[4]
        if len(statusMedicsCaptains) > 0:
            player = userListCopy[getTopItemFromList(statusMedicsCaptains)]
        elif len(statusCaptains) > 0: 
            player = userListCopy[getTopItemFromList(statusCaptains)]
        elif len(medicsCaptains) > 0: 
            player = userListCopy[getTopItemFromList(medicsCaptains)]
        else: 
            player = userListCopy[getTopItemFromList(otherCaptains)]
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

def getAuthorizationStatus(userName):
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM authorizations WHERE nick ILIKE %s', [userName])
    for row in cursor.fetchall():
        return [userName, row[1], row[2], row[3], row[4]]
    return [userName, 0, 0, 0, '']

def getAvailableClasses(listToUse = 'userList'):
    availableClasses = []
    if userLimit == 12:
        numberOfPlayersPerClass = {'demo':2, 'medic':2, 'scout':4, 'pocket':2, 'roamer':2}
    elif userLimit == 24:
        numberOfPlayersPerClass = {'demo':4, 'medic':4, 'scout':8, 'pocket':4, 'roamer':4}
    for gameClass in classList:
        if classCount(gameClass, listToUse) < numberOfPlayersPerClass[gameClass]:
            availableClasses.append(gameClass)
    return availableClasses

def getAvailableServer():
    for server in getServerList():
        try:
            serverInfo = getServerInfo(server)
            for s in serverInfo['serverStatus'].strip().split("\n"):
                if re.search("^players", s):
                    serverInfo['playerCount'] = s.split(" ")[2]
            if 3 > int(serverInfo['playerCount']) and re.search("^Tournament is not live", serverInfo['tournamentInfo']) and (time.time() - server['last']) >= (60 * 15):
                print {'ip':server['dns'], 'port':server['port']}
                return {'ip':server['dns'], 'port':server['port']}
        except:
            print server['dns'] + ": error processing the server info"
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
    cursor.execute('SELECT lower(nick) as nick, medicgames, medicwins, totalgames FROM newstats WHERE nick ILIKE %s ORDER BY totalgames DESC LIMIT 1', [userName]) 
    for row in cursor.fetchall():
        try:
            medicStats['totalGamesAsMedic'] = row[1]
            medicStats['medicWinRatio'] = float(float(row[2]) / float(row[1]))
        except ZeroDivisionError:
            return {'totalGamesAsMedic':0, 'medicWinRatio':0}
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

def getServerInfo(server):
    try:
        TF2Server = SRCDS.SRCDS(server['ip'], int(server['port']), config.rconPassword, 10)
        serverStatus = TF2Server.rcon_command('status')
        serverStatus = re.sub(' +', ' ', serverStatus)
        tournamentInfo = TF2Server.rcon_command('tournament_info')
        return {'map':'', 'playerCount':'', 'serverStatus':serverStatus, 'tournamentInfo':tournamentInfo}
    except:
        return {'map':'', 'playerCount':'', 'serverInfo':0, 'serverStatus':0, 'tournamentInfo':0}

def getServerList():
    serverList = []
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM servers order by dns')
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
    return 6

def getTopItemFromList(list):
    maximumItem = 0
    maximumValue = 0
    for i in list:
        if list[i] >= maximumValue:
            maximumItem = i
            maximumValue = list[i]
    return maximumItem

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
    userName2 = userName.replace("\\", "")
    cursor = connection.cursor()
    cursor.execute('SELECT lower(nick) as nick, wins, (totalgames-wins) AS losses, totalgames FROM newstats WHERE nick ILIKE %s ORDER BY totalgames DESC limit 1', [userName2])
    for row in cursor.fetchall():
        try:
            return [row[0], row[1], row[2], float(float(row[1]) / float(row[3])), row[3]]
        except ZeroDivisionError:
            return [userName2, 0, 0, 0, 1]
    return [userName2, 0, 0, 0, 0]
    
def help():
    send("PRIVMSG " + config.channel + " :\x030,01If you need the help of an admin, type !admin. For any other help please visit \x0311,01http://steamcommunity.com/groups/tf2mix/discussions/0/882961586767057144/\x030,01 to read more about the PUG process.")
    send("PRIVMSG " + config.channel + " :\x030,01For any bug reports with the bot, contact cinq or speedy. For all other inquiries, please contact other admins.")

def invite(userName, userCommand):
    authorize(userName, userCommand, 3)

def ip(userName, userCommand):
    global gameServer
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        if gameServer != '':
            message = "\x030,01Server IP : \"connect " + gameServer + "; password " + password + ";\". Tragicservers is proud to support #tf2mix. Please visit: \x0307,01http://tragicservers.com/"
            send("PRIVMSG " + config.channel + " :" + message)
        return 0
    setIP(userName, userCommand)

def isAdmin(userName):
    global adminList
    server.send_raw("PRIVMSG ChanServ :" + config.channel + " a " + userName)
    counter = 0
    while not userName in adminList and counter < 20:
        irc.process_once(0.2)
        counter += 1
    print adminList
    if userName in adminList:
        return adminList[userName]
    else:
        return 0

def isAdminCommand(userName, userCommand):
    global adminCommands
    userCommand = string.split(userCommand, ' ')[0]
    userCommand = removeLastEscapeCharacter(userCommand)
    if userCommand in adminCommands:
        return 1
    return 0

def isAuthorizedCaptain(userName):
    global captainStage, captainStageList, teamA, teamB
    team = getTeam(captainStageList[captainStage])
    for user in team:
        if user['status'] == 'captain' and user['nick'] == userName:
            return 1
    return 0

def isAuthorizedToAdd(userName):
    authorizationStatus = getAuthorizationStatus(userName)
    winStats = getWinStats(userName)
    if authorizationStatus[1] > 0:
        return authorizationStatus[1]
    elif winStats[1] and authorizationStatus[2] == 0:
        return 1
    else:
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

def isUser(userName):
    if userName in userList:
        return 1
    else:
        return 0

def isUserCommand(userName, escapedUserCommand, userCommand):
    global userCommands
    escapedUserCommand = string.split(escapedUserCommand, ' ')[0]
    escapedUserCommand = removeLastEscapeCharacter(escapedUserCommand)
    if escapedUserCommand in userCommands:
        return 1
    return 0

def initGame():
    global gameServer, initTime, initTimer, nick, pastGames, scrambleList, startGameTimer, state, teamA, teamB, timerInfo
    if state == 'building' or state == 'picking':
        return 0
    initTime = int(time.time())
    pastGames.append({'players':[], 'server':gameServer, 'time':initTime})
    if state == "normal":
        scrambleList = []
        send("PRIVMSG " + config.channel + " :\x038,01Teams are being drafted, please wait in the channel until this process is over.")
        if countCaptains() < 2:
            send("PRIVMSG " + config.channel + " :\x037,01If you find teams unfair you can type \"!scramble\" and they will be adjusted (3 votes needed).")
            state = 'building'
            sendScramblingInvitation()
            initTimer = threading.Timer(20, buildTeams)
            initTimer.start()
            startGameTimer = threading.Timer(100, startGame)
            startGameTimer.start()
            timerInfo = int(time.time())
        else:
            state = 'picking'
            initTimer = threading.Timer(2, assignCaptains, ['captain'])
            initTimer.start()
            players(nick)
    elif state == "captain":
        if countCaptains() < 2:
            return 0
        send("PRIVMSG " + config.channel + " :\x038,01Teams are being drafted, please wait in the channel until this process is over.")
        state = 'picking'
        initTimer = threading.Timer(60, assignCaptains, ['captain'])
        initTimer.start()
        players(nick)
    restartServer()

def initServer():
    global gameServer, lastGame
    try:
        lastGame = time.time()
        TF2Server = SRCDS.SRCDS(string.split(gameServer, ':')[0], int(string.split(gameServer, ':')[1]), config.rconPassword, 10)
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
        send("PRIVMSG " + config.channel + " :\x030,010 matches have been played since the bot got restarted.")
        return 0
    message = "PRIVMSG " + config.channel + " :\x030,01"
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
    send("PRIVMSG " + config.channel + " :\x030,01The PUG's user limit is set to \"" + str(userLimit) + "\".")
    return 0

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
            if re.search('^!needsub', srcdsData[0]):
                needsub('', queryData[i][0])
                cursor.execute('DELETE FROM srcds WHERE time = %s', (queryData[i][1],))
                cursor.execute('COMMIT;')
            for pastGame in pastGames:
                if pastGame['server'] == server or pastGame['server'] == getDNSFromIP(ip) + ':' + port:
                    if re.search('^!gameover', srcdsData[0]):
                        score = srcdsData[1]
                        clearSubstitutes(ip, port)
                        updateLast(ip, port, 0)
                        print 'stats being updated...'
                        updateStats(ip, port, score)
                        send("PRIVMSG " + config.channel + " :\x030,01Game over on server \"" + getDNSFromIP(ip) + ":" + port + "\", final score is : \x0311,01" + score.split(':')[0] + "\x030,01 to \x034,01" + score.split(':')[1] + "\x030,01.")
                    cursor.execute('DELETE FROM srcds WHERE time = %s', (queryData[i][1],))
                    cursor.execute('COMMIT;')
            if time.time() - queryData[i][1] >= 20:
                cursor.execute('DELETE FROM srcds WHERE time = %s', (queryData[i][1],))
                cursor.execute('COMMIT;')

def map():
    send("PRIVMSG " + config.channel + " :\x030,01You can RTV and nominate once you are in the servers.")

def mumble():
    send("PRIVMSG " + config.channel + " :" + "\x030,01Voice server IP : " + voiceServer['ip'] + ":" + voiceServer['port'])
    send("PRIVMSG " + config.channel + " :" + "\x030,01Link to download Mumble : http://sourceforge.net/projects/mumble/")

def need(userName, params):
    neededClasses = {}
    numberOfPlayersPerClass = {'demo':2, 'medic':2, 'scout':4, 'pocket':2, 'roamer':2}
    neededPlayers = 0
    captainsNeeded = 0
    for gameClass in classList:
        if classCount(gameClass) < numberOfPlayersPerClass[gameClass]:
            needed = numberOfPlayersPerClass[gameClass] - classCount(gameClass)
            neededClasses[gameClass] = needed
            neededPlayers = neededPlayers + needed
    if state == 'captain' and countCaptains() < 2:
        captainsNeeded = 2 - countCaptains()
    if neededPlayers == 0 and captainsNeeded == 0:
        send("PRIVMSG %s :\x030,01no players needed." % (config.channel,))
    else:
        msg = ", ".join(['%s: %s' % (key, value) for (key, value) in neededClasses.items()])
        if state == 'captain' and countCaptains() < 2:
            msg = msg + ", captain: %d" % (captainsNeeded,)
        send("PRIVMSG %s :\x030,01%d player(s) needed: %s" % (config.channel, neededPlayers, msg))

def needsub(userName, userCommand):
    global classList, subList
    commandList = string.split(userCommand, ' ')
    sub = {'class':'unspecified', 'id':getNextSubID(), 'server':'', 'steamid':'', 'team':'unspecified'}
    for command in commandList:
        if re.search("[0-9a-z]*\.[0-9a-z]*:[0-9]+$", command):
            sub['server'] = re.findall("[0-9a-z]*\..*:[0-9]+", command)[0]
            sub['server'] = getDNSFromIP(sub['server'].split(':')[0]) + ':' + sub['server'].split(':')[1]
        if re.search("STEAM", command):
            sub['steamid'] = command
    if sub['server'] == '':
        send("NOTICE " + userName + " : You must set a server IP. Here is an example : \"!needsub 127.0.0.1:27015\".")
        return 0
    if 'blue' in commandList:
        sub['team'] = '\x0311,01Blue\x030,01'
    elif 'red' in commandList:
        sub['team'] = '\x034,01Red\x030,01'
    for argument in commandList:
        if argument in classList:
            sub['class'] = argument
    subList.append(sub)
    printSubs()

def nickchange(connection, event):
    global userList
    oldUserName = extractUserName(event.source())
    newUserName = event.target()
    if isUser(oldUserName):
        userList[newUserName] = userList[oldUserName]
        userList[newUserName]['nick'] = newUserName
        del userList[oldUserName]

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
    if re.search('^[0-9]+$', commandList[0]) and getPlayerName(int(commandList[0])):
        commandList[0] = getPlayerName(int(commandList[0]))
        userFound = 1
    elif 'random' in commandList[0]:
        if gameClass == '':
            send("NOTICE " + userName + " : Error, you must specify a class from this list : " +  ', '.join(getRemainingClasses()) + ".")
            return 0
        randomList = []
        for userN in userList.copy():
            if gameClass in userList[userN]['class']:
                randomList.append(userList[userN]['nick'])
        if len(randomList) > 0:
            rint = random.randint(0, len(randomList)-1)
            commandList[0] = randomList[rint]
        else:
            send("NOTICE " + userName + " : Error, there is no one remaining in that class.")
            return 0
        userFound = 1
    else:
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
    if not userFound:
        send("NOTICE " + userName + " : Error, this user doesn\'t exist.")
        return 0
    if not oppositeTeamHasMedic and medicsRemaining == 1 and 'medic' in userList[commandList[0]]['class']:
        send("NOTICE " + userName + " : Error, you can't pick the last medic if you already have one.")
        return 0
    if gameClass == '':
        send("NOTICE " + userName + " : Error, you must specify a class from this list : " +  ', '.join(getRemainingClasses()) + ".")
        return 0
    if gameClass not in userList[commandList[0]]['class']:
        send("NOTICE " + userName + " : You must pick the user as the class he added.")
        return 0
    if gameClass not in getRemainingClasses():
        send("NOTICE " + userName + " : This class is full, pick another one from this list : " +  ', '.join(getRemainingClasses()))
        return 0
    if isAuthorizedCaptain(userName):
        send("NOTICE " + userName + " : You selected \"" + commandList[0] + "\" as \"" + gameClass + "\".")
        userList[commandList[0]]['status'] = ''
        if assignToCaptain:
            clearCaptainsFromTeam(getPlayerTeam(userName))
            userList[commandList[0]]['status'] = 'captain'
        color = '\x0311,01'
        if captainStageList[captainStage] == 'b':
            color = '\x034,01'
        send("PRIVMSG " + config.channel + " :" + color + userName + " \x030,01picked " + color + commandList[0] + "\x030,01 as " + gameClass)
        assignUserToTeam(gameClass, 0, getPlayerTeam(userName), userList[commandList[0]])
        if captainStage < (len(captainStageList) - 1):
            captainStage += 1
            printCaptainChoices()
        else:
            startGame()
    else:
        send("NOTICE " + userName + " : It is not your turn, or you are not authorized to pick.") 

def players(userName):
    printCaptainChoices('channel')

def pubmsg(connection, event):
    analyseIRCText(connection, event)

def printCaptainChoices(printType = 'private'):
    global classList, captainStage, captainStageList, userList
    if printType == 'private':
        captainName = getCaptainNameFromTeam(captainStageList[captainStage])
        captainColor = '\x0312'
        followingColor = '\x035'
        dataPrefix = "NOTICE " + captainName + " : "
        send(dataPrefix + captainName + ", you are captain of a team and it's your turn to pick a player. Type \"!pick nick class\" to add somebody in your team.") 
        send(dataPrefix + "Remaining classes : " +  ', '.join(getRemainingClasses())) 
    else:
        captainColor = '\x038,01'
        followingColor = '\x030,01'
        dataPrefix = "PRIVMSG " + config.channel + " :\x030,01"
    for gameClass in classList:
        choiceList = []
        for userName in userList.copy():
            if gameClass in userList[userName]['class']:
                choiceList.append("(" + str(getPlayerNumber(userName)) + ")" + userName)
        if len(choiceList):
            send(dataPrefix + gameClass.capitalize() + "s: " + ', '.join(choiceList)) 
    choiceList = []
    for userName in userList.copy():
        captain = ''
        if userList[userName]['status'] == 'captain':
            captain = captainColor + 'C' + followingColor
        choiceList.append("(" + str(getPlayerNumber(userName)) + captain + ")" + userName)
    send(dataPrefix +  str(len(choiceList))+ " user(s) : " + ', '.join(choiceList)) 

def printSubs():
    global subList
    if len(subList):
        send("PRIVMSG " + config.channel + " :" + "\x037,01Substitute(s) needed:")
        for sub in subList:
            by = ''
            if sub['steamid'] != '':
                by = ", User = \"" + sub['steamid'] + "\""
            send("PRIVMSG " + config.channel + " :" + "\x030,01ID = \"" + str(sub['id']) + "\", Class = \"" + sub['class'].capitalize() + "\", Server = \"" + sub['server'] + "\", Team = \"" + sub['team'] + "\"" + by)

def printTeams():
    global captainStageList, state, teamA, teamB
    if len(captainStageList) >= 10:
        teamNames = ['Blue', 'Red']
        colors = ['\x0311,01', '\x034,01']
        teams = [teamA, teamB]
    counter = 0
    for i in teams:
        message = colors[counter] + teamNames[counter] + "\x030,01 : "
        for user in teams[counter]:
            gameClass = ''
            if user['class']:
                gameClass = " as " + colors[counter] + user['class'][0] + "\x030,01"
            message += '"' + user['nick'] + gameClass + '" '
        send("PRIVMSG " + config.channel + " :" + message)
        counter += 1

def printTeamsHandicaps():
    if len(pastGames[len(pastGames) - 1]['players']) <= 6:
        return 0
    gamesPlayedCounter = [0, 0]
    handicapTotal = [0, 0]
    for user in pastGames[len(pastGames) - 1]['players']:
        winStats = getWinStats(user['nick'])
        if winStats[1]:
            gamesPlayed = winStats[1]
            handicap = winStats[2]
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
   
def printUserList():
    global lastUserPrint, printTimer, state, userList
    if (time.time() - lastUserPrint) > 5:
        message = "\x030,01" + str(len(userList)) + " user(s) subscribed :"
        for i, user in userList.copy().iteritems():
            userStatus = ''
            if user['status'] == 'captain':
                userStatus = '(\x038,01C\x030,01'
            if userStatus != '':
                userStatus = userStatus + ')'
            message += ' "' + userStatus + user['nick'] + '"'
        send("PRIVMSG " + config.channel + " :" + message + ".")
    else:
        printTimer.cancel()
        printTimer = threading.Timer(5, printUserList)
        printTimer.start()
    lastUserPrint = time.time()

def remove(userName, printUsers = 1, force=0):
    global initTimer, state, userList
    if(isUser(userName)) and (state == 'picking' or state == 'building') and (force == 0):
        send("NOTICE " + userName + " : Warning, you removed but the teams are getting drafted at the moment and there are still some chances that you will get in this PUG. Make sure you clearly announce to the users in the channel and to the captains that you may need a substitute.")
        userList[userName]['remove'] = 1
    elif isUser(userName):
        del userList[userName]
        if state != 'picking':
            initTimer.cancel()
        if printUsers:
            printUserList()
    try:
        del surferList[userName]
    except:
        return 0

def removeAwayUsers():
    global awayList, awayTimer
    for user in awayList:
        remove(user)
    awayList = {}
    awayTimer = time.time()
    updateUserStatus('', '')

def removeUnremovedUsers():
    for user in userList.copy():
        if userList[user]['remove'] == 1:
            remove(user)

def removeLastEscapeCharacter(userCommand):
    if userCommand[len(userCommand) - 1] == '\\':
        userCommand = userCommand[0:len(userCommand) - 1]
    return userCommand

def report(userName, userCommand):
    thread.start_new_thread(sendSteamAnnouncement, (userName, userCommand))

def resetVariables():
    global captainStage, captainStageList, gameServer, teamA, teamB
    captainStage = 0
    captainStageList = ['a', 'b', 'a', 'b', 'b', 'a', 'a', 'b', 'b', 'a']
    gameServer = ''
    removeUnremovedUsers()
    teamA = []
    teamB = []
    print 'Reset variables.'

def restartBot(userName):
    adminLevel = isAdmin(userName)
    if adminLevel < 300:
        return 0
    global restart
    restart = 1

def restartServer():
    try:
        TF2Server = SRCDS.SRCDS(string.split(gameServer, ':')[0], int(string.split(gameServer, ':')[1]), config.rconPassword, 10)
        TF2Server.rcon_command('_restart')
    except:
        return 0

def restrict(userName, userCommand):
    authorize(userName, userCommand, 0)

def saveStats():
    global connection, initTime
    teamName = ['\x0312blue\x031', '\x034red\x031']
    for teamID in ['a', 'b']:
        team = getTeam(teamID)
        for user in team:
            if len(user['class']) == 0:
                user['class'] = ['']
            cursor = connection.cursor()
            winStats = getWinStats(user['nick'])
            try:
                if not winStats[4]:
                    if user['class'][0] == 'medic':
                        cursor.execute('INSERT INTO newstats VALUES (lower(%s), %s, %s, %s, %s, %s, %s, %s)', (user['nick'], "0", "0", "0", "0", initTime, botID, "1"))
                    else:
                        cursor.execute('INSERT INTO newstats VALUES (lower(%s), %s, %s, %s, %s, %s, %s, %s)', (user['nick'], "0", "0", "0", "0", initTime, botID, "0"))
                else:
                    if user['class'][0] == 'medic':
                        cursor.execute('UPDATE newstats SET time = %s, botid = %s, yes = %s WHERE nick = lower(%s)', (initTime, botID, "1", user['nick']))
                    else:
                        cursor.execute('UPDATE newstats SET time = %s, botid = %s, yes = %s WHERE nick = lower(%s)', (initTime, botID, "0", user['nick']))
                cursor.execute('COMMIT;')
            except:
                print '.'

def saveToLogs(data):
    logFile = open(config.channel.replace('#', '') + ".log", 'a')
    try:
        logFile.write(data)
    finally:
        logFile.close()

def say(userCommand):
    send("PRIVMSG " + config.channel + " :" + userCommand.split(' ',1)[1])
        
def scramble(userName, force = 0):
    global scrambleList, startGameTimer, teamA, teamB, timerInfo, userList
    if len(teamA) == 0:
        return 0
    if not startGameTimer.isAlive():
        send("NOTICE " + userName + " :There's no more time remaining to scramble the teams.")
        return 0
    found = 0
    pastGameIndex = len(pastGames) - 1
    for i in pastGames[pastGameIndex]['players']:
        if i['nick'] == userName:
            found = 1
    remainingTime = 0
    if (len(scrambleList) >= 2 and userName not in scrambleList and found) or force:
        if int(time.time()) - initTime >= 70:
            remainingTime = 40
            startGameTimer.cancel()
            startGameTimer = threading.Timer(40, startGame)
            startGameTimer.start()
            timerInfo = int(time.time())
        else:
            remainingTime = 100 - (int(time.time()) - initTime)
        scrambleList = []
        send("PRIVMSG " + config.channel + " :\x037,01Teams got scrambled, " + str(remainingTime) + " seconds remaining before teams are locked.")
        scrambleNew()
    elif userName not in scrambleList and found:
        scrambleList.append(userName)
    print scrambleList

def scrambleNew():
    global teamA, teamB, userList
    num = random.randint(2,3)
    switch = random.sample(classList,num) 
    for i in switch:
        playerList = []
        for j in teamA[:]:
            if j['class'][0] == i:
                playerList.append(j)
                teamA.remove(j)
        for j in teamB[:]:
            if j['class'][0] == i:
                playerList.append(j)
                teamB.remove(j)
        if i != 'scout': 
            teamA.append(playerList[1])
            teamB.append(playerList[0])
        else: 
            scoutList = list(playerList)
            while playerList == scoutList:
                random.shuffle(playerList)
            teamA.extend((playerList[0],playerList[1]))
            teamB.extend((playerList[2],playerList[3]))
    printTeams()
    
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
    send("PRIVMSG " + config.channel + " :\x038,01Warning!\x030,01 " + words[0] + " considered as inactive by the bot : " + ", ".join(nickList) + ". If " + words[1] +" show any activity in the next minute " + words[2] + " will automatically be removed from the player list.")
    for user in awayList:
        send("PRIVMSG " + user + ' :Warning, you are considered as inactive by the bot and a game you subscribed is starting. If you still want to play this game you have to type anything in the channel, suggestion "\x034!ready\x031". If you don\'t want to play anymore you can remove by typing "!remove". Notice that after 60 seconds you will be automatically removed.')

def sendScramblingInvitation():
    userListCopy = userList.copy()
    for user in userListCopy:
        print user
        send("PRIVMSG " + user + " :Teams are being drafted and you will be part of this next PUG, go in " + config.channel + " and look at the current teams, please scramble them if they look unfair.")

def sendStartPrivateMessages():
    color = ['\x0312', '\x034']
    teamName = ['\x0312blue\x03', '\x034red\x03']
    teamCounter = 0
    userCounter = 0
    for teamID in ['a', 'b']:
        team = getTeam(teamID)
        for user in team:
            send("PRIVMSG " + user['nick'] + " :You have been assigned to the " + teamName[teamCounter] + " team. Connect as soon as possible to this TF2 server : \"connect " + gameServer + "; password " + password + ";\". Connect as well to the voIP server, for more information type \"!mumble\" in \"#tf2mix\". \x0307SteamLinker : \x03tf://" + gameServer + "/" + password)
            userCounter += 1
        teamCounter += 1

def sendSteamAnnouncement(userName, userCommand):
    cookies = cookielib.CookieJar()
    data = urllib.urlencode({'username':'zerocinq', 'password':config.steamPassword, 'emailauth':'', 'captchagid':'-1', 'captcha_text':'', 'emailsteamid':''})
    site = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
    page = site.open('https://steamcommunity.com/login/home/')
    page = site.open('https://store.steampowered.com/login/getrsakey/?username=zerocinq')
    page = json.load(page)
    file = open("crypto.js", "w")
    file.write("var crypto = {\"publickey_mod\":\"" + page['publickey_mod'] + "\", \"publickey_exp\":\"" + page['publickey_exp'] + "\", \"password\":\"" + config.steamPassword + "\"}")
    file.close()
    steamPassword = subprocess.Popen(["js", "-f", "rsa.js"], stdout=subprocess.PIPE)
    steamPassword = steamPassword.stdout.readline()
    data = urllib.urlencode({'captcha_text':'', 'captchagid':'-1', 'emailauth':'', 'password':steamPassword, 'rsatimestamp':page['timestamp'], 'username':'zerocinq'})
    page = site.open('https://steamcommunity.com/login/dologin/', data)
    sessionid = ''
    for cookie in cookies:
        if cookie.name == 'sessionid':
            sessionid = urllib.unquote(cookie.value)
    data = urllib.urlencode({'action':'post', 'body':userCommand, 'headline':'Report by: ' + userName, 'sessionID':sessionid})
    page = site.open('http://steamcommunity.com/groups/thestick/announcements', data)
    send("NOTICE " + userName + " : You successfully reported to an admin, the next available one should contact you as soon as possible.")

def setIP(userName, userCommand):
    global gameServer
    if re.search("[0-9a-z]*\.[0-9a-z]*:[0-9]+", userCommand):
        gameServer = re.findall("[0-9a-z]*\..*:[0-9]+", userCommand)[0]
        return 1
    else:
        send("NOTICE " + userName + " : You must set a server IP. Here is an example : \"!add 127.0.0.1:27015\".")
        return 0

def setStartMode(mode):
    global startMode
    startMode = mode

def startGame():
    global gameServer, initTime, state
    state = 'idle'
    send("PRIVMSG " + config.channel + " :\x030,01Final teams for this pug are:")
    printTeams()
    initServer()
    saveStats()
    sendStartPrivateMessages()
    updateLast(string.split(gameServer, ':')[0], string.split(gameServer, ':')[1], initTime)
    autoGameStart()

def stats(userName, userCommand):
    commandList = string.split(userCommand.strip(), ' ')
    cursor = connection.cursor()
    if len(commandList) < 2:
        if len(userList) == 0:
            send("PRIVMSG " + config.channel + ' :\x030,01There is no players added up at the moment.')
            return 0
        maximum = 0
        sorted = []
        for player in userList.copy():
            sorted.append([player,getWinStats(player)[4],getMedicStats(player)['totalGamesAsMedic']])
            if sorted[-1][2] > 0: #calculates percentage of medic games
                sorted[-1][2] = int(float(sorted[-1][2]) / float(sorted[-1][1]) * float(100))
        sorted.sort(key=lambda factor: (factor[2],factor[1]))
        j = 0
        for i in sorted:
            sorted[j] = i[0] + ' = ' + getMedicRatioColor(i[2]) + str(i[1]) + '/' + str(i[2]) + '%\x030,01'
            j += 1
        send("PRIVMSG " + config.channel + ' :\x030,01Medic stats : ' + ", ".join(sorted))
        return 0
    if commandList[1] == 'me':
        commandList[1] = userName
    commandList[1] = commandList[1].replace("\\", "")
    authorizationStatus = getAuthorizationStatus(commandList[1])
    authorizedBy = ''
    medicStats = getMedicStats(commandList[1])
    winStats = getWinStats(commandList[1])
    if authorizationStatus[1] == 1:
        authorizationStatus = ' Authorized by ' + authorizationStatus[4] + '.'
    elif authorizationStatus[1] == 2:
        authorizationStatus = ' Authorized to surf by ' + authorizationStatus[4] + '.'
    elif authorizationStatus[1] == 3:
        authorizationStatus = ' Invited by ' + authorizationStatus[4] + '.'
    elif authorizationStatus[4] != '':
        authorizationStatus = ' Restricted by ' + authorizationStatus[4] + '.'
    else:
        authorizationStatus = ''
    if not winStats[4]:
        send("PRIVMSG " + config.channel + ' :\x030,01No stats are available for the user "' + commandList[1] + '".' + authorizationStatus)
        return 0
    medicRatio = int(float(medicStats['totalGamesAsMedic']) / float(winStats[4]) * 100)
    winRatio = int(winStats[3] * 100)
    color = getMedicRatioColor(medicRatio)
    print commandList[1] + ' played a total of ' + str(winStats[4]) + ' game(s), has a win ratio of ' + str(winRatio) +'% and has a medic ratio of ' + color + str(medicRatio) + '%\x030,01.'
    send("PRIVMSG " + config.channel + ' :\x030,01' + commandList[1] + ' played a total of ' + str(winStats[4]) + ' game(s) and has a medic ratio of ' + color + str(medicRatio) + '%\x030,01.' + authorizationStatus)

def status():
    issue = 0
    for server in getServerList():
        try:
            serverInfo = getServerInfo(server)
            for s in serverInfo['serverStatus'].strip().split("\n"):
                if re.search("^players", s):
                    serverInfo['playerCount'] = s.split(" ")[2]
                if re.search("^map", s):
                    serverInfo['map'] = s.split(" ")[2]
            if 3 <= int(serverInfo['playerCount']):
                if re.search("^Tournament is not live", serverInfo['tournamentInfo']):
                    send("PRIVMSG " + config.channel + " :\x030,01 " + server['dns'] + ": warmup on " + serverInfo['map'] + " with " + serverInfo['playerCount'] + " players")
                else:
                    serverInfo['tournamentInfo'] = serverInfo['tournamentInfo'].split("\"")
                    send("PRIVMSG " + config.channel + " :\x030,01 " + server['dns'] + ": \x0311,01" + serverInfo['tournamentInfo'][3].split(":")[0] + "\x030,01:\x034,01" + serverInfo['tournamentInfo'][3].split(":")[1] + "\x030,01 on " + serverInfo['map'] + " with " + serverInfo['tournamentInfo'][1] + " remaining")
            else:
                send("PRIVMSG " + config.channel + " :\x030,01 " + server['dns'] + ": empty")
        except:
            send("PRIVMSG " + config.channel + " :\x030,01 " + server['dns'] + ": error processing the status info")
            issue = 1
    if issue:
        send("PRIVMSG " + config.channel + " :\x030,01Server issue detected. Please contact eulogy_.")

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
    send("PRIVMSG " + userName + " :You are the substitute for a game that is about to start or that has already started. Connect as soon as possible to this TF2 server : \"connect " + subList[subIndex]['server'] + "; password " + password + ";\". Connect as well to the voIP server, for more information type \"!mumble\" in \"#tf2mix\".")
    del(subList[subIndex])
    remove(userName, 0, 0)
    return 0

def surf(userName, userCommand):
    if not classValidation(userName, userCommand, 'surferList') or not classValidation(userName, userCommand):
        return 0
    userAuthorizationLevel = isAuthorizedToAdd(userName)
    if userAuthorizationLevel < 2:
        winStats = getWinStats(userName)
        medicStats = getMedicStats(userName)
        if winStats[4] < 50 or float(medicStats['totalGamesAsMedic']) / float(winStats[4]) < 0.15:
            send("NOTICE " + userName + " : You do not meet the requirements to use the !surf command. You either need to have the surfer status or have at least 50 games played with a medic ratio above 15%.")
            return 0
    send("NOTICE " + userName + " : Enjoy the ride!")
    userList[userName] = createUser(userName, userCommand, userAuthorizationLevel)
    surferList[userName] = userList[userName]
    print surferList

def surfer(userName, userCommand):
    authorize(userName, userCommand, 2)

def updateName(userName, userCommand):
    commandList = string.split(userCommand.strip(), ' ')
    adminLevel = isAdmin(userName)
    if adminLevel < 250:
        send("NOTICE " + userName + " : You lack the admin privileges to use this command.") 
        return 0
    if len(commandList) < 3:
        send("NOTICE " + userName + " : Error, your command has too few arguments. Here is an example of a valid \"!update\" command : \"!update oldnick newnick\".") 
        return 0
    force = 0
    if 'force' in commandList[0]:
        force = 1
    commandList[1] = commandList[1].replace("\\", "")
    commandList[2] = commandList[2].replace("\\", "")
    if isAdmin(commandList[1]) > adminLevel:
        send("NOTICE " + userName + " : Nice try.") 
        return 0
    cursor = connection.cursor()
    if force:
        cursor.execute('DELETE FROM newstats WHERE nick ILIKE %s', [commandList[1]])
        cursor.execute('UPDATE newstats SET nick = lower(%s) WHERE nick ILIKE %s', (commandList[2],commandList[1]))
        cursor.execute('DELETE FROM authorizations WHERE nick ILIKE %s', [commandList[1]])
        cursor.execute('UPDATE authorizations SET nick = lower(%s) WHERE nick ILIKE %s', (commandList[2],commandList[1]))
        cursor.execute('COMMIT;')
        send("NOTICE " + userName + " : " + "Update name has been forced.")
    else:
        try:
            cursor.execute('UPDATE newstats SET nick = lower(%s) WHERE nick ILIKE %s', (commandList[2],commandList[1]))
        except:
            send("NOTICE " + userName + " : " + "The new nick is already in use in stats or the old nick does not exist.")
            
        else:
            send("NOTICE " + userName + " : " + "Nick successfully updated in stats.")
            cursor.execute('COMMIT;')
            try:
                cursor.execute('UPDATE authorizations SET nick = lower(%s) WHERE nick ILIKE %s', (commandList[2],commandList[1]))
            except:
                send("NOTICE " + userName + " : " + "The new nick is already in use in authorizations or the old nick does not exist.")
            else:
                send("NOTICE " + userName + " : " + "Nick successfully updated in authorizations.")
                cursor.execute('COMMIT;')
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
                print 'The player being updated: ' + player['nick']
                cursor.execute('SELECT yes FROM newstats WHERE nick = lower(%s) AND time = %s ORDER BY totalgames DESC LIMIT 1', (player['nick'], pastGames[i]['time']))
                for row in cursor.fetchall():
                    try:
                        if row[0] == 1:
                            if scoreDict[player['team']] == 1:
                                cursor.execute('UPDATE newstats SET totalgames = totalgames + 1, wins = wins + 1, medicgames = medicgames + 1, medicwins = medicwins +1 WHERE nick = lower(%s) AND time = %s', (player['nick'], pastGames[i]['time']))
                            else:
                                cursor.execute('UPDATE newstats SET totalgames = totalgames + 1, medicgames = medicgames + 1 WHERE nick = lower(%s) AND time = %s', (player['nick'], pastGames[i]['time']))
                        else:
                            if scoreDict[player['team']] == 1:
                                cursor.execute('UPDATE newstats SET totalgames = totalgames + 1, wins = wins + 1 WHERE nick = lower(%s) AND time = %s', (player['nick'], pastGames[i]['time']))
                            else:
                                cursor.execute('UPDATE newstats SET totalgames = totalgames + 1 WHERE nick = lower(%s) AND time = %s', (player['nick'], pastGames[i]['time']))
                        cursor.execute('COMMIT;')
                    except:
                        print "Updating stats for player: " + player['nick'] + " has failed."
            del(pastGames[i])

def updateUserStatus(nick, escapedUserCommand):
    global awayList, userList
    numberOfMedics = 2
    numberOfPlayers = 12
    if len(captainStageList) == 5:
        numberOfMedics = 1
        numberOfPlayers = 6
    if re.search('^\\\\!away', escapedUserCommand) and nick in userList:
        userList[nick]['last'] = time.time() - (10 * 60)
    else:
        if nick in userList:
            userList[nick]['last'] = time.time()
        if nick in awayList:
            del awayList[nick]
        if (state == 'captain' or state == 'normal') and (classCount('demo') < 2 or classCount('scout') < 4 or classCount('pocket') < 2 or classCount('roamer') < 2):
            return 0
        if len(userList) >= numberOfPlayers and len(awayList) == 0 and classCount('medic') >= numberOfMedics:
            initGame()

def welcome(connection, event):
    server.join(config.channel)

nick = 'PUGBOT'
name = 'BOT'

adminCommands = ["\\!addgame", "\\!authorize", "\\!automatic", "\\!fadd", "\\!endgame", "\\!force", "\\!fremove", "\\!invite", "\\!manual", "\\!mode", "\\!restart", "\\!restrict", "\\!surfer", "\\!update", "\\!updateforce"]
adminList = {}
ownerList = ["speedy", "speedygeek", "cinq", "cinqcinqcinq"]
awayList = {}
awayTimer = 0.0
botID = 0
captainStage = 0
captainStageList = ['a', 'b', 'a', 'b', 'b', 'a', 'a', 'b', 'b', 'a']
classList = ['demo', 'medic', 'scout', 'pocket', 'roamer']
connectTimer = threading.Timer(0, None)
formalTeam = ['demo', 'pocket', 'scout', 'roamer', 'medic', 'scout']
gameServer = ''
initTime = int(time.time())
initTimer = threading.Timer(0, None)
lastGame = 0
lastGameType = "normal"
lastLargeOutput = time.time()
lastUserPrint = time.time()
mapList = ["cp_badlands", "cp_gullywash_final1", "cp_snakewater_g7", "cp_granary", "cp_process_final"]
maximumUserLimit = 24
minuteTimer = time.time()
nominatedCaptains = []
password = 'tf2pug'
pastGames = []
printTimer = threading.Timer(0, None)
startMode = 'automatic'
state = 'idle'
teamA = []
teamB = []
restart = 0
scrambleList = []
startGameTimer = threading.Timer(0, None)
subList = []
surferList = {}
timerInfo = 0
userCommands = ["\\!add", "\\!admin", "\\!away", "\\!captain", "\\!game", "\\!help", "\\!ip", "\\!last", "\\!limit", "\\!list", "\\!man", "\\!map", "\\!mumble", "\\!need", "\\!needsub", "\\!notice", "\\!pick", "\\!players", "\\!remove", "\\!report", "\\!say", "\\!scramble", "\\!stats", "\\!status", "\\!sub", "\\!surf", "\\!whattimeisit", "\\!who"]
userLimit = 12
userList = {}
voiceServer = {'ip':'mumble.atf2.org', 'port':'64738'}

connection = psycopg2.connect('dbname=tf2ib host=127.0.0.1 user=tf2ib password=' + config.databasePassword)
irc = irclib.IRC()
server = irc.server()
connect()

irc.add_global_handler('dcc_disconnect', drop)
irc.add_global_handler('disconnect', drop)
irc.add_global_handler('kick', drop)
irc.add_global_handler('nick', nickchange)
irc.add_global_handler('part', drop)
irc.add_global_handler('pubmsg', pubmsg)
irc.add_global_handler('privnotice', pubmsg)
irc.add_global_handler('pubnotice', pubmsg)
irc.add_global_handler('quit', drop)
irc.add_global_handler('welcome', welcome)

thread.start_new_thread(listeningTF2Servers, ())

while not restart:
    irc.process_once(0.2)
    if time.time() - minuteTimer > 60:
        minuteTimer = time.time()
        checkConnection()
        printSubs()
        autoGameStart()

connectTimer.cancel()
