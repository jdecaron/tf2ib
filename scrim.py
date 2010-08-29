#!/usr/bin/python

import irclib
import psycopg
import random
import re
import string
import SRCDS
import time

#irclib.DEBUG = 1

def analyseIRCText(connection, event):
    userName = extractUserName(event.source())
    userCommand = event.arguments()[0]
    escapedChannel = cleanUserCommand(channel).replace('\\.', '\\\\.')
    escapedUserCommand = cleanUserCommand(event.arguments()[0])
    saveToLogs("[" + time.ctime() + "] <" + userName + "> " + userCommand + "\n")
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
                send("PRIVMSG " + channel + " :\x030,01Warning " + userName + ", you are trying an admin command as a normal user.")
        elif isUserCommand(userName, escapedUserCommand, userCommand):
                executeCommand(userName, escapedUserCommand, userCommand)

def book(userName, userCommand):
    global bookedServers
    allServers = []
    availableServers = []
    inUseServers = []
    bookedTo = ''
    server = ''
    servers = getServerList()
    userCommand = userCommand.split()
    serverToBook = ''
    for server in servers:
        allServers.append(server['dns'].split('.')[0])
        if server['available'] == 1:
            availableServers.append(server['dns'].split('.')[0])
        else:
            inUseServers.append(server['dns'].split('.')[0])
    if len(userCommand) <= 1:
        if len(availableServers) > 0:
            send("NOTICE " + userName + " : Available server(s) : " + ", ".join(availableServers))
        if len(inUseServers) > 0:
            i = 0
            for inUseServer in inUseServers:
                inUseServers[i] = inUseServer + '(' + isBookedByWho(inUseServer) + ')'
                i = i + 1
            send("NOTICE " + userName + " : Unavailable server(s) : " + ", ".join(inUseServers))
        if len(servers) == 0:
            send("NOTICE " + userName + " : There are no servers available to book right now. If you know what you are doing and you also know the name of the server you want to book, you can type something like this : \"!book server nick force\".")
        return 0
    providedAServer = 0
    for command in userCommand:
        if command in allServers:
            providedAServer = 1
    if providedAServer:
        bookAServer = 0
        matchAvailableServer = 0
        matchBookedServer = 0
        for command in userCommand:
            if command == '!book':
                continue
            if command in availableServers:
                server = command
                matchAvailableServer = 1
            elif command in inUseServers:
                server = command
                matchBookedServer = 1
            if command != 'force' and command not in availableServers and command not in inUseServers:
                bookedTo = command
        if bookedTo == '':
            bookedTo = userName
        if matchAvailableServer == 1:
            bookAServer = 1
        elif matchBookedServer == 1:
            if 'force' in userCommand:
                bookAServer = 1
            else:
                send("NOTICE " + userName + " : Error! The server you specified is in use at the moment. If you know what you are doing and you want to book it anyway you can book it by adding the force command, example : \"!book server nick force\".")
        else:
            send("NOTICE " + userName + " : Error! The server you want to book isn't in the server list. To view the server list, type \"!book\".")
        if bookAServer == 1:
            serverPassword = getAServerPassword()
            bookedServers[server] = [bookedTo, time.time(), serverPassword, server]
            updateLast(server + '.tf2pug.org', '27015', time.time())
            send("PRIVMSG " + channel + " :\x030,01Server " + server + " has been reserverd to " + bookedTo +  ". Servers are provided by AI : \x0307,01http://aigaming.com/")
            send("PRIVMSG " + userName + " :The information to connect to the server is \"connect " + server + ".tf2pug.org:27015; password " + serverPassword + "\".")
            if bookedTo.lower() != userName.lower():
                send("PRIVMSG " + bookedTo + " : A server has been booked for you and you have 45 minutes to use it. The information to connect to the server is \"connect " + server + ".tf2pug.org:27015; password " + serverPassword + "\". During the 45 minutes period you can execute 2 commands on your servers : !config, map. If you need to re-execute the config just change the map with the \"!map\" command. For more information about each command type \"!man command\".")
            executeRconCommand('changelevel cp_badlands', server + '.tf2pug.org:27015')
            executeRconCommand('sv_password ' + serverPassword, server + '.tf2pug.org:27015')
    else:
        send("NOTICE " + userName + " : You must specify a server you want to book. Example : \"!book server nick\"")

def checkConnection():
    if not server.is_connected():
        connect()

def cleanUserCommand(command):
    return re.escape(command)

def config(userName, userCommand, bypass = 0):
    bookedInfo = [0, 0, 0, 0]
    config = 'push'
    configList = ['ctf', 'koth', 'push', 'stopwatch']
    if bypass == 0:
        bookedInfo = hasABookedServer(userName)
        if bookedInfo == 0:
            return 0
        for command in userCommand.split():
            userCommandList = command.split('_')
            if userCommandList[0] in configList:
                config = userCommandList[0]
                break
            elif len(userCommandList) > 1 and userCommandList[1] in configList:
                config = userCommandList[1]
                break
    else:
        config = userCommand
        bookedInfo[3] = bypass
    executeRconCommand('exec cevo_' + config, bookedInfo[3] + '.tf2pug.org:27015')

