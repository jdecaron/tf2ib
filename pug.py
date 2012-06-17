#!/usr/bin/python

import config
import irclib
import math
import psycopg2
import random
import re
import string
import SRCDS
import thread
import threading
import time

#irclib.DEBUG = 1

def add(userName, userCommand, ninjAdd = 0):
    global state, userLimit, userList
    print "State : " + state
    userAuthorizationLevel = isAuthorizedToAdd(userName)
    if state != 'idle':
        winStats = getWinStats(userName)
        medicStats = getMedicStats(userName)
        print medicStats
        """if userAuthorizationLevel != 3 and not isMedic(userCommand) and (medicStats['totalGamesAsMedic'] == 0 or (float(medicStats['totalGamesAsMedic']) / float(winStats[4]) < 0.05)):
            send("NOTICE " + userName + " : In order to play in this channel you must have a medic ratio of 5% or higher.")
            return 0"""
        if not userAuthorizationLevel:
            send("NOTICE " + userName + " : You must be authorized by an admin to PUG here. Ask any peons or any admins to allow you the access to add to the PUGs. The best way to do it is by asking directly in the channel or by asking a friend that has the authorization to do it. If you used to have access, type \"!stats me\" in order to find who deleted your access and talk with him in order to get it back.")
            return 0
        if state == 'captain' or state == 'highlander' or state == 'normal':
            remove(userName, 0)
            if ((len(userList) == (userLimit -1) and classCount('medic') == 0) or (len(userList) == (userLimit -1) and classCount('medic') <= 1)) and not isMedic(userCommand):
                if not isUser(userName) and userAuthorizationLevel == 3:
                    userLimit = userLimit + 1
                elif not isUser(userName):
                    stats(userName, "!stats " + userName)
                    send("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join this round as this class.")
                    return 0
            if userAuthorizationLevel == 3 and not isUser(userName) and len(userList) == userLimit:
                userLimit = userLimit + 1
            if len(extractClasses(userCommand)) == 0:
                send("NOTICE " + userName + " : " + "Error! You need to specify a class. Example : \"!add scout\".")
                return 0
            elif len(extractClasses(userCommand)) > 1:
                send("NOTICE " + userName + " : " + "Error! You can only add as one class.")
                return 0
            elif extractClasses(userCommand)[0] not in getAvailableClasses():
                send("NOTICE " + userName + " : The class you specified is not in the available class list : " + ", ".join(getAvailableClasses()) + ".")
                return 0
            if len(userList) < userLimit:
                print "User add : " + userName + "  Command : " + userCommand
                userList[userName] = createUser(userName, userCommand, userAuthorizationLevel)
                printUserList()
            if len(userList) >= (getTeamSize() * 2) and classCount('medic') > 1:
                if classCount('demo') < 2 or classCount('scout') < 4 or classCount('soldier') < 3:
                    return 0
                if state == 'captain' and countCaptains() < 2:
                    send("PRIVMSG " + config.channel + " :\x037,01Warning!\x030,01 This PUG need 2 captains to start.")
                    return 0
                if len(findAwayUsers()) == 0:
                    initGame()
                elif type(awayTimer).__name__ == 'float':
                    sendMessageToAwayPlayers()
        elif state == 'scrim':
            if len(userList) == (userLimit - 2) and classCount('medic') == 0 and not isMedic(userCommand):
                send("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join this round as this class.")
                return 0
            print "User add : " + userName + "  Command : " + userCommand
            userList[userName] = createUser(userName, userCommand, userAuthorizationLevel)
            printUserList()
            if len(userList) >= 6 and classCount('medic') > 0:
                if len(findAwayUsers()) == 0:
                    initGame()
                elif type(awayTimer).__name__ == 'float':
                    sendMessageToAwayPlayers()
        elif state == 'picking':
            if initTimer.isAlive():
                if isInATeam(userName):
                    return 0
                if isUserCountOverLimit():
                    if userAuthorizationLevel == 1:
                        return 0
                    elif userAuthorizationLevel == 3 and not isUser(userName):
                        userLimit = userLimit + 1
                userList[userName] = createUser(userName, userCommand, userAuthorizationLevel)
                printUserList()
            else:
                send("NOTICE " + userName + " : You can't add during the picking process.")
                return 0
    else:
        send("PRIVMSG " + config.channel + " :\x030,01You can't \"!add\" until an admin has started a game.")

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
    if not setIP(userName, userCommand):
        return 0
    # Game type.
    if re.search('captain', userCommand):
        allowFriends = 0
        classList = ['demo', 'medic', 'scout', 'soldier']
        lastGameType = 'captain'
        state = 'captain'
        userLimit = 24
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
    send("PRIVMSG " + config.channel + ' :\x030,01PUG started. Game type : ' + state + '. Type "!add" to join a game.')

