#!/usr/bin/python2.6

import irclib
import random
import re
import string
import threading
import time

def add(userName, userCommand):
    global state
    global userList
    print "State : " + state
    if state != 'idle':
        if state == 'normal':
            if classCount('medic') == 2 and re.search('medic', userCommand):
            # Check for the medic slots.
                server.privmsg(userName, "There are already 2 medics in this game, simply type \"!add\" to join.")
                return 0
            # Debug.
            if len(userList) < 12:
                print "User add : " + userName + "  Command : " + userCommand
                userList[userName] = createUser(userName, userCommand)
            # Debug.
            if len(userList) == 12:
                initGame()
            printUserList()
            return 0
    else:
        server.privmsg(channel, "You can't \"!add\" until an admin has started a game.")
        return 0

def addFriend(userName, userCommand):
    global gameServer, userList
    # 2 friends limit.
    commandList = string.split(userCommand, ' ')
    if len(commandList) > 1 and userName in userList:
        for i in range(1, len(commandList)):
            userList[userName]['friends'] = commandList[i]

def addGame(userName, userCommand):
    resetVariables()
    global allowFriends, gameServer, state

    # Game options.
    if re.search('nofriends', userCommand):
        print "Disable friends."
        allowFriends = 0

    # Game server.
    if re.search(" [0-9] *", userCommand):
        gameServer = re.findall("[0-9]", userCommand)[0]
    else:
        server.privmsg(userName, "You must assign a server number. Here is an example : \"!add 2\".")
        return 0

    # Game type.
    if re.search('captain', userCommand):
        state = 'captain'
    elif re.search('classes', userCommand):
        state = 'classes'
    else:
        state = 'normal'

    server.privmsg(channel, 'PUG started. Game type : ' + state + '. Type "!add" to join a game.')

def analyseCommand(connection, event):
    global lastCommand
    userName = extractUserName(event.source())
    if re.match('^!', event.arguments()[0]):
    # Check if the user is trying to pass a command to the bot.
        userCommand = event.arguments()[0]
        if isAdminCommand(userName, userCommand):
            if checkIfUserIsAdmin(event):
            #Execute the admin command.
                lastCommand = userCommand
                executeCommand(userName, userCommand)
                return 1
            else :
            # Exit and report an error.
                server.privmsg(channel, "Warning " + userName + ", you are trying an admin command as a normal user.")
                return 1
        else :
        #Execute the user command.
            if isUserCommand(userName, userCommand):
                lastCommand = userCommand
                executeCommand(userName, userCommand)
                return 1
    return 0

def assignUserToTeam(gameClass, recursiveFriend, team, user):
    global allowFriends, state, teamA, teamB, userList
    if not team:
        if random.randint(0,1):
            team = 'a'
        else:
            team = 'b'
    if state == 'normal':
        # Assign the user to the team if the team's not full.
        if len(getTeam(team)) < 6: # Debug.
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
    if state == 'normal':
        assignUserToTeam('medic', 1, 'a', userList[getAPlayer('medic')])
        assignUserToTeam('medic', 1, 'b', userList[getAPlayer('medic')])
        for i in range(10): #Debug.
            assignUserToTeam('', 1, 0, userList[getAPlayer('')])
        printTeams()
    state = 'idle'
    return 0

def checkIfUserIsAdmin(event):
    global userStatus
    user = extractUserName(event.source())
    server.whois([user])
    while 1:
        irc.process_once(0.2)
        if userStatus != '':
            if re.search('@' + channel + ' ', userStatus):
            # User is an admin.
                userStatus = ''
                return 1
            else :
            # User is not an admin.
                userStatus = ''
                return 0 #Debug.
        time.sleep(0.05)

def classCount(gameClass):
    global userList
    counter = 0
    for i, j in userList.iteritems():
        for userClass in userList[i]['class']:
            if userClass == gameClass:
                counter += 1
    return counter            

def createUser(userName, userCommand):
    global classList
    commandList = string.split(userCommand, ' ')
    user = {'command':'', 'class':[], 'friends':{}, 'nick':'', 'status':'', 'team':''}
    user['command'] = userCommand
    user['class'] = extractClasses(userCommand)
    user['nick'] = userName
    return user

def executeCommand(userName, userCommand):
    if re.search('!add$', userCommand) or re.search('!add ', userCommand):
        add(userName, userCommand)
        return 0
    if re.search('!addfriends*$', userCommand) or re.search('!addfriends* ', userCommand):
        addFriend(userName, userCommand)
        return 0
    if re.search('!addgame$', userCommand) or re.search('!addgame ', userCommand):
        addGame(userName, userCommand)
        return 0
    if re.search('!endgame$', userCommand) or re.search('!endgame ', userCommand):
        stopGame()
        return 0
    if re.search('!ip$', userCommand) or re.search('!ip ', userCommand):
        ip()
        return 0
    if re.search('!remove$', userCommand) or re.search('!remove ', userCommand):
        remove(userName)
        return 0
    if re.search('!vent$', userCommand) or re.search('!vent ', userCommand):
        vent()
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
        print "return 1"
        return 1
    print "return 0"
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

