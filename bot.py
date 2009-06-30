#!/usr/bin/python2.6

import irclib
import random
import re
import sqlite3
import string
import threading
import time

def add(userName, userCommand):
    global state, userList
    print "State : " + state
    if state != 'idle':
        if state == 'captain' or state == 'normal':
            # Debug : 10
            if len(userList) == 10 and classCount('medic') == 0 and not re.search('medic', userCommand, re.IGNORECASE):
                server.send_raw("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join this round as this class.")
                return 0
            # Debug : 11
            if len(userList) == 11 and classCount('medic') <= 1 and not re.search('medic', userCommand, re.IGNORECASE):
                server.send_raw("NOTICE " + userName + " : The only class available is medic. Type \"!add medic\" to join as this class.")
                return 0
            # Debug : 12
            if len(userList) < 12:
                print "User add : " + userName + "  Command : " + userCommand
                userList[userName] = createUser(userName, userCommand)
                printUserList()
            # Debug : 12
            if len(userList) == 12:
                initGame()
        elif state == 'picking':
            if isInATeam(userName):
                return 0
            userList[userName] = createUser(userName, userCommand)
            printUserList()
    else:
        server.privmsg(channel, "\x030,01You can't \"!add\" until an admin has started a game.")

def addFriend(userName, userCommand):
    global userList
    # 2 friends limit.
    commandList = string.split(userCommand, ' ')
    if len(commandList) > 1 and userName in userList:
        for i in range(1, len(commandList)):
            userList[userName]['friends'] = commandList[i]

def addGame(userName, userCommand):
    resetVariables()
    global allowFriends, gameServer, state
    # Game server.
    if re.search("[0-9a-z]*\.[0-9a-z]*:[0-9][0-9][0-9][0-9][0-9]", userCommand, re.IGNORECASE):
        gameServer = re.findall("[0-9a-z]*\..*:[0-9][0-9][0-9][0-9][0-9]", userCommand, re.IGNORECASE)[0]
    else:
        server.send_raw("NOTICE " + userName + " : You must set a server IP. Here is an example : \"!add 127.0.0.1:27015\".")
        return 0
    # Game type.
    if re.search('captain', userCommand, re.IGNORECASE):
        allowFriends = 0
        state = 'captain'
    else:
        state = 'normal'
    server.privmsg(channel, '\x030,01PUG started. Game type : ' + state + '. Type "!add" to join a game.')

def analyseCommand(connection, event):
    global lastCommand
    userName = extractUserName(event.source())
    if re.match('^!', event.arguments()[0]):
    # Check if the user is trying to pass a command to the bot.
        userCommand = event.arguments()[0]
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
                server.privmsg(channel, "\x030,01Warning " + userName + ", you are trying an admin command as a normal user.")
                return 1
        else :
        #Execute the user command.
            if isUserCommand(userName, userCommand):
                lastCommand = userCommand
                executeCommand(userName, userCommand)
                return 1
    return 0

def assignCaptains():
        global teamA, teamB
        assignUserToTeam('medic', 0, 'a', userList[getAPlayer('medic')])
        assignUserToTeam('medic', 0, 'b', userList[getAPlayer('medic')])
        teamA[0]['status'] = 'captain'
        teamB[0]['status'] = 'captain'
        server.privmsg(channel, '\x030,01Captains are \x0311,01' + teamA[0]['nick'] + '\x030,01 and \x034,01' + teamB[0]['nick'] + "\x030,01.")
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

def buildTeams():
    global allowFriends, state, userList
    state = 'idle'
    assignUserToTeam('medic', 1, 'a', userList[getAPlayer('medic')])
    assignUserToTeam('medic', 1, 'b', userList[getAPlayer('medic')])
    for i in range(10): #Debug : 10
        assignUserToTeam('', 1, 0, userList[getAPlayer('')])
    printTeams()

def classCount(gameClass):
    global userList
    counter = 0
    for i, j in userList.iteritems():
        for userClass in userList[i]['class']:
            if userClass == gameClass:
                counter += 1
    return counter            