def connect():
    server.connect(network, port, nick, ircname = name, localaddress = '69.164.199.15')

def executeCommand(userName, escapedUserCommand, userCommand):
    if re.search('^\\\\!book', escapedUserCommand):
        book(userName, userCommand)
        return 0
    if re.search('^\\\\!config', escapedUserCommand):
        config(userName, userCommand)
        return 0
    if re.search('^\\\\!changelevel', escapedUserCommand):
        map(userName, userCommand)
        return 0
    if re.search('^\\\\!kick', escapedUserCommand):
        kick(userName, userCommand)
        return 0
    if re.search('^\\\\!man', escapedUserCommand):
        help()
        return 0
    if re.search('^\\\\!map', escapedUserCommand):
        map(userName, userCommand)
        return 0
    if re.search('^\\\\!mumble', escapedUserCommand):
        mumble()
        return 0
    if re.search('^\\\\!prototype', escapedUserCommand):
        prototype()
        return 0
    if re.search('^\\\\!servers', escapedUserCommand):
        book(userName, '!book')
        return 0
    if re.search('^\\\\!whattimeisit', escapedUserCommand):
        send("PRIVMSG " + channel + " :\x038,01* \x039,01Hammertime \x038,01*")
        return 0

def executeRconCommand(command, server):
    try:
        TF2Server = SRCDS.SRCDS(server.split(':')[0], int(server.split(':')[1]), rconPassword, 30)
        TF2Server.rcon_command(command)
    except:
        return 0

def extractUserName(user):
    if user:
        return string.split(user, '!')[0]
    else:
        return ''

def getAServerPassword():
    return serverPasswords[random.randint(0, len(serverPasswords) - 1)]

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

def getServerList():
    serverList = []
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM servers')
    for row in cursor.fetchall():
        if row[2] >= 0 and (((time.time() - row[2]) >= (60 * 75) and row[4] == 0) or ((time.time() - row[2]) >= (60 * 45) and row[4] == 1)):
            serverList.append({'available':1, 'dns':row[0], 'ip':row[1], 'last':row[2], 'port':row[3], 'botID':row[4]})
        else:
            serverList.append({'available':0, 'dns':row[0], 'ip':row[1], 'last':row[2], 'port':row[3], 'botID':row[4]})
    print serverList
    return serverList

def hasABookedServer(userName):
    for server in bookedServers.copy():
        if bookedServers[server][0].lower() == userName.lower():
            return bookedServers[server]
    send("NOTICE " + userName + " : Error! Your nickname doesn't appear in the booked server list.")
    return 0

def isAdmin(userName):
    server.send_raw("PRIVMSG ChanServ :" + channel + " a " + userName)
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
    userCommand = string.split(userCommand, ' ')[0]
    userCommand = removeLastEscapeCharacter(userCommand)
    for command in adminCommands:
        if command == userCommand:
            return 1
    return 0

def isBookedByWho(server):
    for i in bookedServers.copy():
        if i.lower() == server.lower():
            return bookedServers[i][0]
    return '#tf2.pug.na'

def isGamesurgeCommand(userCommand):
    for command in gamesurgeCommands:
        if command == userCommand:
            return 1
    return 0

def isUserCommand(userName, escapedUserCommand, userCommand):
    escapedUserCommand = string.split(escapedUserCommand, ' ')[0]
    escapedUserCommand = removeLastEscapeCharacter(escapedUserCommand)
    for command in userCommands:
        if command == escapedUserCommand:
            return 1
    send("NOTICE " + userName + " : Invalid command : \"" + userCommand + "\". Type \"!man\" for usage commands.")
    return 0

def kick(userName, userCommand):
    bookedInfo = hasABookedServer(userName)
    if bookedInfo == 0:
        return 0
    userCommand = userCommand.split()
    if len(userCommand) < 2:
        send("NOTICE " + userName + " : Error! You must provide an user ID in order to kick a player. If you need to find it type \"status\" in your TF2 console. Example : \"!kick 10\".")
        return 0
    elif re.match('^\d*$', userCommand[1]):
        executeRconCommand('kickid ' + userCommand[1], bookedInfo[3] + '.tf2pug.org:27015')
    else:
        send("NOTICE " + userName + " : Error! You must provide only numeric character (player ID) in order to kick a player.")
        return 0
    
