from bots import iotBot
from bots import applicationBot
import database.database

database = database.database
iotBotsList = []
appBotsList = []


def generateIotBots():
    deviceList = getDeviceList()
    if deviceList:
        for deviceId in deviceList:
            device = iotBot.IotBotClass(deviceId)
            iotBotsList.append(device)
    return iotBotsList


def generateApplicationBots():
    appList = getApplicationList()
    if appList:
        for installedAppId in appList:
            app = applicationBot.ApplicationBotClass(installedAppId)
            appBotsList.append(app)
    return appBotsList


def getIotBot(bot_id):
    for bot in iotBotsList:
        if bot.getBotId() == bot_id:
            return bot

    return None


def getAppBot(bot_id):
    pass


def getIotBots():
    pass


def getAppBots():
    pass


def deleteIotBot(bot_id):
    pass


def deleteAppBot(bot_id):
    pass


def deleteIotBots(bot_id):
    pass


def deleteAppBots(bot_id):
    pass


def updateIotBot(bot_id):
    pass


def updateAppBot(bot_id):
    pass


def updateIotBots():
    pass


def updateAppBots():
    pass


def getDeviceList():
    deviceList = []
    query = database.executeQuery("select deviceId from device_events_table", False).fetchall()

    for row in query:
        deviceId = row[0]
        if deviceId not in deviceList:
            deviceList.append(deviceId)

    return deviceList


def getApplicationList():
    appList = []
    query = database.executeQuery("select installedAppId from APPs_received_events_table", False).fetchall()

    for row in query:
        installedAppId = row[0]
        if installedAppId not in appList:
            appList.append(installedAppId)

    return appList
