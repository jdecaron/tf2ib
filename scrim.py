#!/usr/bin/python

import config
import irclib
import psycopg2
import random
import re
import string
import SRCDS
import threading
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
    bookedTo = ''
    server = getAvailableServer()
    if server:
        bookedTo = userName
        bookedServers[server['ip']] = [bookedTo, time.time(), "tf2pug", server['ip']]
        updateLast(server['ip'], '27015', time.time())
        send("PRIVMSG " + channel + " :\x030,01Server " + server['ip'] + " has been reserverd to " + bookedTo +  ". Servers are provided by cinq: \x0307,01http://atf2.org/")
        send("PRIVMSG " + userName + " :The information to connect to the server is \"connect " + server['ip'] + ":27015; password tf2pug\". The server is being restarted, the server will be ready in 30 seconds. You can execute 3 commands on your servers : !config, !kick, !map. For more information about each commands type \"!man\".")
        if bookedTo.lower() != userName.lower():
            send("PRIVMSG " + bookedTo + " : A server has been booked for you and you have 60 minutes to use it. The information to connect to the server is \"connect " + server['ip'] + ":27015; password tf2pug\". The server is being restarted, the server will be ready in 30 seconds. You can execute 3 commands on your servers : !config, !kick, !map. For more information about each commands type \"!man\".")
        executeRconCommand('_restart', server['ip'] + ':27015')
    else:
        send("NOTICE " + userName + " : There is no available server to book at the moment.")

def checkConnection():
    if not server.is_connected():
        connect()
    server.join('#tf2scrim')

def cleanUserCommand(command):
    return re.escape(command)

def _config(userName, userCommand, bypass = 0):
    bookedInfo = [0, 0, 0, 0]
    configuration = 'push'
    configList = ['ctf', 'koth', 'push', 'stopwatch']
    if bypass == 0:
        bookedInfo = hasABookedServer(userName)
        if bookedInfo == 0:
            return 0
        for command in userCommand.split():
            userCommandList = command.split('_')
            if userCommandList[0] in configList:
                configuration = userCommandList[0]
                break
            elif len(userCommandList) > 1 and userCommandList[1] in configList:
                configuration = userCommandList[1]
                break
    else:
        configuration = userCommand
        bookedInfo[3] = bypass
    executeRconCommand('exec cevo_' + configuration, bookedInfo[3] + ':27015')

def connect():
    server.connect(config.network, config.port, nick, ircname = name)

def executeCommand(userName, escapedUserCommand, userCommand):
    if re.search('^\\\\!book', escapedUserCommand):
        book(userName, userCommand)
        return 0
    if re.search('^\\\\!config', escapedUserCommand):
        _config(userName, userCommand)
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
    if re.search('^\\\\!status', escapedUserCommand):
        status()
        return 0
    if re.search('^\\\\!whattimeisit', escapedUserCommand):
        send("PRIVMSG " + channel + " :\x038,01* \x039,01Hammertime \x038,01*")
        return 0

def executeRconCommand(command, server):
    try:
        TF2Server = SRCDS.SRCDS(server.split(':')[0], int(server.split(':')[1]), config.rconPassword, 30)
        TF2Server.rcon_command(command)
    except:
        return 0

def extractUserName(user):
    if user:
        return string.split(user, '!')[0]
    else:
        return ''

def getAvailableServer():
    for server in getServerList():
        try:
            serverInfo = getServerInfo(server)
            for s in serverInfo['serverStatus'].strip().split("\n"):
                if re.search("^players", s):
                    serverInfo['playerCount'] = s.split(" ")[2]
            if 3 > int(serverInfo['playerCount']) and re.search("^Tournament is not live", serverInfo['tournamentInfo']) and (time.time() - server['last']) >= (60 * 15) and server['last'] >= 0:
                return {'ip':server['dns'], 'port':server['port']}
        except:
            print "Error processing the server info"
    return 0

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
    cursor.execute('SELECT * FROM servers')
    for row in cursor.fetchall():
        if row[2] >= 0 and (((time.time() - row[2]) >= (60 * 75) and row[4] == 0) or ((time.time() - row[2]) >= (60 * 45) and row[4] == 1)):
            serverList.append({'available':1, 'dns':row[0], 'ip':row[1], 'last':row[2], 'port':row[3], 'botID':row[4]})
        else:
            serverList.append({'available':0, 'dns':row[0], 'ip':row[1], 'last':row[2], 'port':row[3], 'botID':row[4]})
    return serverList

def hasABookedServer(userName):
    for server in bookedServers.copy():
        if bookedServers[server][0].lower() == userName.lower():
            return bookedServers[server]
    send("NOTICE " + userName + " : Error! Your nickname doesn't appear in the booked server list.")
    return 0

