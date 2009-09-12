#!/usr/bin/python2.6

import socket
import sqlite3
import time

#CREATE TABLE srcds(data TEXT, time INTEGER);
database = sqlite3.connect('./tf2pb.sqlite')
cursor = database.cursor()

file = open("servers.txt")
try:
    servers = file.readline().replace('\n', '').split(':')
finally:
    file.close()

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('', 50001))
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
        data = data, int(time.time())
        cursor.execute('INSERT INTO srcds VALUES (?, ?)', data)
        database.commit()
        connection.close()