def choices(userName):
    if isCaptain(userName) or isAdmin(userName):
        printCaptainChoices('channel')

def createUser(userName, userCommand):
    global classList, state
    commandList = string.split(userCommand, ' ')
    user = {'command':'', 'class':[], 'friends':{}, 'nick':'', 'status':'', 'team':''}
    user['command'] = userCommand
    user['class'] = extractClasses(userCommand)
    user['nick'] = userName
    if state == 'captain' or state == 'picking':
        if len(user['class']) > 0:
            server.send_raw("NOTICE " + userName + " : " + "You sucessfully subscribed to the picking process as : " + ", ".join(user['class']) + ".")
        else:
            server.send_raw("NOTICE " + userName + " : " + "You sucessfully subscribed to the picking process but you did not specify any valid class. Please specify one to help the captains chosing you as the right one.")
    return user

def endGame():
    global initTimer, state
    initTimer.cancel()
    state = 'idle'
    print 'PUG stopped.'

def endofwhois(connection, event):
    whoisEnded = 1

def executeCommand(userName, userCommand):
    if re.search('^!add$', userCommand, re.IGNORECASE) or re.search('^!add ', userCommand, re.IGNORECASE):
        add(userName, userCommand)
        return 0
    if re.search('^!addfriends*', userCommand, re.IGNORECASE):
        addFriend(userName, userCommand)
        return 0
    if re.search('^!addgame', userCommand, re.IGNORECASE):
        addGame(userName, userCommand)
        return 0
    if re.search('^!choices', userCommand, re.IGNORECASE):
        choices(userName)
        return 0
    if re.search('^!endgame', userCommand, re.IGNORECASE):
        endGame()
        return 0
    if re.search('^!man', userCommand, re.IGNORECASE):
        help()
        return 0
    if re.search('^!notice', userCommand, re.IGNORECASE):
        notice(userName)
        return 0
    if re.search('^!ip', userCommand, re.IGNORECASE):
        ip()
        return 0
    if re.search('^!pick', userCommand, re.IGNORECASE):
        pick(userName, userCommand)
        return 0
    if re.search('^!rating$', userCommand, re.IGNORECASE) or re.search('^!rating ', userCommand, re.IGNORECASE):
        rating(userName, userCommand)
        return 0
    if re.search('^!ratings', userCommand, re.IGNORECASE):
        ratings(userName)
        return 0
    if re.search('^!replace', userCommand, re.IGNORECASE):
        replace(userName, userCommand)
        return 0
    if re.search('^!remove', userCommand, re.IGNORECASE):
        remove(userName)
        return 0
    if re.search('^!restart', userCommand, re.IGNORECASE):
        restartBot()
        return 0
    if re.search('^!mumble', userCommand, re.IGNORECASE):
        mumble()
        return 0
    if re.search('^!vote', userCommand, re.IGNORECASE):
        vote(userName, userCommand)
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

def firstChoiceMedic(user):
    counter = 0
    for gameClass in userList[user]['class']:
        if gameClass == 'medic':
            break
        counter += 1
    if counter == 0:
        return 1
    return 0

def getAPlayer(gameClass):
    global userList
    for i in range(5):
        candidateList = []
        forcedList = []
        for user in userList:
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
    counter = 0
    for user in userList:
        if (counter + 1) == userNumber:
            return userList[user]['nick']
        counter += 1

def getPlayerNumber(userName):
    global userList
    counter = 1
    for i in userList:
        if i == userName:
            return counter
        counter += 1

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

def getTeam(team):
    global teamA, teamB
    if team == 'a':
        return teamA
    else:
        return teamB

