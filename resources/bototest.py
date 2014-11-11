import time
import serial
import re
import datetime
import boto
import os

class MeshItem(object):
	pass

ids = []
accountID = "navtant"
location = "Wiengartz Sargon"

testMode = 1
if testMode == 1:
	latestDomainName = "WeingartzLatestTest"
	historyDomainName = "WeingartzHistoryTest"
else:
	latestDomainName = "WeingartzLatest"
	historyDomainName = "WeingartzHistory"

x = MeshItem()
x.longid = "A09B09"
x.timestamp = long(time.time() * 1000)
x.hours = 789
ids.append(x)


print "updating cloud information", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

try:
    sdb = boto.connect_sdb('AKIAIKNS47E62775GK6Q', 'hQiT/2WBYOUdl1tERZp8jietOWDnVgqcTBfMwemw')
    domain = sdb.get_domain(latestDomainName)
except:
    print"FAILED"    

try:
    for item in ids:
        if item.found == True:
	    clouditem = domain.new_item(item.longid)
	    clouditem['serial_number'] = item.longid
	    clouditem['time'] = item.timestamp
	    clouditem['location'] = location
	    clouditem['hours'] = item.hours
	    clouditem['account_id'] = accountID

	    clouditem.save()
	else:
	    print "Missing: " + item.longid
except:
    print"FAILED"
    
    