def analyseIRCText(connection, event):
    global adminList, userList
    userName = extractUserName(event.source())
    userCommand = event.arguments()[0]
    escapedChannel = cleanUserCommand(config.channel).replace('\\.', '\\\\.')
    escapedUserCommand = cleanUserCommand(event.arguments()[0])
    saveToLogs("[" + time.ctime() + "] <" + userName + "> " + userCommand + "\n")
    if userName in userList:
        updateUserStatus(userName, escapedUserCommand)
    if re.match('^.*\\\\ \\\\\(.*\\\\\)\\\\ has\\\\ access\\\\ \\\\\x02\d*\\\\\x02\\\\ in\\\\ \\\\' + escapedChannel + '\\\\.$', escapedUserCommand):
        adminList[userCommand.split()[0]] = int(userCommand.split()[4].replace('\x02', ''))
    if re.match('^\\\\!', escapedUserCommand):
    # Check if the user is trying to pass a command to the bot.
        if isAdminCommand(userName, escapedUserCommand):
            if isAdmin(userName):
            #Execute the admin command.
                executeCommand(userName, escapedUserCommand, userCommand)
            else :
            # Exit and report an error.
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
    elif mode == 'scrim':
        captain1 = getAPlayer('captain')
        assignUserToTeam(captain1['class'][0], 0, 'a', userList[captain1['nick']])
        send("PRIVMSG " + config.channel + ' :\x030,01Captain is \x0308,01' + teamA[0]['nick'] + '\x030,01.')
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

def authorize(userName, userCommand, userLevel = 1):
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        send("NOTICE " + userName + " : Error, your command has too few arguments. Here is an example of a valid \"!authorize\" command : \"!authorize nick level\". The level is a value ranging from 0 to 500.")
        return 0
    adminLevel = isAdmin(userName)
    if len(commandList) == 3 and commandList[2] != '' and re.match('^\d*$', commandList[2]) and int(commandList[2]) < adminLevel:
        adminLevel = int(commandList[2])
    authorizationStatus = getAuthorizationStatus(commandList[1])
    authorizationText = ''
    if userLevel == 0:
        authorizationText = 'restricted'
    elif userLevel == 1:
        authorizationText = 'authorized'
    elif userLevel == 2:
        authorizationText = 'protected'
    else:
        authorizationText = 'invited'
    if userLevel > 1 and adminLevel <= 250:
        send("NOTICE " + userName + " : Error, you lack access to this command.") 
        return 0
    if(authorizationStatus[2] > adminLevel):
        send("NOTICE " + userName + " : Error, you can't authorize this user because an other admin with a higher level already authorized or restricted him. And please, don't authorize this user under an other alias, respect the level system.") 
        return 0
    else:
        cursor = connection.cursor()
        cursor.execute('INSERT INTO authorizations VALUES (%s, %s, %s, %s, %s)', (commandList[1], userLevel, adminLevel, time.time(), userName))
        cursor.execute('COMMIT;')
        send("NOTICE " + userName + " : You successfully " + authorizationText + " \"" + commandList[1] + "\" to play in \"" + config.channel + "\".") 

