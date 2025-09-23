import calendar

from bots import bot
import database.database
from database import database
from datetime import datetime


class IotBotClass(bot.BotClass):
    availableGroupedEvents = {}

    def __init__(self, bot_id):
        """
        To create a new IoT bot, you should use this class.

        :param bot_id: IoT device ID
        """
        super().__init__(bot_id)

    def getDeviceNames(self):
        deviceId = self.getBotId()
        deviceNames = database.executeQuery("select DISTINCT linkText from device_events_table where "
                                            "deviceId = ?", False, (deviceId,)).fetchall()
        return deviceNames[0]

    def getDeviceEvents(self, startTime, endTime):
        return database.executeQuery("select * from device_events_table where deviceId = ? and name != 'DeviceUpdated'"
                                     "and unixTime >= ? and unixTime <= ?", False,
                                     (self.getBotId(), startTime, endTime,)).fetchall()

    def getDeviceEventsUnixTimeWindow(self):
        start = database.executeQuery("select min(unixTime) from device_events_table where "
                                      "deviceId = ?  and name != 'DeviceUpdated'", False, (self.getBotId(),)).fetchone()

        end = database.executeQuery("select max(unixTime) from device_events_table where "
                                    "deviceId = ? and name != 'DeviceUpdated'", False, (self.getBotId(),)).fetchone()

        return {
            'deviceId': self.getBotId(),
            'firstEvent': start[0],
            'lastEvent': end[0]
        }

    def groupDeviceEvent(self, event_id):
        """
        Group relevant device events and the source command to the given event_id

        :param event_id: The target device event ID
        :return: Relevant device events and the source command event if any exists
        """
        if event_id in self.availableGroupedEvents:
            return self.availableGroupedEvents.get(event_id)

        if self.checkIdFormat(event_id):
            signatureId = event_id
            stablePart = signatureId[9:]

            eventUnixTime = database.executeQuery("select unixTime from device_events_table where event_id = ? ", False,
                                                  (event_id,)).fetchone()[0]
            relatedDeviceEvents = database.executeQuery("SELECT * FROM device_events_table WHERE event_id like ? AND "
                                                        "(deviceId = ?) AND abs(? - unixTime) <= 100", False,
                                                        ('%' + stablePart, self.getBotId(), eventUnixTime,)).fetchall()

            relatedDeviceEventsList = []
            earliestDeviceEventUnixTime = eventUnixTime
            earliestDeviceEventStableIdPart = stablePart

            for row in relatedDeviceEvents:
                relatedDeviceEventsList.append(row)

                if row[10] < eventUnixTime:
                    earliestDeviceEventUnixTime = row[10]
                    earliestDeviceEventStableIdPart = row[1]
                    earliestDeviceEventStableIdPart = earliestDeviceEventStableIdPart[9:]

            sourceCommandEvent = database.executeQuery("SELECT * FROM device_commands_events_table WHERE event_id "
                                                       "like ? AND (deviceId = ?) AND abs(? - unixTime) <= 200", False,
                                                       ("%" + earliestDeviceEventStableIdPart, self.getBotId(),
                                                        earliestDeviceEventUnixTime,)).fetchone()

            sourceCommand = None

            if sourceCommandEvent is not None:
                sourceCommand = self.getCommandEventApplicationCommand(sourceCommandEvent)

            deviceEventDic = {
                "relevantEvents": relatedDeviceEventsList,
                "sourceCommandEvent": sourceCommandEvent,
                "sourceCommand": sourceCommand,
                "iotBot": self
            }

            if event_id not in self.availableGroupedEvents:
                self.availableGroupedEvents[event_id] = deviceEventDic

            for relevantEvent in relatedDeviceEventsList:
                relevantEventId = relevantEvent[1]

                if relevantEventId != event_id:
                    if relevantEventId not in self.availableGroupedEvents:
                        self.availableGroupedEvents[relevantEventId] = deviceEventDic

            return deviceEventDic
        else:
            raise Exception("Device event format is not supported!")

    def groupPreviousDeviceEvents(self, currentGroupedDeviceEvents):
        if currentGroupedDeviceEvents is None:
            raise Exception("Current grouped device events cannot be None!")

        currentRelevantEvents = currentGroupedDeviceEvents['relevantEvents']
        firstEvent = currentRelevantEvents[0]

        if len(currentRelevantEvents) > 1:
            for deviceEvent in currentRelevantEvents:
                deviceEventUnixTime = deviceEvent[10]
                firstEventUnixTime = firstEvent[10]
                if deviceEventUnixTime < firstEventUnixTime:
                    firstEvent = deviceEvent

        firstEventId = firstEvent[0]
        firstEventDeviceId = firstEvent[15]
        firstEventUnixTime = firstEvent[10]
        previousDeviceEventBeforeCurrentFirstDeviceEvent = \
            database.executeQuery("select * from device_events_table where "
                                  "deviceId = ? and ID < ? and (? - unixTime) > 1000 order by ID DESC LIMIT 1",
                                  False, (firstEventDeviceId, firstEventId, firstEventUnixTime,)).fetchone()

        if previousDeviceEventBeforeCurrentFirstDeviceEvent is not None:
            previousDeviceEventId = previousDeviceEventBeforeCurrentFirstDeviceEvent[1]
            previousDeviceEventsGroup = self.groupDeviceEvent(previousDeviceEventId)
            previousDeviceEventsGroup['previousDeviceEvent'] = previousDeviceEventBeforeCurrentFirstDeviceEvent
            return previousDeviceEventsGroup
        else:
            return None

    def groupNextDeviceEvents(self, currentGroupedDeviceEvents):
        if currentGroupedDeviceEvents is None:
            raise Exception("Current grouped device events cannot be None!")

        currentRelevantEvents = currentGroupedDeviceEvents['relevantEvents']
        lastEvent = currentRelevantEvents[0]

        if len(currentRelevantEvents) > 1:
            for deviceEvent in currentRelevantEvents:
                deviceEventUnixTime = deviceEvent[10]
                firstEventUnixTime = lastEvent[10]
                if deviceEventUnixTime > firstEventUnixTime:
                    lastEvent = deviceEvent

        lastEventId = lastEvent[0]
        lastEventDeviceId = lastEvent[15]
        lastEventUnixTime = lastEvent[10]
        nextDeviceEventAfterCurrentLastDeviceEvent = \
            database.executeQuery("select * from device_events_table where deviceId = ? and ID > ? and "
                                  "(unixTime - ?) > 1000 order by ID ASC "
                                  "LIMIT 1", False, (lastEventDeviceId, lastEventId, lastEventUnixTime,)).fetchone()

        if nextDeviceEventAfterCurrentLastDeviceEvent is not None:
            nextDeviceEventId = nextDeviceEventAfterCurrentLastDeviceEvent[1]
            nextDeviceEventsGroup = self.groupDeviceEvent(nextDeviceEventId)
            nextDeviceEventsGroup['nextDeviceEvent'] = nextDeviceEventAfterCurrentLastDeviceEvent
            return nextDeviceEventsGroup
        else:
            return None

    def getCommandEventApplicationCommand(self, commandEvent):
        commandEventUnixTime = int(commandEvent[10])
        commandEvents = database.executeQuery("select * from device_commands_events_table where deviceId = ? and "
                                              "name = ? and value = ? and unixTime <= ? order by unixTime",
                                              False, (commandEvent[15],
                                                      commandEvent[16],
                                                      commandEvent[11],
                                                      commandEvent[10],)).fetchall()
        commandEventPosition = len(commandEvents)

        targetCommandIndex = commandEventPosition - 1

        commandList = []
        applicationCommands = database.executeQuery("SELECT * FROM APPs_commands_table "
                                                    "WHERE APPs_commands_table.URL like ? AND "
                                                    "APPs_commands_table.command = ?", False,
                                                    ("%/" + commandEvent[15] + "/commands",
                                                     commandEvent[11],)).fetchall()

        for row in applicationCommands:
            date = datetime.strptime(row[14], '%a, %d %b %Y %H:%M:%S GMT')
            appCommandUnixTime = calendar.timegm(date.timetuple()) * 1000

            # if appCommandUnixTime > commandEventUnixTime or abs(commandEventUnixTime - appCommandUnixTime) > 2000:
            #     continue

            if appCommandUnixTime > commandEventUnixTime + 1000:
                continue

            authToken = row[6][7:]
            appId = database.executeQuery("select * from APPs_received_events_table where authToken = ? LIMIT 1",
                                          False, (authToken,)).fetchone()[31]
            dic = {
                "id": row[0],
                "date": date.__str__(),
                "command": row,
                "installedAppId": appId,
                "rowNumber": row[25],
                "source": "application"
            }
            commandList.append(dic)

        simulatorCommands = database.executeQuery("select * from simulator_table where "
                                                  "id_ = ? and command = ?", False,
                                                  (commandEvent[15], commandEvent[11],)).fetchall()

        for row in simulatorCommands:
            date = datetime.strptime(row[28], '%a, %d %b %Y %H:%M:%S GMT')
            simCommandUnixTime = calendar.timegm(date.timetuple()) * 1000

            # if simCommandUnixTime > commandEventUnixTime or abs(commandEventUnixTime - simCommandUnixTime) > 2000:
            #     continue

            if simCommandUnixTime > commandEventUnixTime + 1000:
                continue

            dic = {
                "id": row[0],
                "date": date.__str__(),
                "command": row,
                "installedAppId": None,
                "rowNumber": row[33],
                "source": "simulator"
            }
            commandList.append(dic)

        if len(commandList) == 0:
            return None

        sortedList = sorted(commandList, key=self.key_function)

        try:
            sourceCommand = sortedList[targetCommandIndex]
        except:
            return None
        return sourceCommand

    def key_function(self, item_dictionary):
        return item_dictionary['rowNumber']

    def getAppCommandDeviceCommandEvent(self, appCommand):
        deviceId = appCommand[2][36:72]

        if deviceId != self.getBotId():
            raise Exception('Application command does not belong to this IoT Bot!')

        commandList = []
        applicationCommands = database.executeQuery("SELECT * FROM APPs_commands_table "
                                                    "WHERE APPs_commands_table.URL = ? AND "
                                                    "APPs_commands_table.command = ? "
                                                    "ORDER BY date", False,
                                                    (appCommand[2], appCommand[12])).fetchall()

        for row in applicationCommands:
            date = datetime.strptime(row[14], '%a, %d %b %Y %H:%M:%S GMT')
            dic = {
                "id": row[0],
                "date": date.__str__(),
                "rowNumber": row[25],
                "source": "application"
            }
            commandList.append(dic)

        simulatorCommands = database.executeQuery(
            "select ID, date_res, rowNumber from simulator_table where id_ = ? and command = ?",
            False, (deviceId, appCommand[12],)).fetchall()

        for row in simulatorCommands:
            date = datetime.strptime(row[1], '%a, %d %b %Y %H:%M:%S GMT')
            dic = {
                "id": row[0],
                "date": date.__str__(),
                "rowNumber": row[2],
                "source": "simulator"
            }
            commandList.append(dic)

        sortedList = sorted(commandList, key=self.key_function)

        targetCommandIndex = None
        counter = 0

        for row in sortedList:
            if row['id'] == appCommand[0]:
                targetCommandIndex = counter

            counter += 1

        if targetCommandIndex is not None:

            commandEvents = database.executeQuery(
                "select * from device_commands_events_table where deviceId = ? and value = ? order by unixTime", False,
                (deviceId, appCommand[12],)).fetchall()

            try:
                return commandEvents[targetCommandIndex]
            except:
                return None
        else:
            raise Exception("Target command event was not found!")

    def getCommandEventRelevantDeviceEvents(self, commandEvent):
        signatureId = commandEvent[1]
        stablePart = signatureId[9:]

        relatedDeviceEvents = database.executeQuery("SELECT * FROM device_events_table WHERE event_id like ? AND "
                                                    "(deviceId = ?) AND abs(? - unixTime) <= 100", False,
                                                    ('%' + stablePart, self.getBotId(), commandEvent[10],)).fetchall()

        return relatedDeviceEvents