def getUserRating(userName):
    whoisData = whois(userName)
    if whoisData and len(whoisData['info']) == 0:
        return []
    else:
        print whoisData
        if len(whoisData['auth']) > 0:
            cursor.execute('SELECT * FROM votes WHERE votedAuth = ?', (whoisData['auth'][1],))
        else:
            cursor.execute('SELECT * FROM votes WHERE votedIP = ?', (whoisData['info'][2],))
        numberOfVotes = 0
        sumOfAllVotes = 0
        for row in cursor:
            numberOfVotes += 1
            sumOfAllVotes += row[3]
        if numberOfVotes == 0:
            return []
        else:
            return {'numberOfVotes':numberOfVotes, 'sumOfAllVotes':sumOfAllVotes}

def help():
    server.privmsg(channel, "\x030,01Visit http://docs.google.com/View?id=d8zd3js_173hk3cb9c2 to get help about the PUG process.")

def ip():
    global gameServer
    if gameServer != '':
        message = "\x030,01Server IP : connect " + gameServer + "; password " + password + ";"
        server.privmsg(channel, message)

def isAdmin(userName):
    whoisData = whois(userName)
    if re.search('@' + channel + ' ', whoisData['channel']) or re.search('@' + channel + '$', whoisData['channel']):
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

def isGamesurgeCommand(userCommand):
    global gamesurgeCommands
    for command in gamesurgeCommands:
        if re.search("^" + command, userCommand, re.IGNORECASE):
            return 1
    return 0

def isUser(userName):
    if userName in userList:
        return 1
    else:
        return 0

def initGame():
    global initTimer, state, teamA, teamB
    print "Init game."
    if state == "normal":
        state = 'building'
        # Debug : 20
        initTimer = threading.Timer(20, buildTeams)
        initTimer.start()
    elif state == "captain":
        server.privmsg(channel, "\x030,01Teams are being drafted, please wait in the channel until this process's over.")
        state = 'picking'
        # Debug : 20
        initTimer = threading.Timer(20, assignCaptains)
        initTimer.start()

def isAdminCommand(userName, userCommand):
    global adminCommands
    userCommand = string.split(userCommand, ' ')[0]
    for i in adminCommands:
        if re.search('^' + userCommand + '$', i, re.IGNORECASE):
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
    server.send_raw("NOTICE " + userName + " : Invalid command : \"" + userCommand + "\". Type \"!man\" for usage commands.")
    return 0

def mumble():
    global voiceServer
    message = "\x030,01Voice server IP : " + voiceServer['ip'] + ":" + voiceServer['port'] + "  Password : " + password + "  Download : http://internap.dl.sourceforge.net/sourceforge/mumble/Mumble-1.1.8.exe"
    server.privmsg(channel, message)

def nickChange(connection, event):
    global userList
    oldUserName = extractUserName(event.source())
    newUserName = event.target()
    if oldUserName in userList:
        userList[newUserName] = userList[oldUserName]
        del userList[oldUserName]

def notice(userName):
    server.send_raw("NOTICE " + userName + " : Notice!!!!")

def pick(userName, userCommand):
    global captainStage, classList, state, teamA, teamB, userList
    if not len(teamA) or not len(teamB):
        server.send_raw("NOTICE " + userName + " : The selection is not started yet.") 
        return 0
    commandList = string.split(userCommand, ' ')
    if len(commandList) <= 2:
        server.send_raw("NOTICE " + userName + " : Error, your command has too few arguments. Here is an example of a valid pick command : \"!pick nick scout\".") 
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
    if re.search('^[0-9][0-9]*$', commandList[0]) and int(commandList[0]) > 0 and int(commandList[0]) <= len(userList):
        commandList[0] = getPlayerName(int(commandList[0]))
        userFound = 1
    else:
        # Check if this nickname exists in the player list.
        for user in userList:
            if userList[user]['nick'] == commandList[0]:
                userFound = 1
                break
    if not userFound:
        server.send_raw("NOTICE " + userName + " : Error, this user doesn\'t exists.") 
        return 0
    # Check if the captain specified a class.
    if gameClass == '':
        server.send_raw("NOTICE " + userName + " : Error, you must specify a class from this list : " +  ', '.join(getRemainingClasses()) + ".") 
        return 0
    if gameClass not in getRemainingClasses():
        server.send_raw("NOTICE " + userName + " : This class is full, pick an other one from this list : " +  ', '.join(getRemainingClasses())) 
        return 0
    if isAuthorizedCaptain(userName):
        assignUserToTeam(gameClass, 0, getPlayerTeam(userName), userList[commandList[0]])
        # Debug : 9
        if captainStage < 9:
            captainStage += 1
            printCaptainChoices()
        else:
            printTeams()
            state = 'idle'
            print 'send message to all users'
    else:
        server.send_raw("NOTICE " + userName + " : It is not your turn, or you are not authorized to pick a player") 