def autoGameStart():
    global lastGameType
    if state == 'idle':
        server = getAvailableServer()
    else:
        return 0
    cursor = connection.cursor()
    cursor.execute('UPDATE servers SET last = 0 WHERE last < 0 AND botID = %s', (botID,))
    cursor.execute('COMMIT;')
    if lastGameType == 'captain':
        lastGameType = 'normal'
    elif lastGameType == 'normal':
        lastGameType = 'captain'
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
        send("PRIVMSG " + config.channel + ' :\x030,01Captain picking turn is to ' + captainName + '.')
    else:
        send("PRIVMSG " + config.channel + ' :\x030,01Picking process has not been started yet.')

def checkConnection():
    global connectTimer
    if not server.is_connected():
        connect()
    server.join(config.channel)

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

def countCaptains():
    userListCopy = userList.copy()
    counter = 0
    for user in userListCopy:
        if userListCopy[user]['status'] == 'captain':
            counter = counter + 1
    return counter

def countProtectedUsers():
    invitedCounter = 0
    protectedCounter = 0
    userListCopy = userList.copy()
    for user in userListCopy:
        if userListCopy[user]['authorization'] == 2:
            protectedCounter = protectedCounter + 1
        elif userListCopy[user]['authorization'] == 3:
            invitedCounter = invitedCounter + 1
    return [invitedCounter, protectedCounter]

def connect():
    print [config.network, config.port, nick, name]
    server.connect(config.network, config.port, nick, ircname = name)

def createUser(userName, userCommand, userAuthorizationLevel):
    commandList = string.split(userCommand, ' ')
    user = {'authorization': userAuthorizationLevel, 'command':'', 'class':[], 'friends':{}, 'id':0, 'last':0, 'late':0, 'nick':'', 'remove':0, 'status':'', 'team':''}
    user['command'] = userCommand
    user['id'] = getNextPlayerID()
    user['last'] = time.time()
    if (getUserCount() + 1) > 12:
        user['late'] = 1
    user['class'] = extractClasses(userCommand)
    if re.search('captain', userCommand):
        if 'medic' not in user['class'] and getWinStats(userName)[1] < 20:
            send("NOTICE " + userName + " : " + "You don't meet the requirements to be a captain : minimum of 20 games played.")
        else:
            user['status'] = 'captain'
    user['nick'] = userName
    if state == 'captain' or state == 'picking':
        if len(user['class']) > 0:
            send("NOTICE " + userName + " : " + "You sucessfully subscribed to the picking process as : " + ", ".join(user['class']) + ".")
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
    if re.search('^\\\\!authorize', escapedUserCommand):
        authorize(userName, userCommand)
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
    if re.search('^\\\\!invite', escapedUserCommand):
        invite(userName, userCommand)
        return 0
    if re.search('^\\\\!ip', escapedUserCommand):
        ip(userName, userCommand)
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
    if re.search('^\\\\!protect', escapedUserCommand):
        protect(userName, userCommand)
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
    if re.search('^\\\\!restrict', escapedUserCommand):
        restrict(userName, userCommand)
        return 0
    if re.search('^\\\\!scramble', escapedUserCommand):
        scramble(userName)
        return 0
    if re.search('^\\\\!stats', escapedUserCommand):
        stats(userName, userCommand)
        return 0
    if re.search('^\\\\!status', escapedUserCommand):
        thread.start_new_thread(status, ())
        return 0
    if re.search('^\\\\!sub', escapedUserCommand):
        sub(userName, userCommand)
        return 0
    if re.search('^\\\\!votemap', escapedUserCommand):
        #votemap(userName, escapedUserCommand)
        return 0
    if re.search('^\\\\!whattimeisit', escapedUserCommand):
        send("PRIVMSG " + config.channel + " :\x038,01* \x039,01Hammertime \x038,01*")
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
    if user:
        return string.split(user, '!')[0]
    else:
        return ''

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
        send("PRIVMSG " + config.channel + " :\x030,01The actual game mode is set to \"" + state + "\".")
        return 0
    elif not isAdmin(userName):
        send("PRIVMSG " + config.channel + " :\x030,01Warning " + userName + ", you are trying an admin command as a normal user.")
        return 0
    if mode[1] == 'captain':
        if state == 'scrim':
            captainStageList = ['a', 'b', 'a', 'b', 'b', 'a', 'a', 'b', 'b', 'a']
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
            maximum = 0
            otherCaptainWithMaximumRatio = ''
            for otherCaptain in otherCaptains:
                winStats = getWinStats(otherCaptain['nick'])
                if winStats[3] > maximum:
                    maximum = winStats[3]
                    otherCaptainWithMaximumRatio = otherCaptain['nick']
            if maximum > 0:
                player = userListCopy[otherCaptainWithMaximumRatio]
            else:
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

