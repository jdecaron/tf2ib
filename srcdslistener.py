#!/usr/bin/python

import config
import psycopg2
import socket
import time

database = psycopg2.connect('dbname=tf2ib host=localhost user=tf2ib password=' + databasePassword)
cursor = database.cursor()

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('69.164.199.15', 50007))
listener.listen(1)
servers = ["216.52.148.224", "74.91.113.91", "74.91.115.215"]
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
    print data
    print address[0] 
    if data and address[0] in servers:
        print 'authorized'
        cursor.execute('INSERT INTO srcds VALUES (%s, %s)', (data, int(time.time())))
        database.commit()
        connection.close()