def privmsg(connection, event):
    if not analyseCommand(connection, event):
        server.privmsg(extractUserName(event.source()), "Type \"!man\" for usage commands. Otherwise, don't ask me anything that I can't answer, I'm just a PUG bot.")

def pubmsg(connection, event):
    analyseCommand(connection, event)

def printCaptainChoices(printType = 'private'):
    global classList, captainStage, captainStageList, userList
    print len(userList)
    if printType == 'private':
        captainName = getTeam(captainStageList[captainStage])[0]['nick']
        dataPrefix = "NOTICE " + captainName + " : "
        server.send_raw(dataPrefix + captainName + ", you are captain of a team and it's your turn to pick a player. Type \"!pick nick class\" to add somebody in your team.") 
        server.send_raw(dataPrefix + "Remaining classes : " +  ', '.join(getRemainingClasses())) 
    else:
        dataPrefix = "PRIVMSG " + channel + " :\x030,01 "
    for gameClass in classList:
        choiceList = []
        for userName in userList:
            if gameClass in userList[userName]['class']:
                choiceList.append("(" + str(getPlayerNumber(userName)) + ")" + userName)
        if len(choiceList):
            server.send_raw(dataPrefix + gameClass.capitalize() + "s: " + ', '.join(choiceList)) 
    choiceList = []
    for userName in userList:
        choiceList.append("(" + str(getPlayerNumber(userName)) + ")" + userName)
    server.send_raw(dataPrefix + "All players : " + ', '.join(choiceList)) 

def printTeams():
    global teamA, teamB
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
        server.privmsg(channel, message)
        counter += 1

def printUserList():
    global lastUserPrint, printTimer, state, userList
    if (time.time() - lastUserPrint) > 5:
        lastUserPrint = time.time()
        message = "\x030,01" + str(len(userList)) + " users subscribed : "
        for i, user in userList.iteritems():
            message += '"' + user['nick'] + '"  '
        server.privmsg(channel, message)
    else:
        printTimer.cancel()
        printTimer = threading.Timer(5, printUserList)
        printTimer.start()

def rating(userName, userCommand):
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        server.send_raw("NOTICE " + userName + " : Error, you must supply an user name to the \"!rating\" command.")
        return 0
    userRating = getUserRating(commandList[1])
    if len(userRating) == 0:
        server.send_raw("NOTICE " + userName + " : Error, the user \"" + commandList[1] + "\" doesn't exists in our database.")
        return 0
    else:
        server.privmsg(channel, "\x030,01The user \"" + commandList[1] + "\" is rated average " + str((userRating['sumOfAllVotes'] / userRating['numberOfVotes'])) + "/10 out of " + str(userRating['numberOfVotes']) + " votes.")

