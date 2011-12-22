#!/usr/bin/python
import cookielib
import irclib
import math
import psycopg2
import random
import re
import string
import urllib
import urllib2
import thread
import threading
import time
from BeautifulSoup import BeautifulSoup

#irclib.DEBUG = 1

def add(userName, userCommand):
    userList[userName] = createUser(userName, userCommand)
    printUserList()

def analyseIRCText(connection, event):
    userName = extractUserName(event.source())
    userCommand = event.arguments()[0]
    escapedChannel = cleanUserCommand(channel).replace('\\.', '\\\\.')
    escapedUserCommand = cleanUserCommand(event.arguments()[0])
    saveToLogs("[" + time.ctime() + "] <" + userName + "> " + userCommand + "\n")
    if userName in userList:
        updateUserStatus(userName, escapedUserCommand)
    if re.match('^\\\\!', escapedUserCommand):
    # Check if the user is trying to pass a command to the bot.
        if isUserCommand(userName, escapedUserCommand, userCommand):
                executeCommand(userName, escapedUserCommand, userCommand)

def checkConnection():
    global connectTimer
    if not server.is_connected():
        connect()

def cleanUserCommand(command):
    return re.escape(command)

def connect():
    global connectTimer, network, nick, name, port, server
    server.connect(network, port, nick, ircname = name)

def createUser(userName, userCommand):
    commandList = string.split(userCommand, ' ')
    user = {'command':'', 'class':[], 'friends':{}, 'id':0, 'last':0, 'nick':'', 'remove':0, 'status':'', 'team':''}
    user['command'] = userCommand
    user['id'] = getNextPlayerID()
    user['last'] = time.time()
    user['nick'] = userName
    send("NOTICE " + userName + " : " + "You sucessfully added.")
    return user

def drop(connection, event):
    userName = ''
    if len(event.arguments()) > 1:
        userName = event.arguments()[0]
    else:
        userName = extractUserName(event.source())
    remove(userName)

def executeCommand(userName, escapedUserCommand, userCommand):
    if re.search('^\\\\!add$', escapedUserCommand) or re.search('^\\\\!add\\\\ ', escapedUserCommand):
        add(userName, userCommand)
        return 0
    if re.search('^\\\\!man', escapedUserCommand):
        man()
        return 0
    if re.search('^\\\\!mumble', escapedUserCommand):
        mumble()
        return 0
    if re.search('^\\\\!players', escapedUserCommand):
        players()
        return 0
    if re.search('^\\\\!remove', escapedUserCommand):
        remove(userName)
        return 0

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

def getNextPlayerID():
    global userList
    largestID = 0
    for user in userList.copy():
        if userList[user]['id'] > largestID:
            largestID = userList[user]['id']
    return largestID + 1

def getServers():
    cookies = cookielib.CookieJar()
    data = urllib.urlencode({'viewed_welcome_page':'1'})
    request = urllib2.Request("http://esea.net/index.php?s=servers&type=pug", headers={"Cookie" : "viewed_welcome_page=1"})
    page = urllib2.urlopen(request).read()
    html = BeautifulSoup(page)
    html =  html.find("div", {"class":"content-block"})
    servers = []
    for tr in html('tr'):
        td_counter = 0
        for td in tr('td'):
            if td_counter == 1:
                name = td.a.contents[0]
            if td_counter == 3:
                ip = td.a.contents[0]
            if td_counter == 4:
                players = td.contents[0]
                if players.split('/')[1] == '12':
                    servers.append({'active':0, 'ip':str(ip), 'name':str(name), 'players':int(players.split('/')[0])})
            td_counter = td_counter + 1
    return servers

def getSubIndex(id):
    global subList
    counter = 0
    for sub in subList:
        if sub['id'] == int(id):
            return counter
        counter += 1
    return -1

def getUserCount():
    global userList
    return len(userList)

def help():
    send("PRIVMSG " + channel + " :\x030,03Visit \x0311,03http://communityfortress.com/tf2/news/tf2pugna-released.php\x030,03 to get help about the PUG process.")

def isGamesurgeCommand(userCommand):
    global gamesurgeCommands
    for command in gamesurgeCommands:
        if command == userCommand:
            return 1
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

def man():
    message = "\x030,03This bot has 5 commands: !add !mumble !players !remove"
    send("PRIVMSG " + channel + " :" + message)

def mumble():
    message = "\x030,03Voice server IP: " + voiceServer['ip'] + ":" + voiceServer['port'] + " Download: http://sourceforge.net/projects/mumble/files/Mumble/1.2.3/"
    send("PRIVMSG " + channel + " :" + message)

