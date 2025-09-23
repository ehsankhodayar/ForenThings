import csv
import os
import sys
import threading
import time

sys.path.append('..')
import forenlog.loggingModule
from datetime import datetime, timezone
from os import path
from threading import Thread
from memory_profiler import memory_usage
from frontend import visualization
from bots import botGenerator, questionerBot
from database import database

iotBotsList = []
appBotsList = []
threadPool = []
graphResponseTimeStatisticsDic = {}
graphMemoryStatisticsDic = {}
botGenerationStatistics = {}


def chooseOperation():
    print("\n\033[0mSelect an option:")
    print("1.Log Manager")
    print("2.Forensics Investigation")
    print("3.Exit")

    optionNumber = input("Option Number: ")

    if optionNumber == '1':
        manageLogs()
        return chooseOperation()
    elif optionNumber == '2':
        return forensicsInvestigation()
    elif optionNumber == '3':
        sys.exit()
    else:
        print("\033[91mOption number is not supported!")
        return chooseOperation()


def manageLogs():
    print('\n\033[0mLog Manager option is selected')
    return forenlog.loggingModule.startForenLog()


def forensicsInvestigation():
    print('\n\033[0mForensics Investigation option is selected')
    print("Select the investigation type:")
    print("1.Global Investigation")
    print("2.Device Investigation")
    print("3.Location Investigation")
    print("4.Back")
    optionNumber = input("Option Number: ")
    global investigationOption
    investigationOption = askInvestigationOptions()

    if optionNumber == '1':
        multithreading = askMultithreadingOption()
        return globalInvestigation(multithreading=multithreading)
    elif optionNumber == '2':
        return deviceInvestigation()
    elif optionNumber == '3':
        return locationInvestigation()
    elif optionNumber == '4':
        return chooseOperation()
    else:
        print("\033[91mOption number is not supported!")
        return forensicsInvestigation()


def askMultithreadingOption():
    print('\n\033[0mMultithreading option:')
    answer = input("Do you want to activate the multithreading option to enhance the investigation speed? (yes/no): ")

    if answer == 'yes' or answer == 'y' or answer == '':
        return True
    elif answer == 'no' or answer == 'n':
        return False
    else:
        print("\033[91mInvalid answer!")
        return askMultithreadingOption()


def askInvestigationOptions():
    print("\n\033[0mSelect the desirable investigation option:")
    print("1.ForenFull: Includes both backward & forward investigations")
    print("2.ForenBack: Includes backward investigation only")
    print("3.ForenBackComplete: Includes a complete backward investigation")
    print("4.ForenForward: Includes forward investigation only")
    optionNumber = input("Option Number: ")

    if optionNumber == '1':
        return 'ForenFull'
    elif optionNumber == '2':
        return 'ForenBack'
    elif optionNumber == '3':
        return 'ForenBackComplete'
    elif optionNumber == '4':
        return 'ForenForward'
    else:
        print("\033[91mOption number is not supported!")
        return askInvestigationOptions()