def help():
    send("PRIVMSG " + channel + " :\x030,01!book (reserve you an available server for an hour)")
    send("PRIVMSG " + channel + " :\x030,01!changelevel mapname (change the current level to the specified one)")
    send("PRIVMSG " + channel + " :\x030,01!config push (change the server configuration to one of these: ctf, koth, push)")
    send("PRIVMSG " + channel + " :\x030,01!kick playerid (kick player id from the server)")
    send("PRIVMSG " + channel + " :\x030,01!status (display the status of all the servers)")

def isAdmin(userName):
    server.send_raw("PRIVMSG ChanServ :" + channel + " a " + userName)
    counter = 0
    while not userName in adminList and counter < 20:
        irc.process_once(0.2)
        counter += 1
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
    return '#tf2mix'

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
        executeRconCommand('kickid ' + userCommand[1], bookedInfo[3] + ':27015')
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
        executeRconCommand('changelevel ' + map, bookedInfo[3] + ':27015')
        _config(userName, mapType, bookedInfo[3])
    else:
        send("NOTICE " + userName + " : Available maps : " + ", ".join(mapList))
    
def mumble():
    message = "\x030,01Voice server IP : " + voiceServer['ip'] + ":" + voiceServer['port'] + " Download : http://downloads.sourceforge.net/project/mumble/Mumble/1.2.2/Mumble-1.2.2.exe"
    send("PRIVMSG " + channel + " :" + message)

def prototype():
    print bookedServers

def pubmsg(connection, event):
    analyseIRCText(connection, event)

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

def status():
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
                    send("PRIVMSG " + '#tf2scrim' + " :\x030,01 " + server['dns'] + ": warmup on " + serverInfo['map'] + " with " + serverInfo['playerCount'] + " players")
                else:
                    serverInfo['tournamentInfo'] = serverInfo['tournamentInfo'].split("\"")
                    send("PRIVMSG " + '#tf2scrim' + " :\x030,01 " + server['dns'] + ": \x0311,01" + serverInfo['tournamentInfo'][3].split(":")[0] + "\x030,01:\x034,01" + serverInfo['tournamentInfo'][3].split(":")[1] + "\x030,01 on " + serverInfo['map'] + " with " + serverInfo['tournamentInfo'][1] + " remaining")
            else:
                send("PRIVMSG " + '#tf2scrim' + " :\x030,01 " + server['dns'] + ": empty")
        except:
            send("PRIVMSG " + '#tf2scrim' + " :\x030,01 " + server['dns'] + ": error processing the status info")

def updateLast(ip, port, last):
    ip = getIPFromDNS(ip)
    cursor = connection.cursor()
    cursor.execute('UPDATE servers SET last = %s, botID = %s WHERE ip = %s and port = %s', (last, botID, ip, port))
    cursor.execute('COMMIT;')

def welcome(connection, event):
    server.send_raw("authserv auth " + nick + " " + config.gamesurgePassword)
    server.send_raw("MODE " + nick + " +x")
    server.join(channel)

# Connection information
channel = '#tf2scrim'
nick = 'BOOK-BOT'
name = 'BOT'

adminCommands = ["\\!prototype"]
adminList = {}
bookedServers = {}
botID = 1
gamesurgeCommands = ["\\!access", "\\!addcoowner", "\\!addmaster", "\\!addop", "\\!addpeon", "\\!adduser", "\\!clvl", "\\!delcoowner", "\\!deleteme", "\\!delmaster", "\\!delop", "\\!delpeon", "\\!deluser", "\\!deop", "\\!down", "\\!downall", "\\!devoice", "\\!giveownership", "\\!resync", "\\!trim", "\\!unsuspend", "\\!upall", "\\!uset", "\\!voice", "\\!wipeinfo"]
mapList = ["cp_badlands", "cp_follower", "cp_gravelpit", "cp_gullywash_final1", "cp_freight_final1", "cp_granary", "cp_metalworks_rc3", "cp_process_rc2", "cp_snakewater", "cp_yukon", "ctf_turbine", "koth_pro_viaduct_rc3"]
restart = 0
userCommands = ["\\!book", "\\!changelevel", "\\!config", "\\!kick", "\\!man", "\\!map", "\\!status"]
voiceServer = {'ip':'mumble.atf2.org', 'port':'64738'}

connection = psycopg2.connect('dbname=tf2ib host=127.0.0.1 user=tf2ib password=' + config.databasePassword)
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
        if time.time() - bookedServers[serverName][1] > (60 * 60):
            if serverName in bookedServers:
                updateLast(bookedServers[serverName][3], '27015', 0)
                del bookedServers[serverName]