def listeningTF2Servers():
    global alert, servers
    last_minutes = []
    servers = []
    while 1:
        try:
            servers = getServers()
            last_minutes.append(servers)
        except:
            print "HTTP error."
            time.sleep(15)
            continue
        if len(last_minutes) > 30:
            last_minutes.pop(0)
        c = 0
        for server in servers:
            cl = 0
            for l in last_minutes:
                for s in l:
                    if server['ip'] == s['ip']:
                        if s['players'] == 12:
                            servers[c]['active'] = 1
                        elif cl == len(last_minutes) - 1:
                            # Alert when there's a few players needed.
                            if cl > 1:
                                for sp in last_minutes[cl - 1]:
                                    if sp['ip'] == s['ip']:
                                        if s['players'] >= sp['players'] and s['players'] >= 6 and s['active'] == 1:
                                            sendMessage = 0
                                            if s['ip'] in alerts:
                                                if alerts[s['ip']]['dropped'] + (15 * 60) <= time.time():
                                                    sendMessage = 1
                                            else:
                                                alerts[s['ip']] = dict(emptyAlert)
                                                alerts[s['ip']]['dropped'] = time.time()
                                                sendMessage = 1
                                            if sendMessage:
                                                for user in userList:
                                                    send("PRIVMSG " + user + " :" + s['name'] + " (" + str(s['players']) + "/12) dropped a few players: connect " + s['ip'] + " or join from " + "http://esea.net/index.php?s=servers&id=" + s['name'].split(" ")[1])
                        if s['ip'] in minimums:
                            if s['players'] < minimums[s['ip']]:
                                minimums[s['ip']] = s['players']
                        else:
                            minimums[s['ip']] = s['players']
                cl = cl + 1
            c = c + 1
        for s in servers:
            if s['ip'] in minimums and s['active'] == 0 and s['players'] - minimums[s['ip']] >= 3:
                # Player increase.
                sendMessage = 0
                if s['ip'] in alerts:
                    if alerts[s['ip']]['increasing'] + (15 * 60) <= time.time():
                        sendMessage = 1
                else:
                    alerts[s['ip']] = dict(emptyAlert)
                    sendMessage = 1
                if sendMessage:
                    for user in userList:
                        alerts[s['ip']]['increasing'] = time.time()
                        send("PRIVMSG " + user + " :" + s['name'] + " (" + str(s['players']) + "/12) had a player increase in the last couple minutes: connect " + s['ip'] + " or join from " + "http://esea.net/index.php?s=servers&id=" + s['name'].split(" ")[1])
            if s['active'] == 0 and s['players'] + len(userList) >= 12:
                # Enough players.
                sendMessage = 0
                if s['ip'] in alerts:
                    if alerts[s['ip']]['enough'] + (15 * 60) <= time.time():
                        sendMessage = 1
                else:
                    alerts[s['ip']] = dict(emptyAlert)
                    sendMessage = 1
                if sendMessage:
                    for user in userList:
                        alerts[s['ip']]['enough'] = time.time()
                        send("PRIVMSG " + user + " :" + s['name'] + " (" + str(s['players']) + "/12), the players on that server combined with the players added in the channel are enough to start a PUG: connect " + s['ip'] + " or join from " + "http://esea.net/index.php?s=servers&id=" + s['name'].split(" ")[1])
        print alerts
        time.sleep(30)

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
        sub['team'] = '\x0311,03Blue\x030,03'
    elif 'red' in commandList:
        sub['team'] = '\x034,03Red\x030,03'
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

def players():
    printUserList()

def pubmsg(connection, event):
    analyseIRCText(connection, event)

def printSubs():
    global subList
    if len(subList):
        send("PRIVMSG " + channel + " :" + "\x037,03Substitute(s) needed:")
        for sub in subList:
            by = ''
            if sub['steamid'] != '':
                by = ", User = \"" + sub['steamid'] + "\""
            send("PRIVMSG " + channel + " :" + "\x030,03ID = \"" + str(sub['id']) + "\", Class = \"" + sub['class'].capitalize() + "\", Server = \"" + sub['server'] + "\", Team = \"" + sub['team'] + "\"" + by)