def globalInvestigation(minEventTime=None, maxEventTime=None, multithreading=True):
    print('\n\033[0mGlobal investigation option is selected')

    if minEventTime is None or maxEventTime is None:

        minDeviceEventTime = \
        database.executeQuery("select min(unixTime) from device_events_table where name != 'DeviceUpdated'",
                              False).fetchone()[0]
        maxDeviceEventTime = \
        database.executeQuery("select max(unixTime) from device_events_table where name != 'DeviceUpdated'",
                              False).fetchone()[0]

        minModeEventTime = database.executeQuery("select min(unixTime) from mode_events_table", False).fetchone()[0]
        maxModeEventTime = database.executeQuery("select max(unixTime) from mode_events_table", False).fetchone()[0]

        if minDeviceEventTime is None and minModeEventTime is None:
            print("\033[91mNo Event data is available!")
            return chooseOperation()

        if minModeEventTime:
            minTime = int(min(minDeviceEventTime, minModeEventTime)[0:10])
            maxTime = int(max(maxDeviceEventTime, maxModeEventTime)[0:10]) + 1
        else:
            minTime = int(minDeviceEventTime[0:10])
            maxTime = int(maxDeviceEventTime[0:10]) + 1
    else:
        minTime = minEventTime
        maxTime = maxEventTime

    startTimeWindow = datetime.utcfromtimestamp(minTime).strftime('%Y-%m-%d %H:%M:%S')
    endTimeWindow = datetime.utcfromtimestamp(maxTime).strftime('%Y-%m-%d %H:%M:%S')

    print('The valid time window is from \033[94m' +
          startTimeWindow + ' \033[0mTo \033[94m' + endTimeWindow + '\033[0m')
    print("Please select a time period between the time window mentioned above")

    startEventSearchFromInput = input("Start Time (Y-M-D H:M:S): ")
    try:
        if startEventSearchFromInput == '':
            startEventSearchFrom = minTime
            startEventSearchFromInput = startTimeWindow
        else:
            startEventSearchFrom = int(datetime.strptime(startEventSearchFromInput, '%Y-%m-%d %H:%M:%S')
                                       .replace(tzinfo=timezone.utc).timestamp())
    except:
        print("\033[91mInvalid time window!")
        return globalInvestigation(minTime, maxEventTime, multithreading)

    endEventSearchAtInput = input("End Time (Y-M-D H:M:S): ")
    try:
        if endEventSearchAtInput == '':
            endEventSearchAt = maxTime
            endEventSearchAtInput = endTimeWindow
        else:
            endEventSearchAt = int(datetime.strptime(endEventSearchAtInput, '%Y-%m-%d %H:%M:%S')
                                   .replace(tzinfo=timezone.utc).timestamp())
    except:
        print("\033[91mInvalid time window!")
        return globalInvestigation(minTime, maxEventTime, multithreading)

    if startEventSearchFrom < minTime or startEventSearchFrom > maxTime or endEventSearchAt > maxTime or \
            endEventSearchAt < minTime or endEventSearchAt < startEventSearchFrom:
        print("\033[91mInvalid time window!")
        return globalInvestigation(minTime, maxEventTime, multithreading)
    else:
        if len(iotBotsList) == 0 or len(appBotsList) == 0:
            iotBotsList.clear()
            appBotsList.clear()

            print("Loading IoT and Application Bots...")
            generateBots()

        print("Finding suitable events...")
        devicesEventsList = []

        for iotBot in iotBotsList:
            deviceEvents = iotBot.getDeviceEvents(startEventSearchFrom, endEventSearchAt)
            devicesEventsList.extend(deviceEvents)

        print(
            "Suitable device events from \033[94m" + startEventSearchFromInput +
            " \033[0mTo \033[94m" + endEventSearchAtInput + " \033[0mare:\n")

        for event in devicesEventsList:
            print("\033[94mEvent ID: \033[92m" + event[1] + " \033[94mDescription: \033[92m" +
                  event[4] + ' \033[94mDevice Name: \033[92m' + event[8] + ' \033[94mDate: \033[92m' +
                  event[9] + ' \033[94mAttribute: \033[92m' + event[16] + ' \033[94mValue: \033[92m' +
                  event[11] + ' \033[94mDevice ID: \033[92m' + event[15] + ' \033[94mDTH ID: \033[92m' +
                  event[19] + ' \033[94mLocation ID: \033[92m' + event[17] + ' \033[94mEvent Source: \033[92m' +
                  event[18])

        locationEvents = database.executeQuery("select * from mode_events_table where unixTime >= ? and "
                                               "unixTime <= ?", False,
                                               (startEventSearchFrom, endEventSearchAt,)).fetchall()

        print(
            "\033[0mSuitable location events from \033[94m" + startEventSearchFromInput +
            " \033[0mTo \033[94m" + endEventSearchAtInput + " \033[0mare:\n")

        for event in locationEvents:
            print("\033[94mEvent ID: \033[92m" + event[1] + " \033[94mDescription: \033[92m" +
                  event[4] + ' \033[94mDate: \033[92m' + event[9] + ' \033[94mAttribute: \033[92m' +
                  event[16] + ' \033[94mValue: \033[92m' + event[11] + ' \033[94mLocation ID: \033[92m' +
                  event[17] + ' \033[94mEvent Source: \033[92m' + event[18])

        destination = askDestination()
        coveredEvents = loadRecoveredEvents(destination)

        for deviceEvent in devicesEventsList:
            if deviceEvent[1] in coveredEvents:
                continue

            if multithreading:
                thread = Thread(target=startInvestigationProcess,
                                args=(deviceEvent, 'DEVICE_EVENT', destination, False, True))
                thread.start()
                threadPool.append(thread)
            else:
                startInvestigationProcess(deviceEvent, 'DEVICE_EVENT', destination, False)

        for modeEvent in locationEvents:
            if modeEvent[1] in coveredEvents:
                continue

            if multithreading:
                thread = Thread(target=startInvestigationProcess,
                                args=(modeEvent, 'MODE_EVENT', destination, False, True))
                thread.start()
                threadPool.append(thread)
            else:
                startInvestigationProcess(modeEvent, 'MODE_EVENT', destination, False)

        # Saving statistics when all children threads are finished
        if multithreading:
            while 1:
                if len(threadPool) == 0:
                    saveStatistics(destination)
                    break
                else:
                    time.sleep(10)
        else:
            saveStatistics(destination)