def ratings(userName):
    global userList
    if isCaptain(userName) or isAdmin(userName):
        badlyRatedUsers = []
        notRatedUsers = []
        wellRatedUsers = []
        for user in userList:
            rating = getUserRating(userList[user]['nick'])
            if len(rating):
                if (rating['sumOfAllVotes'] / rating['numberOfVotes']) >= 5:
                    wellRatedUsers.append('(' + str(getPlayerNumber(userList[user]['nick'])) + ')' + userList[user]['nick'])
                else:
                    badlyRatedUsers.append('(' + str(getPlayerNumber(userList[user]['nick'])) + ')' + userList[user]['nick'])
            else:
                notRatedUsers.append('(' + str(getPlayerNumber(userList[user]['nick'])) + ')' + userList[user]['nick'])
        if len(wellRatedUsers):
            server.privmsg(channel, "\x030,01Well rated players : " + ", ".join(wellRatedUsers))
        if len(badlyRatedUsers):
            server.privmsg(channel, "\x030,01Badly rated players : " + ", ".join(badlyRatedUsers))
        if len(notRatedUsers):
            server.privmsg(channel, "\x030,01Not rated players : " + ", ".join(notRatedUsers))

def replace(userName, userCommand):
    global userList
    teamList = ['a', 'b']
    commandList = string.split(userCommand, ' ')
    if len(commandList) < 2:
        server.send_raw("NOTICE " + userName + " : Error, there is not enough arguments in your replace command. Example : \"!replace toreplace substitute\".")
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
                break
            counter += 1
    if type(toReplace) == type({}):
        gameClass = toReplace['class']
        toReplace['class'] = extractClasses(toReplace['command'])
    else:
        server.send_raw("NOTICE " + userName + " : Error, the user you specified to replace is not listed in a team.")
    if substitute in userList:
        userList[substitute]['status'] = 'captain'
        assignUserToTeam(gameClass[0], 0, teamName, userList[substitute])
        print gameClass
        team[counter]['status'] = ''
        userList[team[counter]['nick']] = team[counter]
        del team[counter]
    else:
        server.send_raw("NOTICE " + userName + " : Error, the substitute you specified is not in subscribed list.")
    return 0

def remove(userName):
    global initTimer, state, userList
    print state
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
    global allowFriends, captainStage, gameServer, teamA, teamB, userList
    allowFriends = 1
    captainStage = 0
    gameServer = ''
    teamA = []
    teamB = []
    userList = {}
    print 'Reset variables.'

def restartBot():
    global restart
    restart = 1

def saveVote(votedWhoisData, voterWhoisData, vote):
    global connection, cursor
    votedAuth = ''
    votedIP = votedWhoisData['info'][2]
    voterIP = voterWhoisData['info'][2]
    if len(votedWhoisData['auth']):
        votedAuth = votedWhoisData['auth'][1]
        queryData = votedAuth, voterIP
        cursor.execute('SELECT * FROM votes WHERE votedAuth = ? AND voterIP = ?', queryData)
        if cursor.fetchone():
            queryData = vote, votedAuth, voterIP
            cursor.execute('UPDATE votes SET vote = ? WHERE votedAuth = ? AND voterIP = ?', queryData)
        else:
            queryData = votedIP, votedAuth, voterIP, vote
            cursor.execute('INSERT INTO votes VALUES (?, ?, ?, ?)', queryData)
    else:
        queryData = votedIP, voterIP
        cursor.execute('SELECT * FROM votes WHERE votedIP = ? AND voterIP = ?', queryData)
        if cursor.fetchone():
            queryData = vote, votedIP, voterIP
            cursor.execute('UPDATE votes SET vote = ? WHERE votedIP = ? AND voterIP = ?', queryData)
        else:
            queryData = votedIP, '', voterIP, vote
            cursor.execute('INSERT INTO votes VALUES (?, ?, ?, ?)', queryData)
    connection.commit()

def vote(userName, userCommand):
    global userInfo, whoisEnded
    #Validation of the user vote.
    commandList = string.split(userCommand, ' ')
    if len(commandList) == 3:
        if(re.search('^[0-9][0-9]*$', commandList[2]) and (int(commandList[2]) >= 0 and int(commandList[2]) <= 10)):
            vote = commandList[2]
            votedWhoisData = whois(commandList[1])
        else:
            server.privmsg(userName, "Error, the second argument of your \"!vote\" command must be a number of 0 to 10.")
            return 0
    else:
        server.privmsg(userName, "Your vote can't be registered, you don't have the right number of arguments in yout command. Here is an example of a correct vote command: \"!vote nickname 10\".")
        return 0
    if len(votedWhoisData['info']) > 0:
        voterWhoisData = whois(userName)
        saveVote(votedWhoisData, voterWhoisData, vote)
        server.privmsg(channel, "\x030,01" + userName + " rated " + commandList[1] + " " + vote + "/10.")
    else:
        server.privmsg(channel, "\x030,01" + userName + ", the user you voted for does not exist.")
        return 0