def getTeam(team):
    global teamA, teamB
    if team == 'a':
        return teamA
    else:
        return teamB

def ip():
    global gameServer
    if gameServer != '':
        message = "Match will be played on server " + gameServer + " --> " + servers[gameServer]['ip'] + ":" + servers[gameServer]['port'] 
        server.privmsg(channel, message)

def isUser(userName):
    if userName in userList:
        return 1
    else:
        return 0
def initGame():
    global state, timer2
    print "Init game."
    if state == "normal" or state == "classes":
        timer2 = threading.Timer(20, buildTeams)
        timer2.start()

def isAdminCommand(userName, userCommand):
    global adminCommands
    userCommand = string.split(userCommand, ' ')[0]
    for i in adminCommands:
        if re.search('^' + userCommand + '$', i):
            return 1
    return 0

def isUserCommand(userName, userCommand):
    global userCommands
    userCommand = string.split(userCommand, ' ')[0]
    for i in userCommands:
        if re.search('^' + userCommand + '$', i):
            return 1
    server.privmsg(userName, "Invalid command : " + userCommand)
    return 0

def nickChange(connection, event):
    global userList
    oldUserName = extractUserName(event.source())
    newUserName = event.target()
    if oldUserName in userList:
        userList[newUserName] = userList[oldUserName]
        del userList[oldUserName]

def privmsg(connection, event):
    if not analyseCommand(connection, event):
        server.privmsg(extractUserName(event.source()), "Type \"!help\" for usage commands. Otherwise, don't ask me anything that I can't answer, I'm just a PUG bot.")

def pubmsg(connection, event):
    analyseCommand(connection, event)

def printTeams():
    global teamA, teamB
    teamNames = ['Team A', 'Team B']
    teams = [teamA, teamB]
    counter = 0
    for i in teams:
        message = teamNames[counter] + " : "
        for user in teams[counter]:
            message += ' "' + user['nick'] + '" '
        server.privmsg(channel, message)
        counter += 1

def printUserList():
    global lastUserPrint, timer, userList
    if (time.time() - lastUserPrint) > 5:
        lastUserPrint = time.time()
        # Debug.
        message = str(len(userList)) + "/12 users subscribed :  "
        for i, user in userList.iteritems():
            message += '"' + user['nick']
            if 'medic' in user['class']:
                message += " as \x034medic\x03"
            message += '"  '
        server.privmsg(channel, message)
    else:
        timer = threading.Timer(5, printUserList)
        timer.start()

def stopGame():
    global state
    state = 'idle'
    print 'PUG stopped.'

def remove(userName):
    global userList
    if(isUser(userName)):
        del userList[userName]
    printUserList()

def resetVariables():
    global allowFriends, gameServer, teamA, teamB, userList
    allowFriends = 1
    gameServer = ''
    teamA = []
    teamB = []
    userList = {}
    print 'Reset variables.'

def vent():
    message = "Ventrilo IP : " + servers['ventrilo']['ip'] + ":" + servers['ventrilo']['port'] + "  Password : " + password
    server.privmsg(channel, message)

def welcome(connection, event):
    #server.send_raw ("authserv auth user password")
    server.join ( channel )

def whois(connection, event):
    global userStatus
    userStatus = event.arguments()[1]

# Connection information
network = 'irc.gamesurge.net'
port = 6667
channel = '#tf2.test.us'
nick = 'PUG-BOT'
name = 'BOT'

adminCommands = ["!addgame", "!endgame"]
allowFriends = 1
classList = ['demo', 'medic', 'scout', 'soldier']
gameServer = ''
lastCommand = ""
lastUserPrint = time.time()
password = 'tf2gather'
state = 'idle'
teamA = []
teamB = []
servers = {'1':{'ip':'one.apoplexyservers.com', 'port':'27015'}, '2':{'ip':'two.apoplexyservers.com', 'port':'27015'}, '3':{'ip':'three.apoplexyservers.com', 'port':'27015'}, '4':{'ip':'four.apoplexyservers.com', 'port':'27015'}, '5':{'ip':'five.apoplexyservers.com', 'port':'27015'}, '7':{'ip':'8.12.21.21', 'port':'27015'}, 'ventrilo':{'ip':'vent20.gameservers.com', 'port':'4273'}}
timer = 0
timer2 = 0
userCommands = ["!add", "!addfriend", "!addfriends", "!ip", "!remove", "!vent"]
userList = {}
userStatus = ''

# Create an IRC object
irc = irclib.IRC()

# Create a server object, connect and join the channel
server = irc.server()
server.connect ( network, port, nick, ircname = name )

irc.add_global_handler ( 'nick', nickChange )
irc.add_global_handler ( 'privmsg', privmsg )
irc.add_global_handler ( 'pubmsg', pubmsg )
irc.add_global_handler ( 'welcome', welcome )
irc.add_global_handler ( 'whoischannels', whois )

# Jump into an infinite loop
irc.process_forever()