def askDestination():
    destination = input("\n\033[0mDestination Path: ")

    if path.exists(destination):
        return destination
    else:
        print("\033[91mDestination path is not valid!")
        return askDestination()


def locationInvestigation():
    print('\n\033[0mLocation investigation option is selected')

    minModeEventTime = database.executeQuery("select min(unixTime) from mode_events_table", False).fetchone()[0]
    maxModeEventTime = database.executeQuery("select max(unixTime) from mode_events_table", False).fetchone()[0]

    if minModeEventTime is None or maxModeEventTime is None:
        print("\033[91mNo Location event is available!")
        return chooseOperation()

    minModeEventTime = int(minModeEventTime[0:10])
    maxModeEventTime = int(maxModeEventTime[0:10]) + 1

    startTimeWindow = datetime.utcfromtimestamp(minModeEventTime).strftime('%Y-%m-%d %H:%M:%S')
    endTimeWindow = datetime.utcfromtimestamp(maxModeEventTime).strftime('%Y-%m-%d %H:%M:%S')

    print('The valid time window is from \033[94m' +
          startTimeWindow + ' \033[0mTo \033[94m' + endTimeWindow + '\033[0m')
    print("Please select a time period between the time window mentioned above")

    startEventSearchFromInput = input("Start Time (Y-M-D H:M:S): ")
    try:
        if startEventSearchFromInput == '':
            startEventSearchFrom = minModeEventTime
            startEventSearchFromInput = startTimeWindow
        else:
            startEventSearchFrom = int(datetime.strptime(startEventSearchFromInput, '%Y-%m-%d %H:%M:%S')
                                       .replace(tzinfo=timezone.utc).timestamp())
    except:
        print("\033[91mInvalid time window!")
        return globalInvestigation(minModeEventTime, maxModeEventTime, False)

    endEventSearchAtInput = input("End Time (Y-M-D H:M:S): ")
    try:
        if endEventSearchAtInput == '':
            endEventSearchAt = maxModeEventTime
            endEventSearchAtInput = endTimeWindow
        else:
            endEventSearchAt = int(datetime.strptime(endEventSearchAtInput, '%Y-%m-%d %H:%M:%S')
                                   .replace(tzinfo=timezone.utc).timestamp())
    except:
        print("\033[91mInvalid time window!")
        return globalInvestigation(minModeEventTime, maxModeEventTime, False)

    if startEventSearchFrom < minModeEventTime or startEventSearchFrom > maxModeEventTime or \
            endEventSearchAt > maxModeEventTime or \
            endEventSearchAt < minModeEventTime or endEventSearchAt < startEventSearchFrom:
        print("\033[91mInvalid time window!")
        return globalInvestigation(minModeEventTime, maxModeEventTime, False)
    else:
        if len(iotBotsList) == 0 or len(appBotsList) == 0:
            iotBotsList.clear()
            appBotsList.clear()

            print("Loading IoT and Application Bots...")
            generateBots()

        print("Finding suitable events...")

        locationEvents = database.executeQuery("select * from mode_events_table where unixTime >= ? and "
                                               "unixTime <= ?", False,
                                               (startEventSearchFrom, endEventSearchAt,)).fetchall()

        print(
            "\033[0mSuitable location events from \033[94m" + startEventSearchFromInput +
            " \033[0mTo \033[94m" + endEventSearchAtInput + " \033[0mare:\n")

        eventIdsList = []
        for event in locationEvents:
            eventIdsList.append(event[1])
            print("\033[94mEvent ID: \033[92m" + event[1] + " \033[94mDescription: \033[92m" +
                  event[4] + ' \033[94mDate: \033[92m' + event[9] + ' \033[94mAttribute: \033[92m' +
                  event[16] + ' \033[94mValue: \033[92m' + event[11] + ' \033[94mLocation ID: \033[92m' +
                  event[17] + ' \033[94mEvent Source: \033[92m' + event[18])

        eventId = input("\033[0mEvent ID: ")

        if eventId in eventIdsList:
            eventIndex = eventIdsList.index(eventId)
            event = locationEvents[eventIndex]

            return startInvestigationProcess(event, 'MODE_EVENT')
        else:
            print("\033[91mEvent ID is not valid!")

            return locationInvestigation()