def getAuthorizationStatus(userName):
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM authorizations WHERE nick ILIKE %s AND time = (select MAX(time) FROM authorizations WHERE nick ILIKE %s)', (userName, userName))
    for row in cursor.fetchall():
        return [userName, row[1], row[2], row[3], row[4]]
    return [userName, 0, 0, 0, '']

def getAvailableClasses():
    availableClasses = []
    if userLimit == 12:
        numberOfPlayersPerClass = {'demo':2, 'medic':2, 'scout':4, 'soldier':4}
    elif userLimit == 24:
        numberOfPlayersPerClass = {'demo':4, 'medic':4, 'scout':8, 'soldier':8}
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
        medicStats['medicWinRatio'] = float((float(row[2]) + float(row[1])) / float(row[1] * 2))
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
        winStats = getWinStats(potentialNinjaddSpot[i]['nick'])
        ratio = 0
        if winStats:
            ratio = float(getMedicStats(potentialNinjaddSpot[i]['nick'])['totalGamesAsMedic']) / float(winStats[4])
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
    cursor.execute('SELECT lower(nick) AS nick, count(*), sum(result), (SELECT count(*) FROM stats WHERE nick ILIKE %s AND botID = %s) AS total FROM (SELECT * FROM stats WHERE nick ILIKE %s AND botID = %s ORDER BY TIME DESC LIMIT 20) AS stats GROUP BY lower(nick)', (userName, botID, userName, botID))
    for row in cursor.fetchall():
        return [row[0], row[1], row[2], float((float(row[2]) + float(row[1])) / float(row[1] * 2)), row[3]]
    return [userName, 0, 0, 0, 0]

def help():
    send("PRIVMSG " + config.channel + " :\x030,01Visit \x0311,01http://communityfortress.com/tf2/news/tf2pugna-released.php\x030,01 to get help about the PUG process.")

def invite(userName, userCommand):
    authorize(userName, userCommand, 3)

def ip(userName, userCommand):
    global gameServer
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        if gameServer != '':
            message = "\x030,01Server IP : \"connect " + gameServer + "; password " + password + ";\". Servers are provided by Command Channel : \x0307,01https://commandchannel.com/"
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

def isAuthorizedToAdd(userName):
    authorizationStatus = getAuthorizationStatus(userName)
    winStats = getWinStats(userName)
    if authorizationStatus[1] > 0:
        return authorizationStatus[1]
    elif winStats[1] and authorizationStatus[2] == 0:
        return 1
    else:
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

def isUser(userName):
    if userName in userList:
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

