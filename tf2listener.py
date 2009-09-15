#!/usr/bin/python2.6

import psycopg2
import socket
import time

passwordFile = open("passwords.txt")
serverFile = open("servers.txt")
try:
    passwords = passwordFile.readline().replace('\n', '').split(':')
    tf2pbPassword = passwords[0]
    servers = serverFile.readline().replace('\n', '').split(':')
finally:
    passwordFile.close()
    serverFile.close()

#CREATE TABLE srcds(data TEXT, time INTEGER);
database = psycopg2.connect('dbname=tf2pb host=localhost user=tf2pb password=' + tf2pbPassword)
cursor = database.cursor()

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('', 50007))
listener.listen(1)
while 1:
    try:
        connection, address = listener.accept()
    except:
        listener.listen(1)
        continue
    try:
        data = connection.recv(4096)
    except:
        continue
    if data and address[0] in servers:
        print data
        cursor.execute('INSERT INTO srcds VALUES (%s, %s)', (data, int(time.time())))
        database.commit()
        connection.close()
