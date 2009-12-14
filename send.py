#!/usr/bin/python

import irclib
import psycopg
import sys
import time

irclib.DEBUG = 1

def welcome(connection, event):
    server.join("#tf2.pug")
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
    tf2pbPassword = passwords[0]
finally:
    passwordFile.close()

# Connection information
network = 'Gameservers.NJ.US.GameSurge.net'
port = 6667
channel = '#tf2.pug.na'
name = 'BOT'

# Create an IRC object
irc = irclib.IRC()

# Create a server object, connect and join the channel
server = irc.server()
server.connect(network, port, nick, ircname = name, localaddress = ip)
irc.add_global_handler('welcome', welcome)

#CREATE TABLE messages(id SERIAL PRIMARY KEY, message TEXT);
database = psycopg.connect('dbname=tf2pb host=localhost user=tf2pb password=' + tf2pbPassword)
cursor = database.cursor()

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