def initGame():
    global gameServer, initTime, initTimer, nick, pastGames, scrambleList, startGameTimer, state, teamA, teamB
    if state == 'building' or state == 'picking':
        return 0
    initTime = int(time.time())
    pastGames.append({'players':[], 'server':gameServer, 'time':initTime})
    if state == "normal" or state == "highlander":
        scrambleList = []
        send("PRIVMSG " + config.channel + " :\x038,01Teams are being drafted, please wait in the channel until this process is over.")
        send("PRIVMSG " + config.channel + " :\x037,01If you find teams unfair you can type \"!scramble\" and they will be adjusted.")
        state = 'building'
        initTimer = threading.Timer(20, buildTeams)
        initTimer.start()
        startGameTimer = threading.Timer(100, startGame)
        startGameTimer.start()
    elif state == "captain":
        if countCaptains() < 2:
            return 0
        send("PRIVMSG " + config.channel + " :\x038,01Teams are being drafted, please wait in the channel until this process is over.")
        state = 'picking'
        initTimer = threading.Timer(60, assignCaptains, ['captain'])
        initTimer.start()
        players(nick)
    elif state == "scrim":
        send("PRIVMSG " + config.channel + " :\x038,01Team is being drafted, please wait in the channel until this process is over.")
        state = 'picking'
        initTimer = threading.Timer(60, assignCaptains, ['scrim'])
        initTimer.start()
        players(nick)

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
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        send("PRIVMSG " + config.channel + " :\x030,01The PUG's user limit is set to \"" + str(userLimit) + "\".")
        return 0
    try:
        if not isAdmin(userName):
            send("PRIVMSG " + config.channel + " :\x030,01Warning " + userName + ", you are trying an admin command as a normal user.")
            return 0
        if int(commandList[1]) < 12:
            send("NOTICE " + userName + " : The limit value must be equal or above 12.")
            return 0
        if int(commandList[1]) > maximumUserLimit:
            send("NOTICE " + userName + " : The maximum limit is at " + str(maximumUserLimit) + ". And please, don't restart the bot or the PUG.")
            userLimit = 24
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
                        updateStats(ip, port, score)
                        send("PRIVMSG " + config.channel + " :\x030,01Game over on server \"" + getDNSFromIP(ip) + ":" + port + "\", final score is : \x0311,01" + score.split(':')[0] + "\x030,01 to \x034,01" + score.split(':')[1] + "\x030,01.")
                    cursor.execute('DELETE FROM srcds WHERE time = %s', (queryData[i][1],))
                    cursor.execute('COMMIT;')
            if time.time() - queryData[i][1] >= 20:
                cursor.execute('DELETE FROM srcds WHERE time = %s', (queryData[i][1],))
                cursor.execute('COMMIT;')

def mumble():
    global voiceServer
    message = "\x030,01Voice server IP : " + voiceServer['ip'] + ":" + voiceServer['port'] + "  Password : " + password + "  Download : http://downloads.sourceforge.net/project/mumble/Mumble/1.2.2/Mumble-1.2.2.exe"
    send("PRIVMSG " + config.channel + " :" + message)

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
    if not winStats or float(medicStats['totalGamesAsMedic']) / float(winStats[4]) < 0.16:
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
    if not userFound:
        send("NOTICE " + userName + " : Error, this user doesn\'t exists.")
        return 0
    if lastGameType != 'scrim' and not oppositeTeamHasMedic and medicsRemaining == 1 and 'medic' in userList[commandList[0]]['class']:
        send("NOTICE " + userName + " : Error, you can't pick the last medic if you already have one.")
        return 0
    if gameClass == '':
        send("NOTICE " + userName + " : Error, you must specify a class from this list : " +  ', '.join(getRemainingClasses()) + ".")
        return 0
    if gameClass not in userList[commandList[0]]['class']:
        send("NOTICE " + userName + " : You must pick the user as the class he added.")
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
        send("NOTICE " + commandList[0] + " : " + getCaptainNameFromTeam(getOppositeTeam(getPlayerTeam(userName))) + " picked you as " + gameClass) 
        send("NOTICE " + getCaptainNameFromTeam(getOppositeTeam(getPlayerTeam(userName))) + " : \x037" + userName + " picked " + commandList[0] + " as " + gameClass) 
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
    analyseIRCText(connection, event)