def printUserList():
    print userList
    global lastUserPrint, printTimer
    if (time.time() - lastUserPrint) > 5:
        message = "\x030,03" + str(len(userList)) + " user(s) subscribed :"
        for i, user in userList.copy().iteritems():
            message += ' "' + user['nick'] + '"'
        send("PRIVMSG " + channel + " :" + message)
        filled = []
        for s in servers:
            if s['players'] > 0:
                filled.append(s['name'] + " (" + str(s['players']) + "/12)")
        send("PRIVMSG " + channel + " :\x030,03Servers: " + ", ".join(filled))
    else:
        printTimer.cancel()
        printTimer = threading.Timer(5, printUserList)
        printTimer.start()
    lastUserPrint = time.time()

def prototype():
    print userList

def readPasswords():
    global password
    passwordFile = open("passwords.txt")
    try:
        passwords = passwordFile.readline().replace('\n', '').split(':')
        password = passwords[0]
    finally:
        passwordFile.close()

def remove(userName, printUsers = 1):
    global userLimit
    if isUser(userName):
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
    global gameServer, userLimit, userList
    gameServer = ''
    removeUnremovedUsers()
    print 'Reset variables.'

def restartBot():
    global restart
    restart = 1

def saveToLogs(data):
    logFile = open(channel.replace('#', '') + ".log", 'a')
    try:
        logFile.write(data)
    finally:
        logFile.close()

def send(message, delay = 0):
    global connection
    cursor = connection.cursor()
    cursor.execute('INSERT INTO messages (message) VALUES (%s)', (message,))
    cursor.execute('COMMIT;')

def sendMessageToAwayPlayers():
    global awayTimer
    awayTimer = threading.Timer(60, removeAwayUsers).start()
    if len(awayList) > 1:
        words = ['These players are', 'they don\'t', 'they']
    else:
        words = ['This player is', 'he doesn\'t', 'he']
    nickList = []
    for nick in awayList:
        nickList.append(nick)
    send("PRIVMSG " + channel + " :\x038,03Warning!\x030,03 " + words[0] + " considered as inactive by the bot : " + ", ".join(nickList) + ". If " + words[1] +" show any activity in the next minute " + words[2] + " will automatically be removed from the player list.")
    for user in awayList:
        send("PRIVMSG " + user + ' :Warning, you are considered as inactive by the bot and a game you subscribed is starting. If you still want to play this game you have to type anything in the channel, suggestion "\x034!ready\x031". If you don\'t want to play anymore you can remove by typing "!remove". Notice that after 60 seconds you will be automatically removed.')

def updateUserStatus(nick, escapedUserCommand):
    global awayList, userList
    if re.search('^\\\\!away', escapedUserCommand) and nick in userList:
        userList[nick]['last'] = time.time() - (10 * 60)
    else:
        if nick in userList:
            userList[nick]['last'] = time.time()
        if nick in awayList:
            del awayList[nick]

def welcome(connection, event):
    global password
    server.send_raw("authserv auth " + nick + " " + password)
    server.send_raw("MODE " + nick + " +x")
    server.join(channel)

# Connection information
network = 'Gameservers.NJ.US.GameSurge.net'
port = 6667
channel = '#esea.tf2'
nick = 'PUG-ESEA'
name = 'BOT'

alerts = {}
awayList = {}
awayTimer = 0.0
botID = 0
connectTimer = threading.Timer(0, None)
emptyAlert = {'dropped':0, 'enough':0, 'increasing':0}
gamesurgeCommands = ["\\!access", "\\!addcoowner", "\\!addmaster", "\\!addop", "\\!addpeon", "\\!adduser", "\\!clvl", "\\!delcoowner", "\\!deleteme", "\\!delmaster", "\\!delop", "\\!delpeon", "\\!deluser", "\\!deop", "\\!down", "\\!downall", "\\!devoice", "\\!giveownership", "\\!resync", "\\!trim", "\\!unsuspend", "\\!upall", "\\!uset", "\\!voice", "\\!wipeinfo"]
initTime = int(time.time())
initTimer = threading.Timer(0, None)
lastUserPrint = time.time()
minimums = {}
minuteTimer = time.time()
printTimer = threading.Timer(0, None)
startMode = 'automatic'
state = 'idle'
restart = 0
startGameTimer = threading.Timer(0, None)
password = ''
servers = []
subList = []
userCommands = ["\\!add", "\\!man", "\\!mumble", "\\!players", "\\!remove"]
userLimit = 16
userList = {}
voiceServer = {'ip':'208.100.4.87', 'port':'64793'}

readPasswords()

connection = psycopg2.connect('dbname=tf2ib host=127.0.0.1 user=tf2ib password=' + password)

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

connectTimer.cancel()
