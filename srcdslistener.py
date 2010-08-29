#!/usr/bin/python

import psycopg
import socket
import time

passwordFile = open("passwords.txt")
try:
    passwords = passwordFile.readline().replace('\n', '').split(':')
    tf2ibPassword = passwords[0]
finally:
    passwordFile.close()

#CREATE TABLE srcds(data TEXT, time INTEGER);
database = psycopg.connect('dbname=tf2ib host=localhost user=tf2ib password=' + tf2ibPassword)
cursor = database.cursor()

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('69.164.199.15', 50007))
listener.listen(1)
servers = ["72.14.177.61", "69.164.197.215", "64.85.169.241", "64.85.169.242", "208.100.17.204", "208.100.17.198", "206.123.125.77", "206.123.125.67", "66.207.169.162", "69.61.28.131", "66.207.171.232", "66.207.171.235", "66.207.171.238", "206.123.125.66", "69.61.52.46"]
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