def printCaptainChoices(printType = 'private'):
    global classList, captainStage, captainStageList, userList
    if printType == 'private':
        captainName = getCaptainNameFromTeam(captainStageList[captainStage])
        captainColor = '\x0312'
        followingColor = '\x035'
        protectedColor = '\x033'
        dataPrefix = "NOTICE " + captainName + " : "
        send(dataPrefix + captainName + ", you are captain of a team and it's your turn to pick a player. Type \"!pick nick class\" to add somebody in your team.") 
        send(dataPrefix + "Remaining classes : " +  ', '.join(getRemainingClasses())) 
    else:
        captainColor = '\x038,01'
        followingColor = '\x030,01'
        protectedColor = '\x039,01'
        dataPrefix = "PRIVMSG " + config.channel + " :\x030,01"
    for gameClass in classList:
        choiceList = []
        for userName in userList.copy():
            if gameClass in userList[userName]['class']:
                protected = ''
                """if userList[userName]['authorization'] > 1 and printType == 'private':
                    protected = protectedColor + 'P' + followingColor"""
                choiceList.append("(" + str(getPlayerNumber(userName)) + protected + ")" + userName)
        if len(choiceList):
            send(dataPrefix + gameClass.capitalize() + "s: " + ', '.join(choiceList)) 
    choiceList = []
    for userName in userList.copy():
        captain = ''
        if userList[userName]['status'] == 'captain':
            captain = captainColor + 'C' + followingColor
        protected = ''
        """if userList[userName]['authorization'] > 1:
            protected = protectedColor + 'P' + followingColor"""
        choiceList.append("(" + str(getPlayerNumber(userName)) + captain + protected + ")" + userName)
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
        send("PRIVMSG " + config.channel + " :" + message)
        counter += 1
    printTeamsHandicaps()

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
    print "Teams wins ratios : \x0311,01" + str(int(winRatioOverall[0])) + "%\x030,01 / \x034,01" + str(int(winRatioOverall[1])) + "%"

def printUserList():
    global lastUserPrint, printTimer, state, userList
    if (time.time() - lastUserPrint) > 5:
        message = "\x030,01" + str(len(userList)) + " user(s) subscribed :"
        for i, user in userList.copy().iteritems():
            userStatus = ''
            if user['status'] == 'captain':
                userStatus = '(\x038,01C\x030,01'
            """if user['authorization'] > 1:
                if userStatus == '':
                    userStatus = '('
                userStatus = userStatus + '\x039,01P\x030,01'"""
            if userStatus != '':
                userStatus = userStatus + ')'
            message += ' "' + userStatus + user['nick'] + '"'
        send("PRIVMSG " + config.channel + " :" + message + ".")
    else:
        printTimer.cancel()
        printTimer = threading.Timer(5, printUserList)
        printTimer.start()
    lastUserPrint = time.time()

def protect(userName, userCommand):
    authorize(userName, userCommand, 2)

def prototype():
    print "prototype"

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

def remove(userName, printUsers = 1):
    global initTimer, state, userLimit, userList
    if(isUser(userName)) and (state == 'picking' or state == 'building'):
        send("NOTICE " + userName + " : Warning, you removed but the teams are getting drafted at the moment and there are still some chances that you will get in this PUG. Make sure you clearly announce to the users in the channel and to the captains that you may need a substitute.")
        userList[userName]['remove'] = 1
    elif isUser(userName):
        if isAuthorizedToAdd(userName) > 1 and userLimit > maximumUserLimit and isUser(userName):
            userLimit = userLimit - 1
        del userList[userName]
        initTimer.cancel()
        if printUsers:
            printUserList()


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

def resetVariables():
    global allowFriends, captainStage, captainStageList, gameServer, teamA, teamB, userLimit, userList
    allowFriends = 1
    captainStage = 0
    captainStageList = ['a', 'b', 'a', 'b', 'b', 'a', 'a', 'b', 'b', 'a']
    gameServer = ''
    removeUnremovedUsers()
    teamA = []
    teamB = []
    print 'Reset variables.'

def restartBot():
    global restart
    restart = 1

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
            cursor.execute('INSERT INTO stats VALUES (%s, %s, %s, %s, %s)', (user['class'][0], user['nick'], "0", initTime, botID))
            cursor.execute('COMMIT;')

def saveToLogs(data):
    logFile = open(config.channel.replace('#', '') + ".log", 'a')
    try:
        logFile.write(data)
    finally:
        logFile.close()

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
        send("PRIVMSG " + config.channel + " :\x037,01Teams got scrambled.")
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
    send("PRIVMSG " + config.channel + " :\x038,01Warning!\x030,01 " + words[0] + " considered as inactive by the bot : " + ", ".join(nickList) + ". If " + words[1] +" show any activity in the next minute " + words[2] + " will automatically be removed from the player list.")
    for user in awayList:
        send("PRIVMSG " + user + ' :Warning, you are considered as inactive by the bot and a game you subscribed is starting. If you still want to play this game you have to type anything in the channel, suggestion "\x034!ready\x031". If you don\'t want to play anymore you can remove by typing "!remove". Notice that after 60 seconds you will be automatically removed.')