def deviceInvestigation():
    print('\n\033[0mDevice investigation option is selected')

    if len(iotBotsList) == 0 or len(appBotsList) == 0:
        iotBotsList.clear()
        appBotsList.clear()

        print("Loading IoT and Application Bots...")
        generateBots()

        if len(iotBotsList) == 0 or len(appBotsList) == 0:
            print("\033[91mNo Device event is available!")
            return chooseOperation()

    print("Please select a device ID from the following list of available IoT devices\n")

    idList = []
    for iotBot in iotBotsList:
        idList.append(iotBot.getBotId())
        print("\033[94mDevice ID: \033[92m" + iotBot.getBotId() + " \033[94mDevice Names: \033[92m" + str(
            iotBot.getDeviceNames()))

    deviceId = input("\n\033[0mDevice ID: ")

    if deviceId in idList:
        iotBot = botGenerator.getIotBot(deviceId)

        investigationType = input("\n\033[0mDevice Event Investigation (1) or Device Access Investigation (2): ")

        if investigationType == '1':
            return selectDeviceEvent(iotBot)
        elif investigationType == '2':
            return getDeviceAccessInformation(iotBot)
        else:
            print("\033[91mDevice investigation type is not valid!")
            return deviceInvestigation()
    else:
        print("\033[91mDevice ID is not valid!")
        return deviceInvestigation()


def getDeviceAccessInformation(iotBot):
    print('\n\033[0mThe Selected IoT Device is ' + iotBot.getBotId())

    questionerBotObject = questionerBot.QuestionerBot()
    investigationResult = questionerBotObject.startDeviceAccessInvestigation(iotBot.getBotId(), iotBotsList, appBotsList)
    destination = askDestination()

    saveInvestigationResult(investigationResult.root, iotBot.getBotId(), None, destination, True)


