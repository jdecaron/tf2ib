#!/usr/bin/python

import irclib
import psycopg2
import sys
import time

irclib.DEBUG = 1

def checkConnection():
    global connectTimer
    if not server.is_connected():
        connect()
    server.join("#tf2.pug.na")

def connect():
    server.connect(network, port, nick, ircname = name)

def welcome(connection, event):
    server.join("#tf2.pug.na")

nick = ''
ip = ''
if len(sys.argv) == 2:
    nick = sys.argv[1]
elif len(sys.argv) == 3:
    nick = sys.argv[1]
    ip = sys.argv[2]

passwordFile = open("passwords.txt")
try:
    passwords = passwordFile.readline().replace('\n', '').split(':')
    tf2ibPassword = passwords[0]
finally:
    passwordFile.close()

# Connection information
network = '127.0.0.1'
port = 6667
name = 'BOT'

# Create an IRC object
irc = irclib.IRC()

# Create a server object, connect and join the channel
server = irc.server()
server.connect(network, port, nick, ircname = name, localaddress = ip)
irc.add_global_handler('welcome', welcome)

database = psycopg2.connect('dbname=tf2ib host=localhost user=tf2ib password=' + tf2ibPassword)
cursor = database.cursor()
minuteTimer = time.time()

while 1:
    cursor.execute('BEGIN;')
    cursor.execute('LOCK TABLE messages;')
    cursor.execute('SELECT * FROM messages LIMIT 1;')
    for row in cursor.fetchall():
        print row
        print time.time()
        cursor.execute('DELETE FROM messages WHERE id = %s', (row[0],))
        server.send_raw(row[1])
    cursor.execute('COMMIT;')
    irc.process_once(0.2)
    if time.time() - minuteTimer > 60:
        minuteTimer = time.time()
        checkConnection()
