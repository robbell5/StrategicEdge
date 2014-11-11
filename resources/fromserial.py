import time
import serial
import re
import datetime
import boto
import os
import MySQLdb as database

class MeshItem(object):
	pass


#----CONFIG----#

#file paths for output/input
full_path = os.path.realpath(os.getcwd())
idlistfilehandle = "id_list.txt"
outputfilehandle = "output.txt"

#open usb connection to device
usbport = '/dev/ttyACM0'
ser = serial.Serial(usbport, 19200)
ser.timeout = 1

#various regex stuff
pattern = re.compile("\w+:\s*\w+")
idpattern = re.compile("\w{8}")
houridpattern = re.compile("\w{16}")

#AWS stuff
testMode = 1
if testMode == 1:
	latestDomainName = "WeingartzLatestTest"
	historyDomainName = "WeingartzHistoryTest"
else:
	latestDomainName = "WeingartzLatest"
	historyDomainName = "WeingartzHistory"

accountID = "navtant"
location = "Wiengartz Sargon"
sublocation = "Wiengartz Sargon - 0"

ids = []
idsFromCurrentDB = []
idsFromHistoryDB = []

#----FUNCTIONS----#

def markAllUnfound():
	for item in ids:
		item.found = False

def sleepXFromTime(amount, timestamp):
	now = time.time()
	if amount - (now - timestamp) > 0:
		time.sleep(amount - (now - timestamp))

def printCharsToSerial(output):
	for character in output:
		ser.write(character)
		time.sleep(.300)

def handleMessage(message):
	#id response
	if message[0:2] == "90":
		pass
	#new arrival message
	if message [0:2] == "90":
		pass

def newArrival():
	print "checking for new arrivals", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
	#ask for new arrivals
	start = long(time.time())
	timecheck = long(time.time())
	time.sleep(4)
	lastNSendOut = 0

	while timecheck - start < 200:
		
		if time.time() - lastNSendOut > 45:
			print "n Sendout"
			ser.write("n" + "\n")
			lastNSendOut = long(time.time())
		
		response = ser.readline()
		response = response.strip()

		if len(response) > 0: 
			print response
			if idpattern.match(response):
				inIds = False
				print "accepted: " + response
				for item in ids:
					if item.longid == response[-6:]:
						inIds = True
						sending = "m" + item.longid + "\n"
						print sending
						printCharsToSerial(sending)

				if inIds == False:
					print "adding: " + response[-6:]
					x = MeshItem()
					x.longid = response[-6:]
					x.found = False
					ids.append(x)

					sending = "m" + x.longid + "\n"
					print sending
					printCharsToSerial(sending)

					with open(idlistfilehandle, "a") as id_file:
						id_file.write(response[-6:] + "\n")

		timecheck = time.time()

def wakeUp():
	#wake everybody up
	print "Wake up", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
	for j in range(200):
		ser.write("w" + "\n")
		time.sleep(.701)

def nodeSleep():
	print "Putting everybody to sleep", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
	#put everybody to sleep
	for j in range(20):
		ser.write("x" + "\n")
		time.sleep(.477)

def callout():
	print "Sending out for devices", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
	time.sleep(2)
	#send out for each id
	i = 0
	while i < len(ids):
		
		retries = 0
		while retries < 3 and ids[i].found == False:
			print ("u" + ids[i].longid )
			printCharsToSerial("u" + ids[i].longid + "\n")
			
			start = long(time.time())
			timecheck = long(time.time())		
			
			while ids[i].found == False and timecheck - start < 10:
				
				response = ser.readline()
				response = response.strip()
				if len(response) > 0:
					print response
					if houridpattern.match(response):
						response_hours = int(response[2:10],16)
						response_id = response[-6:]
						for equipment in ids:
							if equipment.longid == response_id and equipment.found == False:
								with open(outputfilehandle, "a") as text_file:
									print "read: " + response
									today = datetime.date.today()
									timestr = today.strftime('%H %M %I %p on %d, %b %Y')
									text_file.write(response + ", " + timestr +"\n")

								equipment.found = True
								equipment.timestamp = long(time.time() * 1000)
								equipment.hours = response_hours
						#create http request
						#send it on another thread
				timecheck = long(time.time())

			retries = retries + 1
		i = i + 1

