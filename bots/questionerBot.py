import json
import time
from datetime import datetime
from bots import botGenerator
from database import database
from anytree import Node, RenderTree


def removeDuplicateNodes(graph):
    graph = graph.root

    # Create a set to store the unique nodes
    unique_nodes = []

    # Iterate through the nodes in the graph
    for pre, fill, node in RenderTree(graph):
        # If the node is not already in the set, add it
        if node.name not in unique_nodes:
            unique_nodes.append(node.name)
        # If the node is already in the set, remove it from the tree
        else:
            node.parent = None
    return graph


class QuestionerBot:
    def __init__(self):
        self.iotBotsList = []
        self.appBotsList = []
        self.coveredApplicationReceivedEvents = []
        self.coveredDeviceEvents = []
        self.coveredModeEvents = []
        self.coveredDeviceEventsInForwardInvestigation = []
        self.coveredModeEventsInForwardInvestigation = []
        self.nodeDic = {}
        self.startEvent = None

        self.forwardInvestigation = True
        self.backwardInvestigation = True
        self.backwardInvestigationComplete = False

    def searchDeviceEvents(self):
        self.generateBots()

    def startDeviceAccessInvestigation(self, deviceId, iotBots, appBots):
        if len(iotBots) == 0 or len(appBots) == 0:
            raise Exception("List of bots or application bots cannot be empty!")
        else:
            self.iotBotsList.extend(iotBots)
            self.appBotsList.extend(appBots)

        iotBot = None

        for bot in self.iotBotsList:
            botId = bot.getBotId()

            if deviceId == botId:
                iotBot = bot

        if iotBot is None:
            raise Exception("The given device ID doesn't exist!")

        deviceNames = str(iotBot.getDeviceNames())

        # deviceNode = Node({'type': 'deviceAccess', 'value': [deviceId, deviceNames]}, None)
        deviceNode = self.createNewNode('deviceAccess', [deviceId, deviceNames], None)

        counter = 0
        for bot in self.appBotsList:
            permissionsDicList = bot.getApplicationDevicePermissions(deviceId)

            if permissionsDicList is not None:
                # appNode = Node({'type': 'appPermissions', 'value': [bot.getBotId()]}, parent=deviceNode)
                appNode = self.createNewNode('appPermissions', [bot.getBotId()], deviceNode)

                for permissionsDic in permissionsDicList:
                    # Node({'type': 'permissions', 'value': [counter, permissionsDic]}, parent=appNode)
                    self.createNewNode('permissions', [counter, permissionsDic], appNode)
                    counter += 1

        return deviceNode

    def startEventInvestigation(self, event, eventType, iotBots, appBots, backwardInvestigation=True,
                                forwardInvestigation=True, backwardInvestigationComplete=False):
        if len(iotBots) == 0 or len(appBots) == 0:
            raise Exception("List of bots or application bots cannot be empty!")
        else:
            self.iotBotsList.extend(iotBots)
            self.appBotsList.extend(appBots)

        self.backwardInvestigation = backwardInvestigation
        self.forwardInvestigation = forwardInvestigation
        self.backwardInvestigationComplete = backwardInvestigationComplete
        self.startEvent = event

        if self.backwardInvestigation == False and self.forwardInvestigation == False:
            raise Exception("Both backward investigation and forward investigation cannot be false!")

        if eventType == 'DEVICE_EVENT':
            if self.backwardInvestigation:
                investigationResult = removeDuplicateNodes(self.startDeviceEventBackwardInvestigation(event))
                return investigationResult
            else:
                investigationResult = removeDuplicateNodes(self.startEventForwardInvestigation(event))
                return investigationResult
        elif eventType == 'MODE_EVENT':
            if self.backwardInvestigation:
                investigationResult = removeDuplicateNodes(self.startModeEventBackwardInvestigation(event))
                return investigationResult
            else:
                investigationResult = removeDuplicateNodes(self.startEventForwardInvestigation(event, None, None, 'modeEvent'))
                return investigationResult
        else:
            raise Exception("Event type is not supported!")

    def startModeEventBackwardInvestigation(self, targetModeEvent, lastChild=None):
        if not self.backwardInvestigation:
            return None

        applicationModeCommandDic = self.backwardModeEvent(targetModeEvent)
        sourceEventNode = None

        if applicationModeCommandDic:
            if applicationModeCommandDic['source'] == 'application':
                sentModeCommand = applicationModeCommandDic['command']
                # appModeCommandNode = Node({'type': 'appModeCommand', 'value': sentModeCommand}, None)
                appModeCommandNode = self.createNewNode('appModeCommand', sentModeCommand, None)
                installedAppId = applicationModeCommandDic['installedAppId']

                if targetModeEvent[0] in self.coveredModeEvents:
                    raise Exception('Repetitive mode event is detected!')
                else:
                    self.coveredModeEvents.append(targetModeEvent[0])

                appBot = None
                for row in self.appBotsList:
                    if row.getBotId() == installedAppId:
                        appBot = row
                        break

                if appBot is None:
                    raise Exception("App bot is not available!")

                appReceivedEvent = appBot.getSentModeCommandSourceEvent(applicationModeCommandDic)

                if appReceivedEvent[0] not in self.coveredApplicationReceivedEvents:
                    self.coveredApplicationReceivedEvents.append(appReceivedEvent[0])
                else:
                    raise Exception('Repetitive app event investigation!')

                if appReceivedEvent:
                    # appNode = Node({'type': 'appEvent', 'value': appReceivedEvent}, None)
                    appNode = self.createNewNode('appEvent', appReceivedEvent, None)
                    appModeCommandNode.parent = appNode
                    eventType = appReceivedEvent[45]
                    appEvent = {
                        'event': appReceivedEvent,
                        'eventType': eventType
                    }
                    originalEvent = appBot.getApplicationReceivedEventOriginalEvent(appEvent)

                    if eventType == 'DEVICE_EVENT':
                        parentEventNode = self.startDeviceEventBackwardInvestigation(originalEvent, lastChild)
                    elif eventType == 'MODE_EVENT':
                        parentEventNode = self.startModeEventBackwardInvestigation(originalEvent, lastChild)
                    else:
                        raise Exception("Event type is not valid!")

                    appNode.parent = parentEventNode

                    if lastChild is not None:
                        lastChild.parent = parentEventNode
                    else:
                        # sourceEventNode = \
                        #     Node({'type': 'modeEvent', 'value': targetModeEvent}, parent=appModeCommandNode)
                        sourceEventNode = self.createNewNode('modeEvent', targetModeEvent, appModeCommandNode)

                self.startEventForwardInvestigation(targetModeEvent, appModeCommandNode, sourceEventNode, 'modeEvent')
            elif applicationModeCommandDic['source'] == 'simulator':
                sentModeCommand = applicationModeCommandDic['command']
                # appModeCommandNode = Node({'type': 'simulatorModeCommand', 'value': sentModeCommand}, None)
                appModeCommandNode = self.createNewNode('simulatorModeCommand', sentModeCommand, None)
                # sourceEventNode = \
                #     Node({'type': 'modeEvent', 'value': targetModeEvent}, parent=appModeCommandNode)
                sourceEventNode = self.createNewNode('modeEvent', targetModeEvent, appModeCommandNode)

                self.startEventForwardInvestigation(targetModeEvent, appModeCommandNode, sourceEventNode, 'modeEvent')

            return sourceEventNode
        else:
            # sourceEventNode = \
            #     Node({'type': 'modeEvent', 'value': targetModeEvent}, parent=None)
            sourceEventNode = self.createNewNode('modeEvent', targetModeEvent, None)
            self.startEventForwardInvestigation(targetModeEvent, None, sourceEventNode, 'modeEvent')
            return sourceEventNode

    def startDeviceEventBackwardInvestigation(self, targetDeviceEvent, lastChild=None):
        if not self.backwardInvestigation:
            return None

        backwardDeviceEventResult = self.groupDeviceEvents(targetDeviceEvent)
        commandEvent = backwardDeviceEventResult['sourceCommandEvent']
        sourceCommand = backwardDeviceEventResult['sourceCommand']
        sourceEventNode = self.createNewNode('deviceEvent', targetDeviceEvent, None)

        eventRelatedIoTBot = backwardDeviceEventResult['iotBot']

        if self.forwardInvestigation is False:
            if self.backwardInvestigationComplete is False:
                nextDeviceEventsGroup = None
            else:
                if self.startEvent == targetDeviceEvent:
                    nextDeviceEventsGroup = None
                else:
                    nextDeviceEventsGroup = eventRelatedIoTBot.groupNextDeviceEvents(backwardDeviceEventResult)
        else:
            nextDeviceEventsGroup = eventRelatedIoTBot.groupNextDeviceEvents(backwardDeviceEventResult)

        if nextDeviceEventsGroup is not None:
            nextDeviceEventSourceCommandEvent = nextDeviceEventsGroup['sourceCommandEvent']

            if nextDeviceEventSourceCommandEvent is None:
                if nextDeviceEventsGroup['nextDeviceEvent'][0] not in self.coveredDeviceEvents:
                    for relevantEvent in nextDeviceEventsGroup['relevantEvents']:
                        self.startEventForwardInvestigation(relevantEvent, sourceEventNode)

        if targetDeviceEvent[0] in self.coveredDeviceEvents:
            raise Exception('Repetitive device event is detected!')
        else:
            self.coveredDeviceEvents.append(targetDeviceEvent[0])

        if backwardDeviceEventResult['sourceCommandEvent'] is None:
            relevantDeviceEvents = backwardDeviceEventResult['relevantEvents']
            parentDeviceEventNode = None
            eventRelatedIoTBot = backwardDeviceEventResult['iotBot']
            previousDeviceEventsGroup = eventRelatedIoTBot.groupPreviousDeviceEvents(backwardDeviceEventResult)

            if previousDeviceEventsGroup is not None:
                previousDeviceEvent = previousDeviceEventsGroup['previousDeviceEvent']
                if previousDeviceEvent[0] not in self.coveredDeviceEvents:
                    parentDeviceEventNode = self.startDeviceEventBackwardInvestigation(previousDeviceEvent, None)
                    if lastChild is not None:
                        lastChild.parent = parentDeviceEventNode
            else:
                return sourceEventNode

            for relevantEvent in relevantDeviceEvents:

                if relevantEvent[0] in self.coveredDeviceEventsInForwardInvestigation:
                    continue

                # relevantEventNode = \
                #     Node({'type': 'deviceEvent', 'value': relevantEvent}, parent=parentDeviceEventNode)
                relevantEventNode = self.createNewNode('deviceEvent', relevantEvent, parentDeviceEventNode)
                self.startEventForwardInvestigation(relevantEvent,
                                               None, relevantEventNode)
            return parentDeviceEventNode

        if backwardDeviceEventResult:
            if sourceCommand is not None:
                if sourceCommand['source'] == 'application':
                    commandSourceEvent = self.backwardApplicationCommand(sourceCommand)

                    if commandSourceEvent:
                        installedAppId = commandSourceEvent[31]

                        if commandSourceEvent[45] == 'DEVICE_EVENT':
                            appEvent = {
                                'event': commandSourceEvent,
                                'eventType': 'DEVICE_EVENT'
                            }

                            appBot = None
                            for applicationBot in self.appBotsList:
                                if applicationBot.getBotId() == installedAppId:
                                    appBot = applicationBot
                                    break

                            if appBot is None:
                                raise Exception("Application bot doesn't exist!")

                            originalDeviceEvent = appBot.getApplicationReceivedEventOriginalEvent(appEvent)

                            if originalDeviceEvent not in self.coveredDeviceEvents:
                                originalDeviceEventNode = self.startDeviceEventBackwardInvestigation(
                                    originalDeviceEvent, None)
                            else:
                                # originalDeviceEventNode = \
                                #     Node({'type': 'deviceEvent', 'value': originalDeviceEvent})
                                originalDeviceEventNode = self.createNewNode('deviceEvent', originalDeviceEvent, None)

                            # commandSourceEventNode = \
                            #     Node({'type': 'appEvent', 'value': commandSourceEvent}, originalDeviceEventNode)
                            commandSourceEventNode = \
                                self.createNewNode('appEvent', commandSourceEvent, originalDeviceEventNode)
                            # commandNode = \
                            #     Node({'type': 'appCommand', 'value': sourceCommand['command']},
                            #          parent=commandSourceEventNode)
                            commandNode = self.createNewNode('appCommand', sourceCommand['command'], commandSourceEventNode)
                            # commandEventNode = \
                            #     Node({'type': 'commandEvent', 'value': commandEvent}, parent=commandNode)
                            commandEventNode = self.createNewNode('commandEvent', commandEvent, commandNode)

                            self.coveredApplicationReceivedEvents.append(commandSourceEvent[0])
                            self.startEventForwardInvestigation(originalDeviceEvent,
                                                                originalDeviceEventNode.parent,
                                                                originalDeviceEventNode)

                            if lastChild is not None:
                                lastChild.parent = commandEventNode
                            else:
                                # sourceEventNode = \
                                #     Node({'type': 'deviceEvent', 'value': targetDeviceEvent},
                                #          parent=commandEventNode)
                                sourceEventNode = self.createNewNode('deviceEvent', targetDeviceEvent, commandEventNode)

                            try:
                                forwardCommandSourceEventResult = \
                                    self.forwardApplicationReceivedEvent(commandSourceEvent, appBot)
                                appAllSentCommands = forwardCommandSourceEventResult['sentCommands']
                            except:
                                appAllSentCommands = None

                            if appAllSentCommands is not None:
                                for sentCommand in appAllSentCommands:
                                    if sentCommand != sourceCommand['command']:
                                        # newSentCommandNode = \
                                        #     Node({'type': 'appCommand', 'value': sentCommand},
                                        #          parent=commandSourceEventNode)
                                        newSentCommandNode = \
                                            self.createNewNode('appCommand', sentCommand, commandSourceEventNode)

                                        forwardNewSentCommandResults = self.forwardApplicationCommand(
                                            sentCommand)

                                        if forwardNewSentCommandResults is None:
                                            continue

                                        newSentCommandResultedCommandEvent = forwardNewSentCommandResults[
                                            'commandEvent']

                                        # newSentCommandResultedCommandEventNode = \
                                        #     Node({'type': 'commandEvent',
                                        #           'value': newSentCommandResultedCommandEvent},
                                        #          parent=newSentCommandNode)
                                        newSentCommandResultedCommandEventNode = \
                                            self.createNewNode('commandEvent', newSentCommandResultedCommandEvent,
                                                               newSentCommandNode)

                                        for newResultedDeviceEvent in forwardNewSentCommandResults[
                                            'resultedDeviceEvents']:
                                            self.startEventForwardInvestigation(newResultedDeviceEvent,
                                                                                newSentCommandResultedCommandEventNode)
                                    else:
                                        forwardNewSentCommandResults = self.forwardApplicationCommand(
                                            sentCommand)

                                        if forwardNewSentCommandResults is None:
                                            continue

                                        newSentCommandResultedCommandEvent = forwardNewSentCommandResults[
                                            'commandEvent']

                                        if commandEvent[0] == newSentCommandResultedCommandEvent[0]:
                                            newSentCommandResultedCommandEventNode = commandEventNode
                                        else:
                                            # newSentCommandNode = \
                                            #     Node({'type': 'appCommand', 'value': sentCommand},
                                            #          parent=commandSourceEventNode)
                                            newSentCommandNode = \
                                                self.createNewNode('appCommand', sentCommand, commandSourceEventNode)
                                            # newSentCommandResultedCommandEventNode = \
                                            #     Node({'type': 'commandEvent',
                                            #           'value': newSentCommandResultedCommandEvent},
                                            #          parent=newSentCommandNode)
                                            newSentCommandResultedCommandEventNode = \
                                                self.createNewNode('commandEvent', newSentCommandResultedCommandEvent,
                                                                   newSentCommandNode)

                                        for newResultedDeviceEvent in forwardNewSentCommandResults[
                                            'resultedDeviceEvents']:
                                            if newResultedDeviceEvent != targetDeviceEvent:
                                                self.startEventForwardInvestigation(newResultedDeviceEvent,
                                                                                    newSentCommandResultedCommandEventNode)
                                            elif newResultedDeviceEvent == targetDeviceEvent and lastChild is None:
                                                self.startEventForwardInvestigation(newResultedDeviceEvent,
                                                                                    newSentCommandResultedCommandEventNode,
                                                                                    sourceEventNode)
                                            elif newResultedDeviceEvent == targetDeviceEvent and lastChild is not None:
                                                self.startEventForwardInvestigation(newResultedDeviceEvent,
                                                                                    newSentCommandResultedCommandEventNode,
                                                                                    lastChild)
                        elif commandSourceEvent[45] == 'MODE_EVENT':
                            appEvent = {
                                'event': commandSourceEvent,
                                'eventType': 'MODE_EVENT'
                            }

                            for appBot in self.appBotsList:
                                if appBot.getBotId() == installedAppId:
                                    originalModeEvent = appBot.getApplicationReceivedEventOriginalEvent(appEvent)

                                    # originalModeEventNode = \
                                    #     Node({'type': 'modeEvent', 'value': originalModeEvent}, parent=None)
                                    # commandSourceEventNode = \
                                    #     Node({'type': 'appEvent', 'value': commandSourceEvent}, None)
                                    commandSourceEventNode = self.createNewNode('appEvent', commandSourceEvent, None)
                                    # commandNode = \
                                    #     Node({'type': 'appCommand', 'value': sourceCommand['command']},
                                    #          parent=commandSourceEventNode)
                                    commandNode = \
                                        self.createNewNode('appCommand', sourceCommand['command'],
                                                           commandSourceEventNode)
                                    # commandEventNode = \
                                    #     Node({'type': 'commandEvent', 'value': commandEvent}, parent=commandNode)
                                    commandEventNode = self.createNewNode('commandEvent', commandEvent, commandNode)

                                    self.coveredApplicationReceivedEvents.append(commandSourceEvent[0])
                                    originalModeEventNode = self.startModeEventBackwardInvestigation(originalModeEvent)
                                    commandSourceEventNode.parent = originalModeEventNode
                                    # startEventForwardInvestigation(originalModeEvent,
                                    #                                originalModeEventNode.parent,
                                    #                                originalModeEventNode, 'modeEvent')

                                    if lastChild is not None:
                                        lastChild.parent = commandEventNode
                                    else:
                                        # sourceEventNode = \
                                        #     Node({'type': 'deviceEvent', 'value': targetDeviceEvent},
                                        #          parent=commandEventNode)
                                        sourceEventNode = \
                                            self.createNewNode('deviceEvent', targetDeviceEvent, commandEventNode)

                                    try:
                                        forwardCommandSourceEventResult = \
                                            self.forwardApplicationReceivedEvent(commandSourceEvent, appBot)
                                        appAllSentCommands = forwardCommandSourceEventResult['sentCommands']
                                    except:
                                        appAllSentCommands = None

                                    if appAllSentCommands is not None:
                                        for sentCommand in appAllSentCommands:
                                            if sentCommand != sourceCommand['command']:
                                                # newSentCommandNode = \
                                                #     Node({'type': 'appCommand', 'value': sentCommand},
                                                #          parent=commandSourceEventNode)
                                                newSentCommandNode = \
                                                    self.createNewNode('appCommand', sentCommand,
                                                                       commandSourceEventNode)

                                                forwardNewSentCommandResults = self.forwardApplicationCommand(
                                                    sentCommand)

                                                if forwardNewSentCommandResults is None:
                                                    continue

                                                newSentCommandResultedCommandEvent = forwardNewSentCommandResults[
                                                    'commandEvent']

                                                # newSentCommandResultedCommandEventNode = \
                                                    # Node({'type': 'commandEvent',
                                                    #       'value': newSentCommandResultedCommandEvent},
                                                    #      parent=newSentCommandNode)
                                                newSentCommandResultedCommandEventNode = \
                                                    self.createNewNode('commandEvent',
                                                                       newSentCommandResultedCommandEvent,
                                                                       newSentCommandNode)

                                                for newResultedDeviceEvent in forwardNewSentCommandResults[
                                                    'resultedDeviceEvents']:
                                                    self.startEventForwardInvestigation(newResultedDeviceEvent,
                                                                                        newSentCommandResultedCommandEventNode)
                                            else:
                                                forwardNewSentCommandResults = self.forwardApplicationCommand(
                                                    sentCommand)

                                                if forwardNewSentCommandResults is None:
                                                    continue

                                                for newResultedDeviceEvent in forwardNewSentCommandResults[
                                                    'resultedDeviceEvents']:
                                                    if newResultedDeviceEvent != targetDeviceEvent:
                                                        self.startEventForwardInvestigation(newResultedDeviceEvent,
                                                                                            commandEventNode)
                                                    elif newResultedDeviceEvent == targetDeviceEvent and lastChild is None:
                                                        self.startEventForwardInvestigation(newResultedDeviceEvent,
                                                                                            commandEventNode,
                                                                                            sourceEventNode)
                                                    elif newResultedDeviceEvent == targetDeviceEvent and lastChild is not None:
                                                        self.startEventForwardInvestigation(newResultedDeviceEvent,
                                                                                            commandEventNode, lastChild)
                                    break

                elif sourceCommand['source'] == 'simulator':
                    # commandNode = Node({'type': 'simulatorCommand', 'value': sourceCommand['command']}, parent=None)
                    commandNode = self.createNewNode('simulatorCommand', sourceCommand['command'], None)
                    # commandEventNode = Node({'type': 'commandEvent', 'value': commandEvent}, parent=commandNode)
                    commandEventNode = self.createNewNode('commandEvent', commandEvent, commandNode)

                    if lastChild is not None:
                        lastChild.parent = commandEventNode
                    else:
                        # sourceEventNode = Node({'type': 'deviceEvent', 'value': targetDeviceEvent},
                        #                        parent=commandEventNode)
                        sourceEventNode = self.createNewNode('deviceEvent', targetDeviceEvent, commandEventNode)

                    if targetDeviceEvent[0] not in self.coveredDeviceEventsInForwardInvestigation:
                        self.startEventForwardInvestigation(targetDeviceEvent, commandEventNode, sourceEventNode)
                else:
                    raise Exception("Source application Command is not supported!")
            else:
                # commandEventNode = Node({'type': 'commandEvent', 'value': commandEvent}, parent=None)
                commandEventNode = self.createNewNode('commandEvent', commandEvent, None)
                # sourceEventNode = Node({'type': 'deviceEvent', 'value': targetDeviceEvent}, parent=commandEventNode)
                sourceEventNode = self.createNewNode('deviceEvent', targetDeviceEvent, commandEventNode)

                if targetDeviceEvent[0] not in self.coveredDeviceEventsInForwardInvestigation:
                    self.startEventForwardInvestigation(targetDeviceEvent, commandEventNode, sourceEventNode)
        else:
            raise Exception("Backward investigation for the give event returned None!")

        return sourceEventNode

    def startEventForwardInvestigation(self, targetEvent, parentNode=None, eventNode=None, eventType='deviceEvent'):
        if not self.forwardInvestigation and not self.backwardInvestigationComplete:
            return None

        if self.backwardInvestigationComplete and self.forwardInvestigation is False:
            if targetEvent == self.startEvent:
                # sourceEventNode = Node({'type': 'deviceEvent', 'value': targetEvent}, parent=parentNode)
                sourceEventNode = self.createNewNode('deviceEvent', targetEvent, parentNode)
                return sourceEventNode

        targetEventId = targetEvent[0]

        if eventType == 'deviceEvent':
            if targetEventId in self.coveredDeviceEventsInForwardInvestigation:
                return None
            else:
                self.coveredDeviceEventsInForwardInvestigation.append(targetEventId)

            if eventNode is None:
                # sourceEventNode = Node({'type': 'deviceEvent', 'value': targetEvent}, parent=parentNode)
                sourceEventNode = self.createNewNode('deviceEvent', targetEvent, parentNode)
            else:
                sourceEventNode = eventNode

            forwardEventResult = self.forwardDeviceEvent(targetEvent)

            backwardDeviceEventResult = self.groupDeviceEvents(targetEvent)
            try:
                eventRelatedIoTBot = backwardDeviceEventResult['iotBot']
                nextDeviceEventsGroup = eventRelatedIoTBot.groupNextDeviceEvents(backwardDeviceEventResult)
            except:
                nextDeviceEventsGroup = None

            if nextDeviceEventsGroup is not None:
                nextDeviceEventSourceCommandEvent = nextDeviceEventsGroup['sourceCommandEvent']

                if nextDeviceEventSourceCommandEvent is None:
                    for nextEvent in nextDeviceEventsGroup['relevantEvents']:
                        self.startEventForwardInvestigation(nextEvent, sourceEventNode)
        elif eventType == 'modeEvent':
            if targetEventId in self.coveredModeEventsInForwardInvestigation:
                return None
            else:
                self.coveredModeEventsInForwardInvestigation.append(targetEventId)

            forwardEventResult = self.forwardModeEvent(targetEvent)

            if eventNode is None:
                # sourceEventNode = Node({'type': 'modeEvent', 'value': targetEvent}, parent=parentNode)
                sourceEventNode = self.createNewNode('modeEvent', targetEvent, parentNode)
            else:
                sourceEventNode = eventNode
        else:
            raise Exception('Target event type is not supported!')

        for destinationApp in forwardEventResult:
            appEventId = destinationApp['applicationBotReceivedEvent'][0]

            if appEventId in self.coveredApplicationReceivedEvents:
                continue
            else:
                self.coveredApplicationReceivedEvents.append(appEventId)

            # appNode = \
            #     Node({'type': 'appEvent', 'value': destinationApp['applicationBotReceivedEvent']},
            #          parent=sourceEventNode)
            appNode = self.createNewNode('appEvent', destinationApp['applicationBotReceivedEvent'], sourceEventNode)
            for sentCommand in destinationApp['sentCommands']:
                # appCommandNode = Node({'type': 'appCommand', 'value': sentCommand}, appNode)
                appCommandNode = self.createNewNode('appCommand', sentCommand, appNode)

                if sentCommand is not None:
                    forwardApplicationCommandDic = self.forwardApplicationCommand(sentCommand)

                    if forwardApplicationCommandDic:
                        # commandEventNode = \
                        #     Node({'type': 'commandEvent', 'value': forwardApplicationCommandDic['commandEvent']},
                        #          parent=appCommandNode)
                        commandEventNode = \
                            self.createNewNode('commandEvent',
                                               forwardApplicationCommandDic['commandEvent'], appCommandNode)
                        if forwardApplicationCommandDic['resultedDeviceEvents']:
                            for newEvent in forwardApplicationCommandDic['resultedDeviceEvents']:
                                self.startEventForwardInvestigation(newEvent, commandEventNode)

            for sentModeCommand in destinationApp['sentModeCommands']:
                if sentModeCommand is not None:
                    forwardApplicationModeCommandModeEvent = \
                        self.forwardApplicationModeCommand(sentModeCommand,
                                                      destinationApp['applicationBotReceivedEvent'][31])

                    if forwardApplicationModeCommandModeEvent:
                        if forwardApplicationModeCommandModeEvent[0] in self.coveredModeEvents:
                            continue

                        # appModeCommandNode = Node({'type': 'appModeCommand', 'value': sentModeCommand}, appNode)
                        appModeCommandNode = self.createNewNode('appModeCommand', sentModeCommand, appNode)
                        # modeEventNode = \
                        #     Node({'type': 'modeEvent', 'value': forwardApplicationModeCommandModeEvent},
                        #          parent=appModeCommandNode)
                        modeEventNode = self.createNewNode('modeEvent',
                                                           forwardApplicationModeCommandModeEvent,
                                                           appModeCommandNode)
                        self.startEventForwardInvestigation(forwardApplicationModeCommandModeEvent, modeEventNode,
                                                       modeEventNode,
                                                       'modeEvent')

            for sentNotification in destinationApp['sentNotifications']:
                # Node({'type': 'appNotification', 'value': sentNotification}, appNode)
                self.createNewNode('appNotification', sentNotification, appNode)

        return sourceEventNode

    def groupDeviceEvents(self, targetDeviceEvent):
        # if not self.backwardInvestigation:
        #     return None

        eventId = targetDeviceEvent[1]
        deviceId = targetDeviceEvent[15]
        iotBotObject = None

        for iotBotRow in self.iotBotsList:
            iotBotId = iotBotRow.getBotId()

            if deviceId == iotBotId:
                iotBotObject = iotBotRow
                break

        if iotBotObject is None:
            return None

        return iotBotObject.groupDeviceEvent(eventId)

    def backwardModeEvent(self, targetModeEvent):
        if not self.backwardInvestigation:
            return None

        locationId = targetModeEvent[17]
        link = 'https://api.smartthings.com/locations/' + locationId + '/modes/current'
        modeName = targetModeEvent[11]
        modeId = None

        modeCommandList = []
        applicationModeCommands = database.executeQuery("SELECT * FROM apps_mode_commands_table "
                                                        "WHERE link = ? AND "
                                                        "json_extract(apps_mode_commands_table.body_res, '$.name') = ? "
                                                        "ORDER BY date_res", False,
                                                        (link, modeName,)).fetchall()

        for row in applicationModeCommands:
            if modeId is None:
                payload = json.loads(row[12])
                modeId = payload['modeId']

            date = datetime.strptime(row[14], '%a, %d %b %Y %H:%M:%S GMT')
            authToken = row[7][7:]
            appId = database.executeQuery("select * from APPs_received_events_table where authToken = ? LIMIT 1",
                                          False, (authToken,)).fetchone()[31]
            dic = {
                "id": row[0],
                "date": date.__str__(),
                "command": row,
                "installedAppId": appId,
                "source": "application"
            }
            modeCommandList.append(dic)

        if modeId is None:
            return None

        # Simulator mode commands check-up goes here
        if modeId:
            simulatorModeCommands = database.executeQuery(
                "SELECT * FROM simulator_mode_commands_table where id_ = ? and "
                "mode_id = ? ORDER BY date_res", False,
                (locationId, modeId,)).fetchall()
            for row in simulatorModeCommands:
                date = datetime.strptime(row[29], '%a, %d %b %Y %H:%M:%S GMT')
                dic = {
                    "id": row[0],
                    "date": date.__str__(),
                    "command": row,
                    "source": "simulator"
                }
                modeCommandList.append(dic)

        sortedList = sorted(modeCommandList, key=self.key_function)

        modeEvents = database.executeQuery(
            "select * from mode_events_table where value = ? and locationId = ? order by unixTime", False,
            (modeName, locationId,)).fetchall()

        targetModeEventIndex = None
        counter = 0
        for row in modeEvents:
            if row[0] == targetModeEvent[0]:
                targetModeEventIndex = counter
            counter += 1

        if targetModeEventIndex is not None:
            return sortedList[targetModeEventIndex]
        else:
            raise Exception("Target mode event was not found!")

    def backwardApplicationCommand(self, command):
        if not self.backwardInvestigation:
            return None

        appId = command['installedAppId']
        appBot = None

        for appBotRow in self.appBotsList:
            appBotId = appBotRow.getBotId()

            if appId == appBotId:
                appBot = appBotRow
                break

        if appBot is None:
            raise Exception("Target Application Bot doesn't exist!")

        return appBot.getSentCommandSourceEvent(command)

    def forwardDeviceEvent(self, targetDeviceEvent):
        if not self.forwardInvestigation and not self.backwardInvestigationComplete:
            return None

        deviceId = targetDeviceEvent[15]
        forwardDeviceEventList = []
        iotBotObject = None

        for iotBot in self.iotBotsList:
            if iotBot.getBotId() == deviceId:
                iotBotObject = iotBot

        if iotBotObject is None:
            return None

        event = {
            'event': targetDeviceEvent,
            'eventType': 'DEVICE_EVENT'
        }

        for appBot in self.appBotsList:
            receivedEvent = appBot.getApplicationReceivedEvent(event)

            if receivedEvent is not None:
                sentCommands = appBot.getApplicationSentCommands(receivedEvent)
                sentModeCommands = appBot.getApplicationSentModeCommands(receivedEvent)
                sentNotifications = appBot.getApplicationSentNotifications(receivedEvent)
                forwardDeviceEventDic = {
                    'applicationBotReceivedEvent': receivedEvent,
                    'sentCommands': sentCommands,
                    'sentModeCommands': sentModeCommands,
                    'sentNotifications': sentNotifications
                }
                forwardDeviceEventList.append(forwardDeviceEventDic)

        return forwardDeviceEventList

    def forwardModeEvent(self, targetModeEvent):
        if not self.forwardInvestigation and not self.backwardInvestigationComplete:
            return None

        forwardModeEventList = []
        event = {
            'event': targetModeEvent,
            'eventType': 'MODE_EVENT'
        }

        for appBot in self.appBotsList:
            receivedEvent = appBot.getApplicationReceivedEvent(event)

            if receivedEvent is not None:
                sentCommands = appBot.getApplicationSentCommands(receivedEvent)
                sentModeCommands = appBot.getApplicationSentModeCommands(receivedEvent)
                sentNotifications = appBot.getApplicationSentNotifications(receivedEvent)
                forwardDeviceEventDic = {
                    'applicationBotReceivedEvent': receivedEvent,
                    'sentCommands': sentCommands,
                    'sentModeCommands': sentModeCommands,
                    'sentNotifications': sentNotifications
                }
                forwardModeEventList.append(forwardDeviceEventDic)

        return forwardModeEventList

    def forwardApplicationCommand(self, appCommand):
        if not self.forwardInvestigation and not self.backwardInvestigationComplete:
            return None

        deviceId = appCommand[2][36:72]

        for iotBot in self.iotBotsList:
            if iotBot.getBotId() == deviceId:
                commandEvent = iotBot.getAppCommandDeviceCommandEvent(appCommand)

                if commandEvent is None:
                    return None

                resultedDeviceEvents = iotBot.getCommandEventRelevantDeviceEvents(commandEvent)
                return {
                    'commandEvent': commandEvent,
                    'resultedDeviceEvents': resultedDeviceEvents
                }

    def forwardApplicationModeCommand(self, appModeCommand, appId):
        if not self.forwardInvestigation and not self.backwardInvestigationComplete:
            return None

        for appBot in self.appBotsList:
            if appBot.getBotId() == appId:
                return appBot.getApplicationModeCommandModeEvent(appModeCommand, appId)

    def forwardApplicationReceivedEvent(self, appEvent, appBot):
        if not self.forwardInvestigation and not self.backwardInvestigationComplete:
            return None

        if appEvent is not None and appBot is not None:
            installedAppId = appEvent[31]

            if installedAppId != appBot.getBotId():
                raise Exception('This event was not received by this application!')

            sentCommands = appBot.getApplicationSentCommands(appEvent)
            sentModeCommands = appBot.getApplicationSentModeCommands(appEvent)
            sentNotifications = appBot.getApplicationSentNotifications(appEvent)
            forwardDeviceEventDic = {
                'applicationBotReceivedEvent': appEvent,
                'sentCommands': sentCommands,
                'sentModeCommands': sentModeCommands,
                'sentNotifications': sentNotifications
            }

            return forwardDeviceEventDic
        else:
            raise Exception("Application received event or Application Bot cannot be None!")

    def key_function(self, item_dictionary):
        return item_dictionary['date']

    def generateBots(self):
        self.iotBotsList.extend(botGenerator.generateIotBots())
        self.appBotsList.extend(botGenerator.generateApplicationBots())

    def createNewNode(self, nodeType, nodeValue, parentNode):
        nodeKey = nodeType + str(nodeValue[0])

        if nodeKey in self.nodeDic:
            node = self.nodeDic[nodeKey]
            if parentNode is not None:
                node.parent = parentNode
        else:
            node = Node({'type': nodeType, 'value': nodeValue}, parent=parentNode)
            self.nodeDic[nodeKey] = node

        return node


if __name__ == '__main__':
    questionerBot = QuestionerBot()
    questionerBot.generateBots()