def map(userName, userCommand):
    bookedInfo = hasABookedServer(userName)
    if bookedInfo == 0:
        return 0
    map = ''
    for command in userCommand.split():
        if command in mapList:
            map = command
    if map != '':
        mapType = map.split('_')[0]
        if mapType == 'cp':
            if map == 'cp_gravelpit':
                mapType = 'stopwatch'
            else:
                mapType = 'push'
        print bookedInfo[3] + '.tf2pug.org:27015'
        executeRconCommand('changelevel ' + map, bookedInfo[3] + '.tf2pug.org:27015')
        executeRconCommand('sv_password ' + bookedInfo[2], bookedInfo[3] + '.tf2pug.org:27015')
        config(userName, mapType, bookedInfo[3])
    else:
        send("NOTICE " + userName + " : Available maps : " + ", ".join(mapList))
    
def mumble():
    message = "\x030,01Voice server IP : " + voiceServer['ip'] + ":" + voiceServer['port'] + "  Password : " + password + "  Download : http://downloads.sourceforge.net/project/mumble/Mumble/1.2.2/Mumble-1.2.2.exe"
    send("PRIVMSG " + channel + " :" + message)

def prototype():
    print bookedServers

def pubmsg(connection, event):
    analyseIRCText(connection, event)

def readPasswords():
    global rconPassword, botPassword
    passwordFile = open("passwords.txt")
    try:
        passwords = passwordFile.readline().replace('\n', '').split(':')
        rconPassword = passwords[1]
        botPassword = passwords[0]
    finally:
        passwordFile.close()

def removeLastEscapeCharacter(userCommand):
    if userCommand[len(userCommand) - 1] == '\\':
        userCommand = userCommand[0:len(userCommand) - 1]
    return userCommand

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
    cursor = connection.cursor()
    cursor.execute('INSERT INTO messages (message) VALUES (%s)', (message,))
    cursor.execute('COMMIT;')

def updateLast(ip, port, last):
    ip = getIPFromDNS(ip)
    cursor = connection.cursor()
    cursor.execute('UPDATE servers SET last = %s, botID = %s WHERE ip = %s and port = %s', (last, botID, ip, port))
    cursor.execute('COMMIT;')

def welcome(connection, event):
    server.send_raw("authserv auth " + nick + " " + botPassword)
    server.send_raw("MODE " + nick + " +x")
    server.join(channel)

# Connection information
network = 'Gameservers.NJ.US.GameSurge.net'
port = 6667
channel = '#tf2scrim'
nick = 'SCRIM-BOT'
name = 'BOT'

adminCommands = ["\\!prototype"]
adminList = {}
bookedServers = {}
botID = 1
botPassword = ''
gamesurgeCommands = ["\\!access", "\\!addcoowner", "\\!addmaster", "\\!addop", "\\!addpeon", "\\!adduser", "\\!clvl", "\\!delcoowner", "\\!deleteme", "\\!delmaster", "\\!delop", "\\!delpeon", "\\!deluser", "\\!deop", "\\!down", "\\!downall", "\\!devoice", "\\!giveownership", "\\!resync", "\\!trim", "\\!unsuspend", "\\!upall", "\\!uset", "\\!voice", "\\!wipeinfo"]
mapList = ["cp_badlands", "cp_follower", "cp_gravelpit", "cp_gullywash", "cp_freight_final1", "cp_granary", "cp_yukon", "ctf_turbine", "koth_viaduct"]
rconPassword = ''
restart = 0
serverPasswords = ["heavymachinegun", "jetpack", "offensechamber", "chipotle", "lightninggun", "entourage", "california", "vmars", "gotfraggon", "bdropped", "miguelo", "steven", "haffey", "carbon", "sherwood", "foil", "broskow", "kansas", "dailybread", "habs", "eulogy", "valo", "remz", "poutine", "montreal", "sauce", "koubis", "nopole", "mrbishop", "quebec", "chadgap", "railfest", "banquise", "bebe"]
userCommands = ["\\!book", "\\!changelevel", "\\!config", "\\!kick", "\\!map", "\\!servers"]
voiceServer = {'ip':'mumble.tf2pug.org', 'port':'64738'}

readPasswords()
connection = psycopg.connect('dbname=tf2ib host=127.0.0.1 user=tf2ib password=' + botPassword)
irc = irclib.IRC()
server = irc.server()
connect()

irc.add_global_handler('pubmsg', pubmsg)
irc.add_global_handler('privnotice', pubmsg)
irc.add_global_handler('pubnotice', pubmsg)
irc.add_global_handler('welcome', welcome)

# Jump into an infinite loop
while not restart:
    global bookedServers
    irc.process_once(0.2)
    for serverName in bookedServers.copy():
        if time.time() - bookedServers[serverName][1] > (60 * 1):
            if serverName in bookedServers:
                updateLast(bookedServers[serverName][3] + '.tf2pug.org', '27015', 0)
                del bookedServers[serverName]