def selectDeviceEvent(iotBot):
    print('\n\033[0mThe Selected IoT Device is ' + iotBot.getBotId())

    validTimeWindow = iotBot.getDeviceEventsUnixTimeWindow()
    unixStart = int(validTimeWindow['firstEvent'][0:10])
    unixEnd = int(validTimeWindow['lastEvent'][0:10]) + 1
    startTime = datetime.utcfromtimestamp(unixStart).strftime('%Y-%m-%d %H:%M:%S')
    endTime = datetime.utcfromtimestamp(unixEnd).strftime('%Y-%m-%d %H:%M:%S')

    print('The valid time window for this IoT device is from \033[94m' +
          startTime + ' \033[0mTo \033[94m' + endTime + '\033[0m')
    print("Please select a time period between the time window mentioned above")

    startEventSearchFromInput = input("Start Time (Y-M-D H:M:S): ")
    try:
        if startEventSearchFromInput == '':
            startEventSearchFrom = unixStart
            startEventSearchFromInput = startTime
        else:
            startEventSearchFrom = int(datetime.strptime(startEventSearchFromInput, '%Y-%m-%d %H:%M:%S')
                                       .replace(tzinfo=timezone.utc).timestamp())
    except:
        print("\033[91mInvalid time window!")
        return selectDeviceEvent(iotBot)

    endEventSearchAtInput = input("End Time (Y-M-D H:M:S): ")
    try:
        if endEventSearchAtInput == '':
            endEventSearchAt = unixEnd
            endEventSearchAtInput = endTime
        else:
            endEventSearchAt = int(datetime.strptime(endEventSearchAtInput, '%Y-%m-%d %H:%M:%S')
                                   .replace(tzinfo=timezone.utc).timestamp())
    except:
        print("\033[91mInvalid time window!")
        return selectDeviceEvent(iotBot)

    if startEventSearchFrom < unixStart or startEventSearchFrom > unixEnd or endEventSearchAt > unixEnd or \
            endEventSearchAt < unixStart or endEventSearchAt < startEventSearchFrom:
        print("\033[91mInvalid time window!")
        return selectDeviceEvent(iotBot)
    else:
        print("Finding suitable device events...")
        eventsList = iotBot.getDeviceEvents(startEventSearchFrom, endEventSearchAt)

        print("Please select an event ID from the following list of available device events:\n")
        print(
            "Suitable device events from \033[94m" + startEventSearchFromInput +
            " \033[0mTo \033[94m" + endEventSearchAtInput + " \033[0mare:\n")

        eventIdsList = []
        for event in eventsList:
            eventIdsList.append(event[1])
            print("\033[94mEvent ID: \033[92m" + event[1] + " \033[94mDescription: \033[92m" +
                  event[4] + ' \033[94mDevice Name: \033[92m' + event[8] + ' \033[94mDate: \033[92m' +
                  event[9] + ' \033[94mAttribute: \033[92m' + event[16] + ' \033[94mValue: \033[92m' +
                  event[11] + ' \033[94mDevice ID: \033[92m' + event[15] + ' \033[94mDTH ID: \033[92m' +
                  event[19] + ' \033[94mLocation ID: \033[92m' + event[17] + ' \033[94mEvent Source: \033[92m' +
                  event[18])

        eventId = input("\033[0mEvent ID: ")

        if eventId in eventIdsList:
            eventIndex = eventIdsList.index(eventId)
            event = eventsList[eventIndex]

            return startInvestigationProcess(event, 'DEVICE_EVENT')
        else:
            print("\033[91mEvent ID is not valid!")

            return selectDeviceEvent(iotBot)