def sendStartPrivateMessages():
    color = ['\x0312', '\x034']
    teamName = ['\x0312blue\x03', '\x034red\x03']
    teamCounter = 0
    userCounter = 0
    for teamID in ['a', 'b']:
        team = getTeam(teamID)
        for user in team:
            send("PRIVMSG " + user['nick'] + " :You have been assigned to the " + teamName[teamCounter] + " team. Connect as soon as possible to this TF2 server : \"connect " + gameServer + "; password " + password + ";\". Connect as well to the voIP server, for more information type \"!mumble\" in \"#tf2.pug.na\". \x0307SteamLinker : \x03tf://" + gameServer + "/" + password)
            userCounter += 1
        teamCounter += 1

def setIP(userName, userCommand):
    global gameServer
    # Game server.
    if re.search("[0-9a-z]*\.[0-9a-z]*:[0-9][0-9][0-9][0-9][0-9]", userCommand):
        gameServer = re.findall("[0-9a-z]*\..*:[0-9][0-9][0-9][0-9][0-9]", userCommand)[0]
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
            send("PRIVMSG " + config.channel + ' :\x030,01There is no players added up at the moment.')
            return 0
        maximum = 0
        sorted = []
        stats = {}
        for player in userList.copy():
            stats[player] = []
            stats[player].append(getWinStats(player)[4])
            stats[player].append(getMedicStats(player)['totalGamesAsMedic'])
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
        send("PRIVMSG " + config.channel + ' :\x030,01Medic stats : ' + ", ".join(sorted))
        return 0
    if commandList[1] == 'me':
        commandList[1] = userName
    authorizationStatus = getAuthorizationStatus(commandList[1])
    authorizedBy = ''
    medicStats = getMedicStats(commandList[1])
    winStats = getWinStats(commandList[1])
    if authorizationStatus[1] == 1:
        authorizationStatus = ' Authorized by ' + authorizationStatus[4] + '.'
    elif authorizationStatus[1] == 2:
        authorizationStatus = ' Protected by ' + authorizationStatus[4] + '.'
    elif authorizationStatus[1] == 3:
        authorizationStatus = ' Invited by ' + authorizationStatus[4] + '.'
    elif authorizationStatus[4] != '':
        authorizationStatus = ' Restricted by ' + authorizationStatus[4] + '.'
    else:
        authorizationStatus = ''
    if not winStats[1]:
        send("PRIVMSG " + config.channel + ' :\x030,01No stats are available for the user "' + commandList[1] + '".' + authorizationStatus)
        return 0
    medicRatio = int(float(medicStats['totalGamesAsMedic']) / float(winStats[4]) * 100)
    winRatio = int(winStats[3] * 100)
    color = getMedicRatioColor(medicRatio)
    print commandList[1] + ' played a total of ' + str(winStats[4]) + ' game(s), has a win ratio of ' + str(winRatio) +'% and has a medic ratio of ' + color + str(medicRatio) + '%\x030,01.'
    send("PRIVMSG " + config.channel + ' :\x030,01' + commandList[1] + ' played a total of ' + str(winStats[4]) + ' game(s) and has a medic ratio of ' + color + str(medicRatio) + '%\x030,01.' + authorizationStatus)

