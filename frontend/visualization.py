import json
import os
import subprocess

import graphviz
import time
from anytree import Node, RenderTree


def graphVisualization(tree, startingNode, destinationFileAddress, view=True, now=int(time.time())):
    fileDir = destinationFileAddress + '/' + str(now) + '.gv'
    visualization = graphviz.Digraph(filename=fileDir)
    for pre, fill, parent in RenderTree(tree.root):
        children = parent.children

        for child in children:
            parentNode = str(parent.name['value'][0])
            childNode = str(child.name['value'][0])
            visualization.node(parentNode, label=getNodeContent(parent.name),
                               style='filled', fillcolor=getNodeColor(parent.name, startingNode))
            visualization.node(childNode, label=getNodeContent(child.name),
                               style='filled', fillcolor=getNodeColor(child.name, startingNode))
            visualization.edge(parentNode, childNode, label=getEdgeLabel(parent.name, child.name), dir='back')

    visualization.render()
    if view:
        visualization.view()


def getEdgeLabel(parentNode, childNode):
    parentNodeType = parentNode['type']
    childNodeType = childNode['type']

    if parentNodeType == 'commandEvent' and childNodeType == 'deviceEvent':
        return ' rooted in'
    elif parentNodeType == 'appCommand' and childNodeType == 'commandEvent':
        return ' created by'
    elif parentNodeType == 'simulatorCommand' and childNodeType == 'commandEvent':
        return ' created by'
    elif parentNodeType == 'appEvent' and childNodeType == 'appCommand':
        return ' caused by'
    elif parentNodeType == 'deviceEvent' and childNodeType == 'appEvent':
        return ' subscribed to'
    elif parentNodeType == 'modeEvent' and childNodeType == 'appEvent':
        return ' subscribed to'
    elif parentNodeType == 'simulatorModeCommand' and childNodeType == 'modeEvent':
        return ' associated with'
    elif parentNodeType == 'appModeCommand' and childNodeType == 'modeEvent':
        return ' caused by'
    elif parentNodeType == 'appEvent' and childNodeType == 'appModeCommand':
        return ' associated with'
    elif parentNodeType == 'appEvent' and childNodeType == 'appNotification':
        return ' created by'
    elif parentNodeType == 'deviceEvent' and childNodeType == 'deviceEvent':
        return ' happened before'
    elif parentNodeType == 'deviceAccess' and childNodeType == 'appPermissions':
        return ' Accessed'
    elif parentNodeType == 'appPermissions' and childNodeType == 'permissions':
        return ' Rooted'
    else:
        return 'unknown'


def getNodeColor(node, startingNode):
    nodeType = node['type']
    nodeValue = node['value']

    if len(nodeValue) > 1:
        if nodeValue[1] == startingNode:
            return '#ff000042'

    return 'white'


