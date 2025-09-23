import json
from datetime import datetime

from bots import bot
import database.database
from database import database


class ApplicationBotClass(bot.BotClass):
    def __init__(self, bot_id):
        """
        To create a new application bot, you should use this class.

        :param bot_id: Installed Application ID
        """
        super().__init__(bot_id)

    def searchEvent(self, event_id):
        """
        Search for the given event and return it if this application has received such event before.

        :param event_id: event ID
        :return:
        """
        pass

    def searchCommand(self, event_id):
        """
        Search for the sent command by this application after receiving a particular event.

        :param event_id: The ID of target event
        :return: Sent command ID if it exits
        """
        pass

    def getSentCommandSourceEvent(self, command):
        """
        Get the source event of the sent command.

        :param command: Target application/simulator command
        :return: Source events if the target command is an application command. Otherwise, return None
        """

        if command['source'] == 'application':
            applicationCommand = command['command']

            authToken = str(applicationCommand[6])[7:]
            rowNumber = applicationCommand[25]
            sourceEvent = database.executeQuery("select * from APPs_received_events_table where authToken = ? and "
                                                "installedAppId = ? and rowNumber < ? order by ID DESC LIMIT 1",
                                                False, (authToken, self.getBotId(), rowNumber)).fetchone()

            if not sourceEvent:
                raise Exception("Source event is not found!")

            return sourceEvent
        elif command['source'] == 'simulator':
            applicationCommand = command['command']

            return None
        else:
            raise Exception("Command type is not supported!")

    def getSentModeCommandSourceEvent(self, modeCommand):
        if modeCommand['source'] == 'application':
            applicationModeCommand = modeCommand['command']
            authToken = str(applicationModeCommand[7])[7:]
            rowNumber = applicationModeCommand[26]
            sourceEvent = database.executeQuery("select * from APPs_received_events_table where authToken = ? and "
                                                "installedAppId = ? and rowNumber < ? order by ID DESC LIMIT 1",
                                                False, (authToken, self.getBotId(), rowNumber)).fetchone()

            if not sourceEvent:
                raise Exception("Source event is not found!")

            return sourceEvent
        elif modeCommand['source'] == 'simulator':

            return None
        else:
            raise Exception("Mode command type is not supported!")

    def getApplicationReceivedEventOriginalEvent(self, appEvent):
        if self.getBotId() != appEvent['event'][31]:
            raise Exception('This event does not belong to this Application Bot!')

        eventType = appEvent['eventType']

        if eventType == "DEVICE_EVENT":
            appDeviceEvent = appEvent['event']
            appEventDeviceId = appDeviceEvent[50]
            appEventLocationId = appDeviceEvent[32]
            appEventAttribute = appDeviceEvent[53]
            appEventValue = appDeviceEvent[54]
            appEventDate = appDeviceEvent[44]
            originalEvent = database.executeQuery("select * from device_events_table where deviceId = ? and "
                                                  "locationId = ? and name = ? and value = ? and "
                                                  "substr(date, 0, 20) = ?", False, (appEventDeviceId,
                                                                                     appEventLocationId,
                                                                                     appEventAttribute,
                                                                                     appEventValue,
                                                                                     appEventDate[0:19],)).fetchall()
            if len(originalEvent) > 1:
                pass
            if originalEvent:
                return originalEvent[0]
            else:
                return None
        elif eventType == "MODE_EVENT":
            modeEvent = appEvent['event']
            appEventLocationId = modeEvent[32]
            appEventDate = modeEvent[44]
            second = int(appEventDate[17:19])

            # Because simulator creates mode events twice and it may create delay between received events!
            appEventDate2 = appEventDate[0:17] + str(second - 1) + "Z"
            originalModeEvent = database.executeQuery("select * from mode_events_table where "
                                                      "locationId = ? and "
                                                      "(substr(date, 0, 20) = ? or substr(date, 0, 20) = ?)", False,
                                                      (appEventLocationId, appEventDate[0:19],
                                                       appEventDate2[0:19])).fetchone()
            return originalModeEvent
        else:
            raise Exception("Application event type is not supported!")

    def getApplicationReceivedEvent(self, event):
        eventType = event['eventType']

        if eventType == "DEVICE_EVENT":
            deviceEvent = event['event']

            if deviceEvent[6] == "False" and deviceEvent[7] == "False":
                return None

            sourceEventDeviceId = deviceEvent[15]
            sourceEventLocationId = deviceEvent[17]
            sourceEventAttribute = deviceEvent[16]
            sourceEventValue = deviceEvent[11]

            if isfloat(sourceEventValue):
                sourceEventValue = float(sourceEventValue)
                if sourceEventValue - int(sourceEventValue) == 0:
                    sourceEventValue = int(sourceEventValue)

            sourceEventDate = deviceEvent[9]
            receivedEvent = database.executeQuery("select * from APPs_received_events_table where "
                                                  "deviceEventDeviceID = ? and DeviceEventLocationId = ? and "
                                                  "attribute = ? and deviceEventValue = ? and "
                                                  "substr(eventTime, 0, 20) = ? and "
                                                  "eventType = ? and installedAppId = ?",
                                                  False, (sourceEventDeviceId,
                                                          sourceEventLocationId,
                                                          sourceEventAttribute,
                                                          sourceEventValue,
                                                          sourceEventDate[0:19],
                                                          eventType,
                                                          self.getBotId(),)).fetchall()
            if len(receivedEvent) > 1:
                eventIndex = self.getDeviceEventOrderIndex(deviceEvent)
                return receivedEvent[eventIndex]
            if receivedEvent:
                return receivedEvent[0]
            else:
                return None
        elif eventType == "MODE_EVENT":
            modeEvent = event['event']
            sourceEventLocationId = modeEvent[17]
            sourceEventDate = modeEvent[9]
            receivedEvents = database.executeQuery("select * from APPs_received_events_table where "
                                                  "locationId = ? and substr(eventTime, 0, 20) = ? and "
                                                  "eventType = ? and installedAppId = ?",
                                                  False, (sourceEventLocationId, sourceEventDate[0:19],
                                                          eventType, self.getBotId(),)).fetchall()
            if receivedEvents:
                return receivedEvents[-1]
            else:
                return None
        else:
            raise Exception("Event type is not supported!")

    def getDeviceEventOrderIndex(self, event):
        similarEvents = database.executeQuery("select * from device_events_table where "
                                              "deviceId = ? and substr(date, 0, 20) = ? "
                                              "and value = ? and locationId = ? and name = ? "
                                              "and displayed = 'True' and isStateChange = 'True' order by ID",
                                              False, (event[15], event[9][0:19],
                                                      event[11],
                                                      event[17],
                                                      event[16],)).fetchall()
        if similarEvents is None:
            raise Exception("Device event is not available!")

        counter = 0
        for row in similarEvents:
            if row[0] == event[0]:
                return counter
            counter += 1

        raise Exception("Device event is not available!")

    def getAppDeviceEventOrderIndex(self, appEvent):
        similarEvents = database.executeQuery("select * from APPs_received_events_table where "
                                              "deviceEventDeviceID = ? and substr(eventTime, 0, 20) = ? "
                                              "and attribute = ? and locationId = ? and deviceEventValue = ? "
                                              "order by ID", False, (appEvent[50], appEvent[44][0:19],
                                                                     appEvent[53],
                                                                     appEvent[32],
                                                                     appEvent[54],)).fetchall()
        if similarEvents is None:
            raise Exception("Device event is not available!")

        counter = 0
        for row in similarEvents:
            if row[0] == appEvent[0]:
                return counter
            counter += 1

        raise Exception("Device event is not available!")

    def getApplicationSentCommands(self, receivedAppEvent):
        authToken = receivedAppEvent[30]
        rowNumber = receivedAppEvent[69]

        nextReceivedAppEventRowNumber = database.executeQuery("select rowNumber from APPs_received_events_table "
                                                              "where installedAppId = ? and ID > ? "
                                                              "order by ID LIMIT  1",
                                                              False, (receivedAppEvent[31],
                                                                      receivedAppEvent[0])).fetchone()

        if nextReceivedAppEventRowNumber is None:
            sentCommands = database.executeQuery("select * from APPs_commands_table "
                                                 "where Authorization = ? and rowNumber > ?",
                                                 False, ("Bearer " + authToken,
                                                         rowNumber,)).fetchall()
        else:
            sentCommands = database.executeQuery("select * from APPs_commands_table "
                                                 "where Authorization = ? and rowNumber > ? and rowNumber <= ?",
                                                 False, ("Bearer " + authToken,
                                                         rowNumber,
                                                         nextReceivedAppEventRowNumber[0],)).fetchall()

        return sentCommands

    def getApplicationSentModeCommands(self, receivedAppEvent):
        authToken = receivedAppEvent[30]
        rowNumber = receivedAppEvent[69]

        nextReceivedAppEventRowNumber = database.executeQuery("select rowNumber from APPs_received_events_table "
                                                              "where installedAppId = ? and ID > ? "
                                                              "order by ID LIMIT  1",
                                                              False, (receivedAppEvent[31],
                                                                      receivedAppEvent[0])).fetchone()

        if nextReceivedAppEventRowNumber is None:
            sentModeCommands = database.executeQuery("select * from apps_mode_commands_table "
                                                     "where authorization_req = ? and rowNumber > ?",
                                                     False, ("Bearer " + authToken,
                                                             rowNumber,)).fetchall()
        else:
            sentModeCommands = database.executeQuery("select * from apps_mode_commands_table "
                                                     "where authorization_req = ? and rowNumber > ? and rowNumber <= ?",
                                                     False, ("Bearer " + authToken,
                                                             rowNumber, nextReceivedAppEventRowNumber[0],)).fetchall()

        return sentModeCommands

    def getApplicationModeCommandModeEvent(self, sentModeCommand, botId):
        if self.getBotId() != botId:
            raise Exception('Application mode command does not belong to this Application Bot!')

        locationId = sentModeCommand[2][38:74]
        requestPayload = json.loads(sentModeCommand[12])
        responsePayload = json.loads(sentModeCommand[25])
        modeName = responsePayload["name"]
        modeId = requestPayload["modeId"]

        modeCommandList = []
        applicationModeCommands = database.executeQuery("SELECT * FROM apps_mode_commands_table "
                                                        "WHERE link = ? AND "
                                                        "payload = ? "
                                                        "ORDER BY date_res", False,
                                                        (sentModeCommand[2], sentModeCommand[12])).fetchall()

        for row in applicationModeCommands:
            date = datetime.strptime(row[14], '%a, %d %b %Y %H:%M:%S GMT')
            dic = {
                "id": row[0],
                "date": date.__str__(),
                "source": "application"
            }
            modeCommandList.append(dic)

        # Simulator mode commands check-up goes here
        simulatorModeCommands = database.executeQuery("SELECT id, date_res FROM simulator_mode_commands_table where "
                                                      "id_ = ? and mode_id = ? ORDER BY date_res", False,
                                                      (locationId, modeId)).fetchall()
        for row in simulatorModeCommands:
            date = datetime.strptime(row[1], '%a, %d %b %Y %H:%M:%S GMT')
            dic = {
                "id": row[0],
                "date": date.__str__(),
                "source": "simulator"
            }
            modeCommandList.append(dic)

        sortedList = sorted(modeCommandList, key=key_function)

        targetModeCommandIndex = None
        counter = 0

        for row in sortedList:
            if row['id'] == sentModeCommand[0]:
                targetModeCommandIndex = counter
            counter += 1

        if targetModeCommandIndex is not None:
            modeEvents = database.executeQuery(
                "select * from mode_events_table where value = ? and locationId = ? order by unixTime", False,
                (modeName, locationId,)).fetchall()

            if targetModeCommandIndex >= len(modeEvents):
                return None

            modeEvent = modeEvents[targetModeCommandIndex]

            return modeEvent
        else:
            raise Exception("Target mode event was not found!")

    def getApplicationSentNotifications(self, receivedAppEvent):
        authToken = receivedAppEvent[30]
        rowNumber = receivedAppEvent[69]
        nextReceivedAppEventRowNumber = database.executeQuery("select rowNumber from APPs_received_events_table "
                                                              "where installedAppId = ? and ID > ? "
                                                              "order by ID LIMIT  1",
                                                              False, (receivedAppEvent[31],
                                                                      receivedAppEvent[0])).fetchone()
        if nextReceivedAppEventRowNumber is None:
            sentNotifications = database.executeQuery("select * from notifications "
                                                      "where authorization_req = ? and rowNumber > ?",
                                                      False, ("Bearer " + authToken, rowNumber,)).fetchall()
        else:
            sentNotifications = database.executeQuery("select * from notifications "
                                                      "where authorization_req = ? and rowNumber > ? and rowNumber <= ?",
                                                      False, ("Bearer " + authToken, rowNumber,
                                                              nextReceivedAppEventRowNumber[0],)).fetchall()

        return sentNotifications

    def getApplicationDevicePermissions(self, targetDeviceId):
        """
        Get application's permissions for a particular IoT device.

        :return: Apps' Permissions in different time periods
        """
        appInstallUpdateData = \
            database.executeQuery("select * from apps_install_update_table where "
                                  "json_extract(apps_install_update_table.installData, "
                                  "'$.installedApp.installedAppId') = ? or "
                                  "json_extract(apps_install_update_table.updateData, "
                                  "'$.installedApp.installedAppId') = ? order by date_req", False,
                                  (self.getBotId(), self.getBotId(), )).fetchall()
        permissionsDicList = []

        for appData in appInstallUpdateData:
            if appData[1] == 'INSTALL':
                Data = json.loads(appData[8])
                lifecycle = 'INSTALL'
            elif appData[1] == 'UPDATE':
                Data = json.loads(appData[7])
                lifecycle = 'UPDATE'
            else:
                raise Exception('Unsupported lifecycle event is detected!')

            permissions = Data['installedApp']['permissions']
            date = appData[24]
            locationId = Data['installedApp']['locationId']
            targetDevicePermissions = []

            for permission in permissions:
                if 'devices' in permission:
                    deviceId = permission[-36:]
                    if targetDeviceId == deviceId:
                        targetDevicePermissions.append(permission[0:1])

            if len(targetDevicePermissions) == 0:
                return None

            permissionsDic = {
                "installedAppId": self.getBotId(),
                "lifecycle": lifecycle,
                "deviceId": targetDeviceId,
                "locationId": locationId,
                "date": date,
                "permissions": targetDevicePermissions
            }
            permissionsDicList.append(permissionsDic)

        return permissionsDicList


def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False


def key_function(item_dictionary):
    return item_dictionary['date']