def status():
    for server in getServerList():
        try:
            TF2Server = SRCDS.SRCDS(server['ip'], int(server['port']), config.rconPassword, 10)
            serverInfo = {'map':'', 'playerCount':''}
            serverStatus = TF2Server.rcon_command('status')
            serverStatus = re.sub(' +', ' ', serverStatus)
            tournamentInfo = TF2Server.rcon_command('tournament_info')
            for s in serverStatus.strip().split("\n"):
                if re.search("^players", s):
                    serverInfo['playerCount'] = s.split(" ")[2]
                if re.search("^map", s):
                    serverInfo['map'] = s.split(" ")[2]
            if 3 <= int(serverInfo['playerCount']):
                if re.search("^Tournament is not live", tournamentInfo):
                    send("PRIVMSG " + config.channel + " :\x030,01 " + server['dns'] + ": warmup on " + serverInfo['map'] + " with " + serverInfo['playerCount'] + " players")
                else:
                    tournamentInfo = tournamentInfo.split("\"")
                    send("PRIVMSG " + config.channel + " :\x030,01 " + server['dns'] + ": \x0311,01" + tournamentInfo[3].split(":")[0] + "\x030,01:\x034,01" + tournamentInfo[3].split(":")[1] + "\x030,01 on " + serverInfo['map'] + " with " + tournamentInfo[1] + " remaining")
            else:
                send("PRIVMSG " + config.channel + " :\x030,01 " + server['dns'] + ": empty")
        except:
            send("PRIVMSG " + config.channel + " :\x030,01 " + server['dns'] + ": error processing the status info")

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
        if (state == 'captain' or state == 'normal') and (classCount('demo') < 2 or classCount('scout') < 4 or classCount('soldier') < 3):
            return 0
        if len(userList) >= numberOfPlayers and len(awayList) == 0 and classCount('medic') >= numberOfMedics:
            initGame()

def welcome(connection, event):
    server.send_raw("authserv auth " + nick + " " + config.gamesurgePassword)
    server.send_raw("MODE " + nick + " +x")
    server.join(config.channel)

# Connection information
nick = 'PUG-BOT'
name = 'BOT'

adminCommands = ["\\!addgame", "\\!authorize", "\\!automatic", "\\!endgame", "\\!force", "\\!invite", "\\!manual", "\\!prototype", "\\!replace", "\\!restart", "\\!restrict"]
adminList = {}
allowFriends = 1
awayList = {}
awayTimer = 0.0
botID = 0
captainStage = 0
captainStageList = ['a', 'b', 'a', 'b', 'b', 'a', 'a', 'b', 'b', 'a']
classList = ['demo', 'medic', 'scout', 'soldier']
connectTimer = threading.Timer(0, None)
formalTeam = ['demo', 'medic', 'scout', 'scout', 'soldier', 'soldier']
gameServer = ''
gamesurgeCommands = ["\\!access", "\\!addcoowner", "\\!addmaster", "\\!addop", "\\!addpeon", "\\!adduser", "\\!clvl", "\\!delcoowner", "\\!deleteme", "\\!delmaster", "\\!delop", "\\!delpeon", "\\!deluser", "\\!deop", "\\!down", "\\!downall", "\\!devoice", "\\!giveownership", "\\!resync", "\\!trim", "\\!unsuspend", "\\!upall", "\\!uset", "\\!voice", "\\!wipeinfo"]
initTime = int(time.time())
initTimer = threading.Timer(0, None)
lastGame = 0
lastGameType = "normal"
lastLargeOutput = time.time()
lastUserPrint = time.time()
mapList = ["cp_badlands", "cp_gullywash_final1", "cp_snakewater", "cp_granary"]
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
userCommands = ["\\!add", "\\!addfriend", "\\!addfriends", "\\!away", "\\!captain", "\\!game", "\\!ip", "\\!last", "\\!limit", "\\!man", "\\!mumble", "\\!ninjadd", "\\!needsub", "\\!notice", "\\!pick", "\\!players", "\\!protect", "\\!ready", "\\!remove", "\\!scramble", "\\!stats", "\\!status", "\\!sub", "\\!votemap", "\\!whattimeisit"]
userLimit = 12
userList = {}
voiceServer = {'ip':'tf2pug.commandchannel.com', 'port':'31472'}

connection = psycopg2.connect('dbname=tf2ib host=127.0.0.1 user=tf2ib password=' + config.databasePassword)

# Create an IRC object
irc = irclib.IRC()

# Create a server object, connect and join the channel
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