def startInvestigationProcess(event, eventType, destination=None, showResult=True, multithreading=False):
    print("\nStarting event investigation process for \033[92m" + str(event) + '\033[0m')

    if investigationOption == 'ForenFull':
        backwardInvestigation = True
        backwardInvestigationComplete = True
        forwardInvestigation = True
    elif investigationOption == 'ForenBack':
        backwardInvestigation = True
        backwardInvestigationComplete = False
        forwardInvestigation = False
    elif investigationOption == 'ForenBackComplete':
        backwardInvestigation = True
        backwardInvestigationComplete = True
        forwardInvestigation = False
    elif investigationOption == 'ForenForward':
        backwardInvestigation = False
        backwardInvestigationComplete = False
        forwardInvestigation = True
    else:
        raise Exception("Unsupported investigation option is detected!")

    if eventType == 'DEVICE_EVENT' or eventType == 'MODE_EVENT':
        print("Event Type: \033[92m" + eventType + "\033[0m\n")
        investigationResult = None
        startTime = None
        finishTime = None
        investigationTime = None
        numNodes = None

        def runQuestionerBot():
            nonlocal startTime
            startTime = round(time.time() * 1000)
            nonlocal investigationResult
            questionerBotObject = questionerBot.QuestionerBot()
            investigationResult = \
                questionerBotObject.startEventInvestigation(event, eventType, iotBotsList, appBotsList,
                                                            backwardInvestigation, forwardInvestigation, backwardInvestigationComplete)
            nonlocal finishTime
            finishTime = round(time.time() * 1000)
            nonlocal investigationTime
            investigationTime = finishTime - startTime
            nonlocal numNodes
            numNodes = len(investigationResult.root.descendants) + 1
            return investigationResult

        mem_usage = memory_usage(runQuestionerBot, interval=0.1)

        if numNodes not in graphResponseTimeStatisticsDic:
            graphResponseTimeStatisticsDic[numNodes] = []

        executionTimeList = graphResponseTimeStatisticsDic[numNodes]
        executionTimeList.append(investigationTime)
        graphResponseTimeStatisticsDic[numNodes] = executionTimeList

        if numNodes not in graphMemoryStatisticsDic:
            graphMemoryStatisticsDic[numNodes] = []

        memoryUsageList = graphMemoryStatisticsDic[numNodes]
        memoryUsageList.append(max(mem_usage))
        graphMemoryStatisticsDic[numNodes] = memoryUsageList

        currentGraphStatistics = {
            'numberOfNodes': numNodes,
            'startTime': startTime,
            'finishTime': finishTime,
            'investigationTime': investigationTime,
            'minMemoryUsage': min(mem_usage),
            'maxMemoryUsage': max(mem_usage),
            'avgMemoryUsage': sum(mem_usage) / len(mem_usage)
        }

        print("\n\033[92mEvent investigation process is finished.")

        thread = Thread(target=saveInvestigationResult, args=(investigationResult, event[1], currentGraphStatistics,
                                                              destination, showResult))

        if multithreading:
            removeThreadFromPool(threading.current_thread())

        return thread.start()
    else:
        raise Exception("Event type is not supported!")


def saveInvestigationResult(investigationResult, sourceEventId, graphStatistics, destination=None, showResult=True):
    if investigationResult is None:
        raise Exception("Investigation results cannot be None!")
    else:
        print("\n\033[0mSaving investigation results...")

        if destination is None:
            destination = input("Destination Path: ")

        if path.exists(destination):
            now = int(time.time())
            directory = destination + '/' + str(now) + '_' + str(sourceEventId)
            os.mkdir(directory)

            visualization.graphVisualization(investigationResult, sourceEventId, directory, showResult, now)
            visualization.saveTxtFormat(investigationResult, sourceEventId, directory, showResult, now)

            # Saving Statistics
            if graphStatistics is not None:
                fileDir = directory + '/graph-statistics.txt'
                txtContent = "Number of Recovered Nodes: " + str(graphStatistics['numberOfNodes']) + "\nStart Time: " + \
                             str(graphStatistics['startTime']) + "\nFinish Time: " + str(graphStatistics['finishTime']) + \
                             '\nInvestigation Time: ' + str(graphStatistics['investigationTime']) + \
                             '\nMin Memory Usage (Mib/100 ms): ' + str(graphStatistics['minMemoryUsage']) + \
                             '\nMax Memory Usage (Mib/100 ms): ' + str(graphStatistics['maxMemoryUsage']) + \
                             '\nAverage Memory Usage (Mib/100 ms): ' + str(graphStatistics['avgMemoryUsage'])
                with open(fileDir, "x", encoding="utf-8") as f:
                    f.write(txtContent)

            print("\033[92mInvestigation results have been saved successfully in " + destination)
            return directory
        else:
            print("\033[91mDestination path is not valid!")

            return saveInvestigationResult(investigationResult, sourceEventId, graphStatistics, None, showResult, )