def writeToLocalDatabase():
    
    print "Writing information to local database!"
    connection = database.connect('localhost', 'root', 'password', 'Current');

    with connection:
    
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS Current("
                       + "snumber VARCHAR(255) PRIMARY KEY ,"
                       + "time BIGINT,"
                       + "hours INT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS History("
                      + "id INT PRIMARY KEY AUTO_INCREMENT,"
                      + "snumber VARCHAR(255),"
                      + "time BIGINT,"
                      + "hours INT)")
           
        for item in ids:
            if item.found == True:
                cursor.execute("INSERT INTO Current("
                              + "snumber, time, hours) "
                              + "VALUES("
                              + "'" + item.longid + "',"
                              + str(item.timestamp) + ","
                              + str(item.hours) + ")"
                              + " ON DUPLICATE KEY UPDATE time=VALUES(time), hours=VALUES(hours);")
                   
                print "Added (" + item.longid + ") to 'Current'"
                       
                cursor.execute("INSERT INTO History("
                                      + "snumber, time, hours) "
                                      + "VALUES("
                                      + "'" + item.longid + "',"
                                      + str(item.timestamp) + ","
                                      + str(item.hours) + ")")
                print "Added (" + item.longid + ") to 'History'"
                               
            else:
                print "Missing: " + item.longid

        cursor.execute("SELECT * FROM Current")
        numrows = cursor.rowcount
        print "Number of rows in 'Current' DB: " + str(numrows)
        
        for i in xrange(0,numrows):
            row = cursor.fetchone()
            x = MeshItem()
            x.longid = row[0]
            x.timestamp = row[1]
            x.hours = row[2]
            idsFromCurrentDB.append(x)
            print "Item (" + x.longid + ") found in 'Current' database"
        
        cursor.execute("SELECT * FROM History")
        numrows = cursor.rowcount
        print "Number of rows in 'History' DB: " + str(numrows)
        
        for i in xrange(0,numrows):
            row = cursor.fetchone()
            x = MeshItem()
            x.longid = row[1]
            x.timestamp = row[2]
            x.hours = row[3]
            idsFromHistoryDB.append(x)
            print "Item (" + x.longid + ") found in 'History' database"

def writeToCloud():
    print "Attempting to update cloud information: ", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        sdb = boto.connect_sdb('AKIAIKNS47E62775GK6Q', 'hQiT/2WBYOUdl1tERZp8jietOWDnVgqcTBfMwemw')
        domain = sdb.get_domain(latestDomainName)
        
        try:
            #upload to cloud
            #upload current
            for item in idsFromCurrentDB:
                clouditem = domain.get_item(item.longid)
                if clouditem:
                    if long(item.hours) > long(clouditem['hours']):
                        print "Local data for item (" + item.longid + ") is newer!"
                        clouditem = domain.new_item(item.longid)
                        clouditem['serial_number'] = item.longid
                        clouditem['time'] = item.timestamp
                        clouditem['location'] = location
                        clouditem['hours'] = item.hours
                        clouditem['account_id'] = accountID
                        
                        clouditem.save()
                    
                    else:
                        print "Item (" + item.longid + ") has newer cloud info!"
        
                else:
                    print "Item (" + item.longid + ") does not exist on cloud"
                    clouditem = domain.new_item(item.longid)
                    clouditem['serial_number'] = item.longid
                    clouditem['time'] = item.timestamp
                    clouditem['location'] = location
                    clouditem['hours'] = item.hours
                    clouditem['account_id'] = accountID

    #upload history
    #upload to cloud
#    historyDomain = sdb.get_domain(historyDomainName)
#            for item in idsFromHistoryDB:
#                if item.found == True:
#                    clouditem = historyDomain.new_item(item.longid + " " + str(item.timestamp))
#                    clouditem['serial_number'] = item.longid
#                    clouditem['time'] = item.timestamp
#                    clouditem['location'] = sublocation
#                    clouditem['hours'] = item.hours
#                    clouditem['account_id'] = accountID
#                            
#                    clouditem.save()

            print "Removing local database!"
            connection = database.connect('localhost', 'root', 'password', 'Current');

            with connection:
    
                cursor = connection.cursor()
                cursor.execute("DROP TABLE IF EXISTS Current")
                cursor.execute("DROP TABLE IF EXISTS History")

        except:
            print "Failed - Cannot Update Database"

    except:
        print "Failed - Cannot Connect"

def readListOfIdsFromPan():
    try:
        with open(idlistfilehandle, "r") as id_file:
            lines = id_file.read().split("\n")
            
            for line in lines:
                if line != '':
                    x = MeshItem()
                    x.longid = line.strip()
                    x.found = False
                    x.hours = 0
                    ids.append(x)

    except IOError:
        print ""

    print len(ids)

def flushSerial():
    ser.read(ser.inWaiting())

#----MAIN SCRIPT START----#

readListOfIdsFromPan()

markAllUnfound()

flushSerial()

wakeUp()

newArrival()

callout()

nodeSleep()

ser.close()

writeToLocalDatabase()

writeToCloud()