def getNodeContent(node, seperator='\\n'):
    nodeType = node['type']
    nodeValue = node['value']

    if nodeType == 'simulatorCommand':
        simulatorCommand = nodeValue[22]
        deviceId = nodeValue[21]
        date = nodeValue[28]
        return 'Simulator Command: ' + simulatorCommand + seperator + 'Device ID: ' + deviceId + seperator + 'Date: ' + date
    elif nodeType == 'commandEvent':
        eventId = nodeValue[1]
        description = nodeValue[4]
        date = nodeValue[9]
        command = nodeValue[11]
        deviceId = nodeValue[15]
        locationId = nodeValue[17]
        eventSource = nodeValue[18]

        return 'Event Source: ' + eventSource + seperator + 'Event ID: ' + eventId + seperator + 'Description: ' + description + \
               seperator + 'Command: ' + command + seperator + 'DeviceID: ' + deviceId + seperator + 'Location ID: ' + \
               locationId + seperator + 'Date: ' + date
    elif nodeType == 'appCommand':
        appCommand = nodeValue[12]
        deviceId = nodeValue[2][36:72]
        date = nodeValue[14]
        component = nodeValue[10]
        capability = nodeValue[11]
        arguments = nodeValue[13]
        sessionOrder = str(nodeValue[25])
        return 'Application Command: ' + appCommand + seperator + 'Device ID: ' + \
               deviceId + seperator + 'Component: ' + component + seperator + 'Capability: ' + capability + \
               seperator + 'Arguments: ' + arguments + seperator + 'Session ID: ' + sessionOrder + seperator +\
               'Date: ' + date
    elif nodeType == 'appNotification':
        title = nodeValue[12]
        message = nodeValue[11]
        notifType = nodeValue[13]
        locationId = nodeValue[10]
        date = nodeValue[15]
        return 'Application Notification: ' + title + seperator + 'Message: ' + \
               message + seperator + 'Type: ' + notifType + seperator + 'Location ID: ' + locationId + \
               seperator + 'Date: ' + date
    elif nodeType == 'appModeCommand':
        requestPayload = json.loads(nodeValue[12])
        responsePayload = json.loads(nodeValue[25])
        appModeCommand = 'location mode'
        locationId = nodeValue[2][38:74]
        modeId = requestPayload["modeId"]
        modeName = responsePayload["name"]
        date = nodeValue[14]
        return 'Application Command: ' + appModeCommand + seperator + 'Location ID: ' + locationId + seperator + \
               'Mode ID: ' + modeId + seperator + 'Mode Name: ' + modeName + seperator + 'Date: ' + date
    elif nodeType == 'deviceEvent':
        eventId = nodeValue[1]
        description = nodeValue[4]
        date = nodeValue[9]
        name = nodeValue[16]
        value = nodeValue[11]
        deviceId = nodeValue[15]
        locationId = nodeValue[17]
        eventSource = nodeValue[18]
        deviceTypeId = nodeValue[19]
        return 'Event Source: ' + eventSource + seperator + 'Event ID: ' + eventId + seperator + 'Description: ' + \
               description + seperator + 'Attribute: ' + name + seperator + 'Value: ' + value + seperator + 'Device ID: ' + deviceId + \
               seperator + 'DTH ID: ' + deviceTypeId + seperator + 'Location ID: ' + locationId + seperator + 'Date: ' + date
    elif nodeType == 'appEvent':
        installedAppId = nodeValue[31]
        locationId = nodeValue[32]
        date = nodeValue[44]
        eventType = nodeValue[45]
        eventId = nodeValue[46]
        deviceId = nodeValue[50]
        component = nodeValue[51]
        capability = nodeValue[52]
        attribute = nodeValue[53]
        value = nodeValue[54]
        subscriptionName = nodeValue[57]

        if eventType == 'DEVICE_EVENT':
            return 'Event Source: App Subscription' + seperator + 'Installed App ID: ' + installedAppId + \
                   seperator + 'Event ID: ' + eventId + seperator + 'Device ID: ' + deviceId + seperator + 'Location ID: ' + locationId + \
                   seperator + 'Component: ' + component + seperator + 'Capability: ' + capability + seperator + 'Attribute: ' + attribute + \
                   seperator + 'Value: ' + value + seperator + 'Subscription Name: ' + subscriptionName + seperator + 'Date: ' + date
        elif eventType == 'MODE_EVENT':
            modeId = nodeValue[48]
            return 'Event Source: App Subscription' + seperator + 'Installed App ID: ' + installedAppId + \
                   seperator + 'Event ID: ' + eventId + seperator + 'Location ID: ' + locationId + seperator + 'Mode ID: ' + modeId +\
                   seperator + 'Subscription Name: ' + subscriptionName + seperator + 'Date: ' + date
        else:
            raise Exception('Event type is not defined!')
    elif nodeType == 'modeEvent':
        eventId = nodeValue[1]
        description = nodeValue[4]
        name = nodeValue[16]
        value = nodeValue[11]
        date = nodeValue[9]
        locationId = nodeValue[17]
        eventSource = nodeValue[18]

        return 'Event Source: ' + eventSource + seperator + 'Event ID: ' + \
               eventId + seperator + 'Location ID: ' + locationId + \
               seperator + 'Description: ' + description + seperator + 'Attribute: ' + \
               name + seperator + 'Value: ' + value + seperator + 'Date: ' + date
    elif nodeType == "simulatorModeCommand":
        modeId = nodeValue[24]
        locationId = nodeValue[19]
        date = nodeValue[29]
        return 'Simulator Command: change mode' + seperator + 'Mode ID: ' + modeId + seperator + \
               'Location ID: ' + locationId + seperator + 'Date: ' + date
    elif nodeType == "deviceAccess":
        deviceId = nodeValue[0]
        deviceNames = nodeValue[1]
        return 'IoT Device' + seperator + 'Device ID: ' + deviceId + seperator + 'Device Names: ' + deviceNames
    elif nodeType == "appPermissions":
        installedAppId = nodeValue[0]
        return 'Smart Application' + seperator + 'Installed App ID: ' + installedAppId
    elif nodeType == "permissions":
        permissionsDic = nodeValue[1]
        lifecycle = permissionsDic['lifecycle']
        locationId = permissionsDic['locationId']
        date = permissionsDic['date']
        permissions = permissionsDic['permissions']
        return 'Permissions' + seperator + 'Lifecycle: ' + lifecycle + seperator + 'Location ID: ' + \
               locationId + seperator + 'Date: ' + date + seperator + 'Permissions: ' + str(permissions)
    else:
        return str(nodeValue[0])


def saveTxtFormat(tree, startingNode, destinationFileAddress, view=True, now=int(time.time())):
    fileDir = destinationFileAddress + '/' + str(now) + '.txt'
    txtContent = "Investigation Results for Event ID: " + startingNode
    for pre, fill, node in RenderTree(tree.root):
        txtContent += str("\n%s%s" % (pre, getNodeContent(node.name, ', ')))

    with open(fileDir, "x", encoding="utf-8") as f:
        f.write(txtContent)

    if view:
        subprocess.Popen([fileDir], shell=True)