def saveStatistics(destination):
    if destination is None:
        raise Exception("Directory cannot be None!")

    if path.exists(destination):
        fileDir1 = destination + '/graph-response-time-statistics.csv'
        fileDir2 = destination + '/graph-memory-usage-statistics.csv'
        fileDir3 = destination + '/bot-generation-statistics.txt'
        header1 = graphResponseTimeStatisticsDic.keys()
        header2 = graphMemoryStatisticsDic.keys()
        lists = graphResponseTimeStatisticsDic.values()
        maxLength = max(len(x) for x in lists)

        for key in graphResponseTimeStatisticsDic:
            if len(graphResponseTimeStatisticsDic[key]) < maxLength:
                difference = maxLength - len(graphResponseTimeStatisticsDic[key])
                newList1 = []
                newList2 = []
                newList1.extend(graphResponseTimeStatisticsDic[key])
                newList2.extend(graphMemoryStatisticsDic[key])

                for x in range(difference):
                    newList1.append("Null")
                    newList2.append("Null")

                graphResponseTimeStatisticsDic[key] = newList1
                graphMemoryStatisticsDic[key] = newList2

        with open(fileDir1, "w") as f:
            writer = csv.writer(f)
            writer.writerow(header1)
            writer.writerows(zip(*graphResponseTimeStatisticsDic.values()))

        with open(fileDir2, "w") as f:
            writer = csv.writer(f)
            writer.writerow(header2)
            writer.writerows(zip(*graphMemoryStatisticsDic.values()))

        with open(fileDir3, "x", encoding="utf-8") as f:
            txtContent = "Number of IoT Bots: " + str(botGenerationStatistics['numIoTBots']) + \
                         '\nIoT Bot Generation Latency: ' + str(botGenerationStatistics['iotBotGenerationLatency']) + \
                         '\nNumber of Application Bots: ' + str(botGenerationStatistics['numAppBots']) + \
                         '\nApplication Bot Generation Latency: ' + \
                         str(botGenerationStatistics['appBotGenerationLatency']) + \
                         '\nTotal Device Events: ' + str(botGenerationStatistics['numDeviceEvents']) + \
                         '\nTotal Mode Events: ' + str(botGenerationStatistics['numModeEvents']) + \
                         '\nTotal Events: ' + str(botGenerationStatistics['totalEvents'])

            f.write(txtContent)

    else:
        raise Exception("Directory does not exist!")


def loadRecoveredEvents(destination):
    dirList = os.walk(destination)
    coverEvents = []
    for i in dirList:
        dirName = i[0][len(destination)+12:]
        if dirName != '':
            coverEvents.append(i[0][len(destination)+12:])

    return coverEvents


def generateBots():
    # Generating IoT Bots
    iotBotGenerationStartTime = round(time.time() * 1000)

    iotBotsList.extend(botGenerator.generateIotBots())

    iotBotGenerationFinishTime = round(time.time() * 1000)
    iotBotGenerationExecutionTime = iotBotGenerationFinishTime - iotBotGenerationStartTime
    numIotBots = len(iotBotsList)

    # Generating Application Bots
    appBotGenerationStartTime = round(time.time() * 1000)

    appBotsList.extend(botGenerator.generateApplicationBots())

    appBotGenerationFinishTime = round(time.time() * 1000)
    appBotGenerationExecutionTime = appBotGenerationFinishTime - appBotGenerationStartTime
    numAppBots = len(appBotsList)

    # Events
    numDeviceEvents = database.executeQuery("select count(*) from device_events_table where name != 'DeviceUpdated'",
                                            False).fetchone()
    numModeEvents = database.executeQuery('select count(*) from mode_events_table', False).fetchone()
    totalEvents = numDeviceEvents[0] + numModeEvents[0]

    botGenerationStatistics['numIoTBots'] = numIotBots
    botGenerationStatistics['iotBotGenerationLatency'] = iotBotGenerationExecutionTime
    botGenerationStatistics['numAppBots'] = numAppBots
    botGenerationStatistics['appBotGenerationLatency'] = appBotGenerationExecutionTime
    botGenerationStatistics['numDeviceEvents'] = numDeviceEvents[0]
    botGenerationStatistics['numModeEvents'] = numModeEvents[0]
    botGenerationStatistics['totalEvents'] = totalEvents


def removeThreadFromPool(thread):
    threadPool.remove(thread)


if __name__ == '__main__':
    chooseOperation()
