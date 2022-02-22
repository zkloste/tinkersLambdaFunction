import json
import time
import DBInteractions
import requests
import dateutil.parser
from decimal import Decimal
import boto3
import makePredictions





# initialize variables to -1
currentFlow = -1
currentStreets1h = -1
currentStreets3h = -1
currentBed1h = -1
currentBed3h = -1
currentTwins1h = -1
currentTwins3h = -1
t1 = -1
t2 = -1
t3 = -1
t4 = -1
t5 = -1

# get current epoch hour
t = int(time.time())
tHour = t - t % 3600



# pull data from usgs/openweather to get data from that hour
# attempt to get data from usgs water data
USGSresponse = requests.get(
    'https://waterservices.usgs.gov/nwis/iv/?format=json&sites=04207200&parameterCd=00060&siteStatus=all')
water_dict = USGSresponse.json()
USGSdatetime = water_dict['value']['timeSeries'][0]['values'][0]['value'][0]['dateTime']
USGSEpoch = dateutil.parser.isoparse(USGSdatetime)
USGSEpoch = int(USGSEpoch.timestamp())  # get epoch seconds using timestamp
USGSEpoch = USGSEpoch - USGSEpoch % 3600  # get last hour by subtracted modulus 1hr
USGSFlow = water_dict['value']['timeSeries'][0]['values'][0]['value'][0]['value']
if USGSEpoch == tHour:
    currentFlow = USGSFlow

# pull data from openweather api
weatherResponse = requests.get(
    'http://api.weatherapi.com/v1/current.json?key=823bc6c1f95641ad9e612823221702&q=44087&aqi=no')
weather_dict = weatherResponse.json()
twinsEpoch = weather_dict['current']['last_updated_epoch']
twinsEpoch = twinsEpoch - twinsEpoch % 3600
twinsRain1h = weather_dict['current']['precip_in']
if twinsEpoch == tHour:
    currentTwins1h = twinsRain1h

# pull streetsboro rain data
weatherResponse = requests.get(
    'http://api.weatherapi.com/v1/current.json?key=823bc6c1f95641ad9e612823221702&q=44241&aqi=no')
weather_dict = weatherResponse.json()
streetsEpoch = weather_dict['current']['last_updated_epoch']
streetsEpoch = streetsEpoch - streetsEpoch % 3600
streetsRain1h = weather_dict['current']['precip_in']
if streetsEpoch == tHour:
    currentStreets1h = streetsRain1h

# pull bedford rain data
weatherResponse = requests.get(
    'http://api.weatherapi.com/v1/current.json?key=823bc6c1f95641ad9e612823221702&q=44146&aqi=no')
weather_dict = weatherResponse.json()
bedfordEpoch = weather_dict['current']['last_updated_epoch']
bedfordEpoch = bedfordEpoch - bedfordEpoch % 3600
bedfordRain1h = weather_dict['current']['precip_in']
if bedfordEpoch == tHour:
    currentBed1h = bedfordRain1h

# create the db reference then update chunk in the databaase
waterTable = DBInteractions.createTable()
chunk = {
    'Epoch': tHour,
    'flow': currentFlow,
    'twinRain1h': currentTwins1h,
    'twinRain3h': float(currentTwins3h),
    'bedRain1h': currentBed1h,
    'bedRain3h': float(currentBed3h),
    'streetsRain1h': currentStreets1h,
    'streetsRain3h': float(currentStreets3h),
    't+1': t1,
    't+2': t2,
    't+3': t3,
    't+4': t4,
    't+5': t5
}
chunk = json.loads(json.dumps(chunk), parse_float=Decimal)
waterTable.put_item(Item=chunk)

# attempt to get last 5 hours of water data
# needed for 3h rain and 5h predictions
waterData = []
nextEpoch = tHour
for i in range(6):
    nextEpoch = tHour - 3600 * i
    # get the data in table from that hour
    waterData.append(DBInteractions.getWaterData(epoch=nextEpoch))

    if waterData[i]:
        print("got data successfully: ")

# calculate 3h rain
for i in range(3):
    try:
        if waterData[i]['Item']:
            # set 3h rain data to 0 from initialization of -1
            if i == 0:
                currentBed3h = 0
                currentStreets3h = 0
                currentTwins3h = 0
            # add bedford rain to 3h total if it has a valid value (not -1)
            if waterData[i]['Item']['bedRain1h'] > -1:
                # add 1h rain data to 3h rain data to get running total
                currentBed3h = currentBed3h + waterData[i]['Item']['bedRain1h']
            # add twins rain to 3h total if it has a valid value (not -1)
            if waterData[i]['Item']['twinRain1h'] > -1:
                # add 1h rain data to 3h rain data to get running total
                currentTwins3h = currentTwins3h + waterData[i]['Item']['twinRain1h']
            # add streets rain to 3h total if it has a valid value (not -1)
            if waterData[i]['Item']['streetsRain1h'] > -1:
                # add 1h rain data to 3h rain data to get running total
                currentStreets3h = currentStreets3h + waterData[i]['Item']['streetsRain1h']
    except KeyError:
        print("in exception")


#make predictions for next 5 hours
#required inputs:
#last 5 hours of data (data can't be -1)
for i in range(6):
    try:
        if waterData[i]['Item']:
            print("water data exists at " + str(i))
        if (waterData[i]['Item']['twinRain1h'] == -1 or waterData[i]['Item']['twinRain3h'] == -1 or
                waterData[i]['Item']['streetsRain1h'] == -1 or waterData[i]['Item']['streetsRain3h'] == -1 or
                waterData[i]['Item']['bedRain1h'] == -1 or waterData[i]['Item']['bedRain3h'] == -1 or waterData[i]['Item']['flow'] == -1):
            print("value is equal to -1")
            break
    except KeyError:
        print("key error exception in prediction")
        break

    #if i == 5 then all conditions were satisfied - prediction is able to be made
    if i == 5:
        tvalues = makePredictions.useWaterData(waterData)

        chunk = {
            'Epoch': tHour,
            'flow': currentFlow,
            'twinRain1h': currentTwins1h,
            'twinRain3h': float(currentTwins3h),
            'bedRain1h': currentBed1h,
            'bedRain3h': float(currentBed3h),
            'streetsRain1h': currentStreets1h,
            'streetsRain3h': float(currentStreets3h),
            't+1': tvalues[0],
            't+2': tvalues[1],
            't+3': tvalues[2],
            't+4': tvalues[3],
            't+5': tvalues[4]
        }
        chunk = json.loads(json.dumps(chunk), parse_float=Decimal)
        waterTable.put_item(Item=chunk)






# #get data from db for all epochs
# requiredEpochs = [USGSEpoch]
# if twinsEpoch in requiredEpochs:
#     requiredEpochs=requiredEpochs
# else:
#     requiredEpochs.append(twinsEpoch)
# if streetsEpoch in requiredEpochs:
#     requiredEpochs=requiredEpochs
# else:
#     requiredEpochs.append(streetsEpoch)
# if bedfordEpoch in requiredEpochs:
#     requiredEpochs=requiredEpochs
# else:
#     requiredEpochs.append(bedfordEpoch)

# twinsEpochdbData = DBInteractions.getWaterData(twinsEpoch)
# if twinsEpochdbData.__len__() == 1:
#     print("hi")
# elif twinsEpochdbData['Item'][]
#
#
# #get the db entry for the current hour
# dbData = DBInteractions.getWaterData(tHour)


print(tHour)