def welcome(connection, event):
    server.send_raw ("authserv auth " + nick + " password")
    server.send_raw ("MODE " + nick + " +x")
    server.join(channel)

def whois(userName):
    resetUserVariables()
    global userAuth, userChannel, userInfo, whoisEnded
    counter = 0
    whoisEnded = 0
    server.whois([userName])
    while not whoisEnded and counter < 10:
        irc.process_once(0.2)
        counter += 1
    return {'auth':userAuth, 'channel':userChannel, 'info':userInfo}

def whoisauth(connection, event):
    for i in event.arguments():
        userAuth.append(i)

def whoischannels(connection, event):
    global userChannel
    if re.search('#', event.arguments()[1]):
        userChannel = event.arguments()[1]
        return 0

def whoisuser(connection, event):
    global userInfo
    for i in event.arguments():
        userInfo.append(i)

# Connection information
network = '127.0.0.1'
port = 6667
channel = '#tf2.pug.na'
nick = 'PUG-BOT'
name = 'BOT'

adminCommands = ["!addgame", "!endgame", "!replace", "!restart"]
allowFriends = 1
captainStage = 0
captainStageList = ['a', 'b', 'a', 'b', 'a', 'b', 'a', 'b', 'a', 'b'] 
classList = ['demo', 'medic', 'scout', 'soldier']
formalTeam = ['demo', 'medic', 'scout', 'scout', 'soldier', 'soldier']
gameServer = ''
gamesurgeCommands = ["!access", "!addcoowner", "!addmaster", "!addop", "!addpeon", "!adduser", "!clvl", "!delcoowner", "!deleteme", "!delmaster", "!delop", "!delpeon", "!deluser", "!deop", "!down", "!downall", "!devoice", "!giveownership", "!resync", "!trim", "!unsuspend", "!upall", "!uset", "!voice", "!wipeinfo"]
lastCommand = ""
lastUserPrint = time.time()
nominatedCaptains = []
password = 'tf2pug'
state = 'idle'
teamA = []
teamB = []
printTimer = threading.Timer(0, None)
initTimer = threading.Timer(0, None)
restart = 0
userCommands = ["!add", "!addfriend", "!addfriends", "!choices", "!ip", "!man", "!mumble", "!notice", "!pick", "!rating", "!ratings", "!remove", "!vote"]
userAuth = []
userChannel = []
userInfo = []
userList = {}
voiceServer = {'ip':'mumble.tf2pug.org', 'port':'64738'}
whoisEnded = 0

#CREATE TABLE votes (votedIP varchar(255), votedAuth varchar(255), voterIP varchar(255), vote int)
connection = sqlite3.connect('./tf2pb.sqlite')
cursor = connection.cursor()

# Create an IRC object
irc = irclib.IRC()

# Create a server object, connect and join the channel
server = irc.server()
server.connect ( network, port, nick, ircname = name )

#irc.add_global_handler("all_events", all, -10)
irc.add_global_handler('endofwhois', endofwhois)
irc.add_global_handler('nick', nickChange)
irc.add_global_handler('privmsg', privmsg)
irc.add_global_handler('pubmsg', pubmsg)
irc.add_global_handler('welcome', welcome)
irc.add_global_handler('whoisauth', whoisauth)
irc.add_global_handler('whoischannels',whoischannels)
irc.add_global_handler('whoisuser',whoisuser)

# Jump into an infinite loop
while not restart:
    irc.process_once(0.2)
