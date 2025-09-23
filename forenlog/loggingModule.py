import ast
import glob
import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile

sys.path.append('..')
from database import database

DEBUG = False
URL = None
Authorization = None
host = None
component = None
capability = None
command = None
arguments = None
cmd = None
c = ""

url_regex = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
acceptableRange = range(3000, 4001)  # Range of acceptable port number

if DEBUG:
    tempFolder_logs = "ExtractedLogs/"
else:
    tempFolder_logs = tempfile.gettempdir() + "/ExtractedLogs/"


# Changing the extension of .saz to .zip
def rename(logFile, extension):
    name = os.path.splitext(logFile)[0]
    os.rename(logFile, name + extension)

    return True


# Extractin the .zip file
def extract_logs(logFile):
    global tempFolder_logs

    # Clear previous extracted logs
    print("test " + tempFolder_logs)
    if os.path.exists(tempFolder_logs):
        for filename in os.listdir(tempFolder_logs):
            file_path = os.path.join(tempFolder_logs, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    time_ = str(time.time())
    destinationFolder = tempFolder_logs + "/" + time_

    with zipfile.ZipFile(logFile, 'r') as zip_ref:
        # Extracting
        zip_ref.extractall(destinationFolder)

    return destinationFolder


def logsProcessing(LogFileDir):
    for file in os.listdir(LogFileDir):
        print(file)
        if file.endswith(".saz"):
            sazFileDir = LogFileDir + '/' + file

            # Change the extension to .zip
            print("Renaming: .zip   ", end="")
            rename(sazFileDir, ".zip")
            print("Done")

            zipFile = file.split(".saz")[0] + ".zip"
            zipFileDir = LogFileDir + '/' + zipFile

            # Extracting
            print("Extracting...", end="")
            destinationFolder = extract_logs(zipFileDir)
            print("Done")

            # Change the extension back to .saz
            print("Renaming: .saz   ", end="")
            rename(zipFileDir, ".saz")
            print("Done")

            return True


# Gathering files using a pattern
def gather_files_pattern(pattern):
    '''
    :param pattern: pattern to find a file (*.txt)
    :return: list of files
    '''
    files_ = []

    org_dir = os.getcwd()
    os.chdir(os.getcwd() + "/contents/raw/")

    for file in glob.glob(pattern):
        files_.append(file)

    os.chdir(org_dir)

    return files_


def application_commands(file, logtxtFiles):
    '''
    :param file: text file to find application commands
    :return: True/False list of files
    '''
    print("Start processing: " + file)

    # Start processing the file which is related to application commands
    x = file[-9:]
    if x == '007_c.txt':
        g = 7
    with open(file) as logs_host_api:
        for line_host_api in logs_host_api:
            line_host_api = line_host_api.split("\n")[0]

            # Getting the needed information from each line
            if ("POST" in line_host_api):
                method, URL = (line_host_api.split(" HTTP/1.1")[0]).split(" ")
            else:
                if ("Accept: " in line_host_api):
                    accept = line_host_api.split("Accept: ")[1]
                else:
                    if ("Content-Type: " in line_host_api):
                        contentType = line_host_api.split("Content-Type: ")[1]
                    else:
                        if ("Accept-Language: " in line_host_api):
                            acceptLanguage = line_host_api.split("Accept-Language: ")[1]
                        else:
                            if ("Authorization" in line_host_api):
                                Authorization = line_host_api.split("Authorization: ")[1]
                            else:
                                if ("User-Agent: " in line_host_api):
                                    userAgent = line_host_api.split("User-Agent: ")[1]
                                else:
                                    if ("Content-Length: " in line_host_api):
                                        contentLength = line_host_api.split("Content-Length: ")[1]
                                    else:
                                        if ("host" in line_host_api):
                                            host = line_host_api.split("host: ")[1]
                                        else:
                                            if ("commands" in line_host_api):
                                                cmd = ast.literal_eval(line_host_api)
                                                if 'component' in cmd["commands"][0]:
                                                    component = cmd["commands"][0]['component']
                                                else:
                                                    component = None
                                                capability = cmd["commands"][0]['capability']
                                                command = cmd["commands"][0]['command']
                                                if 'arguments' in cmd["commands"][0]:
                                                    arguments = cmd["commands"][0]['arguments']
                                                    arguments = json.dumps(arguments)
                                                else:
                                                    arguments = None

    # Getting the responses
    request_file = file.split("/")[-1]
    response_file = request_file.replace("c", "s")

    # Pop the response file from the list
    logtxtFiles.remove(response_file)

    response_file_dir = file.replace("_c.txt", "_s.txt")
    commandResponse = application_commands_response(response_file_dir)

    if commandResponse is False:
        return False

    date, content_type, content_length, connection, server, x_rate_limit, x_rate_limit_remain, x_rate_limit_reset, access_allow_methods, access_allow_headers, payload = commandResponse

    # Checking for any duplication
    conditionDic = {
        'payload': payload,
        'date': date,
        'Authorization': Authorization
    }
    duplication_check = database.duplication_check("APPs_commands_table", conditionDic)

    if duplication_check:
        print("Duplicated row")
        return False

    # Database related operations
    print("Table: APPs_commands_table")
    rowNumber = int(file[file.rindex('/') + 1:file.rindex('_')])
    query = """INSERT INTO APPs_commands_table (method, URL, accept, contentType, acceptLanguage, Authorization, userAgent, contentLength, host, component, capability, command, arguments, date, content_type, content_length, connection, server, x_rate_limit, x_rate_limit_remain, x_rate_limit_reset, access_allow_methods, access_allow_headers, payload, rowNumber)
            VALUES('{0}','{1}','{2}','{3}','{4}','{5}','{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}', '{21}', '{22}', '{23}', '{24}')""".format(
        method, URL, accept, contentType, acceptLanguage,
        Authorization, userAgent, contentLength, host,
        component, capability, command, arguments, date, content_type, content_length, connection, server, x_rate_limit,
        x_rate_limit_remain, x_rate_limit_reset, access_allow_methods, access_allow_headers, payload, rowNumber)
    ret_app_commands = database.executeQuery(query, True, None)

    if (ret_app_commands):
        return True
    else:
        return False


# Application Response
def application_commands_response(file):
    with open(file) as responses:
        for line in responses:
            # Filtering
            line = line.split("\n")[0]

            if ("HTTP/1.1" in line):
                response_method, response_URL, response_val = line.split(" ")

                if response_URL == '403':
                    return False
            else:
                if ("Date" in line):
                    date = line.split("Date: ")[1]
                else:
                    if ("Content-Type: " in line):
                        content_type = line.split("Content-Type: ")[1]
                    else:
                        if ("Content-Length: " in line):
                            content_length = line.split("Content-Length: ")[1]
                        else:
                            if ("Connection: " in line):
                                connection = line.split("Connection: ")[1]
                            else:
                                if ("Server: " in line):
                                    server = line.split("Server: ")[1]
                                else:
                                    if ("X-RateLimit-Limit: " in line):
                                        x_rate_limit = line.split("X-RateLimit-Limit: ")[1]
                                    else:
                                        if ("X-RateLimit-Remaining: " in line):
                                            x_rate_limit_remain = line.split("X-RateLimit-Remaining: ")[1]
                                        else:
                                            if ("X-RateLimit-Reset: " in line):
                                                x_rate_limit_reset = line.split("X-RateLimit-Reset: ")[1]
                                            else:
                                                if ("Access-Control-Allow-Methods: " in line):
                                                    access_allow_methods = line.split("Access-Control-Allow-Methods: ")[
                                                        1]
                                                else:
                                                    if ("Access-Control-Allow-Headers: " in line):
                                                        access_allow_headers = \
                                                            line.split("Access-Control-Allow-Headers: ")[1]
                                                    else:
                                                        payload = line

    try:
        g = content_type
    except:
        print("sdsd")

    return (
        date, content_type, content_length, connection, server, x_rate_limit, x_rate_limit_remain, x_rate_limit_reset,
        access_allow_methods, access_allow_headers, payload)


def application_received_events(request, response):
    '''
    :param request, response: The request and response
    :return: True/False of the database insert operation
    '''
    print("Start processing: " + request)

    # Request processing
    with open(request) as logs_local_host:
        for line_local_host in logs_local_host:

            line_local_host = line_local_host.split("\n")[0]

            if ('"lifecycle":"UPDATE"' in line_local_host):
                return None

            if ("HTTP/1.1" in line_local_host):
                method, URL = (line_local_host.split(" HTTP/1.1")[0]).split(" ")
            else:
                if ("Host" in line_local_host):
                    host = line_local_host.split("Host: ")[1]
                else:
                    if ("User-Agent" in line_local_host):
                        user_agent = line_local_host.split("User-Agent: ")[1]
                    else:
                        if ("Content-Length" in line_local_host):
                            content_length = line_local_host.split("Content-Length: ")[1]
                        else:
                            if ("Accept: " in line_local_host):
                                accept = line_local_host.split("Accept: ")[-1]
                            else:
                                if ("Accept-Encoding: " in line_local_host):
                                    accept_encoding = line_local_host.split("Accept-Encoding: ")[1]
                                else:
                                    if ("Authorization" in line_local_host):
                                        authorization = line_local_host.split("Authorization: ")[1]
                                    else:
                                        if ("Cdn-Loop: " in line_local_host):
                                            cdnLoop = line_local_host.split("Cdn-Loop: ")[1]
                                        else:
                                            if ("Cf-Connecting-Ip: " in line_local_host):
                                                cf_connection_ip = line_local_host.split("Cf-Connecting-Ip: ")[1]
                                            else:
                                                if ("Cf-Ipcountry: " in line_local_host):
                                                    cfIpcountry = line_local_host.split("Cf-Ipcountry: ")[1]
                                                else:
                                                    if ("Cf-Ray: " in line_local_host):
                                                        cfRay = line_local_host.split("Cf-Ray: ")[1]
                                                    else:
                                                        if ("Cf-Visitor: " in line_local_host):
                                                            cfVisitor = line_local_host.split("Cf-Visitor: ")[1]
                                                        else:
                                                            if ("Cf-Warp-Tag-Id" in line_local_host):
                                                                cf_wrap_tag_id = \
                                                                    line_local_host.split("Cf-Warp-Tag-Id: ")[1]
                                                            else:
                                                                if ("Content-Type" in line_local_host):
                                                                    conentType = \
                                                                        line_local_host.split("Content-Type: ")[1]
                                                                else:
                                                                    if ("Date" in line_local_host):
                                                                        date = line_local_host.split("Date: ")[1]
                                                                    else:
                                                                        if ("Digest" in line_local_host):
                                                                            digest = line_local_host.split("Digest: ")[
                                                                                1]
                                                                        else:
                                                                            if ("X-B3-Parentspanid" in line_local_host):
                                                                                parentspanid = line_local_host.split(
                                                                                    "X-B3-Parentspanid: ")[1]
                                                                            else:
                                                                                if ("X-B3-Sampled" in line_local_host):
                                                                                    sampled = line_local_host.split(
                                                                                        "X-B3-Sampled: ")[1]
                                                                                else:
                                                                                    if (
                                                                                            "X-B3-Spanid" in line_local_host):
                                                                                        spanid = line_local_host.split(
                                                                                            "X-B3-Spanid: ")[1]
                                                                                    else:
                                                                                        if (
                                                                                                "X-B3-Traceid" in line_local_host):
                                                                                            traceid = \
                                                                                                line_local_host.split(
                                                                                                    "X-B3-Traceid: ")[1]
                                                                                        else:
                                                                                            if (
                                                                                                    "X-Forwarded-For" in line_local_host):
                                                                                                forwarded_for = \
                                                                                                    line_local_host.split(
                                                                                                        "X-Forwarded-For: ")[
                                                                                                        1]
                                                                                            else:
                                                                                                if (
                                                                                                        "X-Forwarded-Proto" in line_local_host):
                                                                                                    forwarded_proto = \
                                                                                                        line_local_host.split(
                                                                                                            "X-Forwarded-Proto: ")[
                                                                                                            1]
                                                                                                else:
                                                                                                    if (
                                                                                                            "X-St-Correlation" in line_local_host):
                                                                                                        correlation = \
                                                                                                            line_local_host.split(
                                                                                                                "X-St-Correlation: ")[
                                                                                                                1]
                                                                                                    else:
                                                                                                        if (
                                                                                                                "eventId" in line_local_host):
                                                                                                            payload_raw = line_local_host
                                                                                                            payload = json.loads(
                                                                                                                line_local_host)

                                                                                                            lifecycle = \
                                                                                                                payload[
                                                                                                                    'lifecycle']
                                                                                                            executionId = \
                                                                                                                payload[
                                                                                                                    'executionId']
                                                                                                            locale = \
                                                                                                                payload[
                                                                                                                    'locale']
                                                                                                            version = \
                                                                                                                payload[
                                                                                                                    'version']
                                                                                                            authToken = \
                                                                                                                payload[
                                                                                                                    'eventData'][
                                                                                                                    'authToken']
                                                                                                            installedAppId = \
                                                                                                                payload[
                                                                                                                    'eventData'][
                                                                                                                    'installedApp'][
                                                                                                                    'installedAppId']
                                                                                                            locationId = \
                                                                                                                payload[
                                                                                                                    'eventData'][
                                                                                                                    'installedApp'][
                                                                                                                    'locationId']

                                                                                                            try:
                                                                                                                lightsValueType = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'lights'][
                                                                                                                        0][
                                                                                                                        'valueType'])
                                                                                                                lightsDeviceId1 = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'lights'][
                                                                                                                        0][
                                                                                                                        'deviceConfig'][
                                                                                                                        'deviceId'])
                                                                                                                lightsComponentId1 = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'lights'][
                                                                                                                        0][
                                                                                                                        'deviceConfig'][
                                                                                                                        'componentId'])
                                                                                                                lightsDeviceId2 = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'lights'][
                                                                                                                        0][
                                                                                                                        'deviceConfig'][
                                                                                                                        'deviceId'])
                                                                                                                lightsComponentId2 = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'lights'][
                                                                                                                        0][
                                                                                                                        'deviceConfig'][
                                                                                                                        'componentId'])
                                                                                                            except:
                                                                                                                lightsValueType = ""
                                                                                                                lightsDeviceId1 = ""
                                                                                                                lightsComponentId1 = ""
                                                                                                                lightsDeviceId2 = ""
                                                                                                                lightsComponentId2 = ""

                                                                                                            try:
                                                                                                                switchValueType = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'switch'][
                                                                                                                        0][
                                                                                                                        'valueType'])
                                                                                                                switchDeviceId = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'switch'][
                                                                                                                        0][
                                                                                                                        'deviceConfig'][
                                                                                                                        'deviceId'])
                                                                                                                switchComponentId = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'switch'][
                                                                                                                        0][
                                                                                                                        'deviceConfig'][
                                                                                                                        'componentId'])
                                                                                                                deviceConfigDeviceID = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'switch'][
                                                                                                                        0][
                                                                                                                        'deviceConfig'][
                                                                                                                        'deviceId'])
                                                                                                                deviceConfigComponentID = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'installedApp'][
                                                                                                                        'config'][
                                                                                                                        'switch'][
                                                                                                                        0][
                                                                                                                        'deviceConfig'][
                                                                                                                        'componentId'])

                                                                                                            except:
                                                                                                                switchValueType = ""
                                                                                                                switchDeviceId = ""
                                                                                                                switchComponentId = ""
                                                                                                                deviceConfigDeviceID = ""
                                                                                                                deviceConfigComponentID = ""

                                                                                                            permissions = (
                                                                                                                payload[
                                                                                                                    'eventData'][
                                                                                                                    'installedApp'][
                                                                                                                    'permissions'])

                                                                                                            eventTime = (
                                                                                                                payload[
                                                                                                                    'eventData'][
                                                                                                                    'events'][
                                                                                                                    0][
                                                                                                                    'eventTime'])
                                                                                                            eventType = (
                                                                                                                payload[
                                                                                                                    'eventData'][
                                                                                                                    'events'][
                                                                                                                    0][
                                                                                                                    'eventType'])
                                                                                                            eventId = ""
                                                                                                            DeviceEventLocationId = ""
                                                                                                            ownerId = ""
                                                                                                            ownerType = ""
                                                                                                            deviceEventDeviceID = ""
                                                                                                            deviceEventComponentID = ""
                                                                                                            capability = ""
                                                                                                            attribute = ""
                                                                                                            deviceEventValue = ""
                                                                                                            deviceEventValueType = ""
                                                                                                            stateChange = ""
                                                                                                            subscriptionName = ""

                                                                                                            if (
                                                                                                                    eventType == 'deviceEvent' or eventType == 'DEVICE_EVENT'):
                                                                                                                eventId = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'eventId'])
                                                                                                                DeviceEventLocationId = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'locationId'])
                                                                                                                ownerId = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'ownerId'])
                                                                                                                ownerType = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'ownerType'])
                                                                                                                deviceEventDeviceID = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'deviceId'])
                                                                                                                deviceEventComponentID = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'componentId'])
                                                                                                                capability = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'capability'])
                                                                                                                attribute = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'attribute'])
                                                                                                                deviceEventValue = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'value'])
                                                                                                                deviceEventValueType = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'valueType'])
                                                                                                                stateChange = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'stateChange'])
                                                                                                                subscriptionName = (
                                                                                                                    payload[
                                                                                                                        'eventData'][
                                                                                                                        'events'][
                                                                                                                        0][
                                                                                                                        'deviceEvent'][
                                                                                                                        'subscriptionName'])
                                                                                                            else:
                                                                                                                if (
                                                                                                                        eventType == 'modeEvent' or eventType == 'MODE_EVENT'):
                                                                                                                    eventId = \
                                                                                                                        payload[
                                                                                                                            "eventData"][
                                                                                                                            "events"][
                                                                                                                            0][
                                                                                                                            "modeEvent"][
                                                                                                                            "eventId"]
                                                                                                                    DeviceEventLocationId = (
                                                                                                                        payload[
                                                                                                                            'eventData'][
                                                                                                                            'events'][
                                                                                                                            0][
                                                                                                                            'modeEvent'][
                                                                                                                            'locationId'])
                                                                                                                    ownerId = (
                                                                                                                        payload[
                                                                                                                            'eventData'][
                                                                                                                            'events'][
                                                                                                                            0][
                                                                                                                            'modeEvent'][
                                                                                                                            'modeId'])
                                                                                                                    ownerType = ""
                                                                                                                    deviceEventDeviceID = ""
                                                                                                                    deviceEventComponentID = ""
                                                                                                                    capability = ""
                                                                                                                    attribute = ""
                                                                                                                    deviceEventValue = ""
                                                                                                                    deviceEventValueType = ""
                                                                                                                    stateChange = ""
                                                                                                                    subscriptionName = ""

                                                                                                            #### Getting responses
                                                                                                            response_method, response_URL, response_val, response_x_powered_by, response_content_type, response_content_length, response_etag, response_date, response_connection, response_keep_alive, response_payload = application_response(
                                                                                                                response)
                                                                                                            print(
                                                                                                                response_etag)
                                                                                                            rowNumber = int(
                                                                                                                request[
                                                                                                                request.rindex(
                                                                                                                    '/') + 1:request.rindex(
                                                                                                                    '_')])

                                                                                                            # Checking for any duplication
                                                                                                            conditionDic = {
                                                                                                                'traceid': traceid,
                                                                                                                'eventTime': eventTime,
                                                                                                                'eventId': eventId,
                                                                                                                'authToken': authToken,
                                                                                                                'authorization': authorization
                                                                                                            }
                                                                                                            duplication_check = database.duplication_check(
                                                                                                                "APPs_received_events_table",
                                                                                                                conditionDic)

                                                                                                            if duplication_check:
                                                                                                                print(
                                                                                                                    "Duplicated row")
                                                                                                                return False

                                                                                                            # Database related operations
                                                                                                            print(
                                                                                                                "Table: APPs_received_events_table")
                                                                                                            query = """INSERT INTO APPs_received_events_table (method, URL, host, user_agent, content_length, accept, accept_encoding, authorization,cdnLoop, cf_connection_ip, cfIpcountry, cfRay, cfVisitor, cf_wrap_tag_id, conentType, date, digest, parentspanid, sampled, spanid, traceid, forwarded_for, forwarded_proto, correlation, payload, lifecycle, executionId, locale, version, authToken, installedAppId, locationId, lightsValueType, lightsDeviceId1, lightsComponentId1, lightsDeviceId2, lightsComponentId2, switchValueType, switchDeviceId, switchComponentId, deviceConfigDeviceID, deviceConfigComponentID, permissions, eventTime, eventType, eventId, DeviceEventLocationId, ownerId, ownerType, deviceEventDeviceID, deviceEventComponentID, capability, attribute, deviceEventValue, deviceEventValueType, stateChange, subscriptionName, response_method, response_URL, response_val, response_x_powered_by, response_content_type, response_content_length, response_etag, response_date, response_connection, response_keep_alive, response_payload, rowNumber)VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}', '{21}', '{22}', '{23}', '{24}', '{25}', '{26}', '{27}', '{28}', '{29}', '{30}', '{31}', '{32}', '{33}', '{34}', '{35}', '{36}', '{37}', '{38}', '{39}', '{40}', '{41}', '{42}', '{43}', '{44}', '{45}', '{46}', '{47}', '{48}', '{49}', '{50}', '{51}', '{52}', '{53}', '{54}', '{55}','{56}', '{57}',  '{58}', '{59}', '{60}', '{61}', '{62}', '{63}', '{64}', '{65}', '{66}', '{67}', '{68}')""".format(
                                                                                                                method,
                                                                                                                URL,
                                                                                                                host,
                                                                                                                user_agent,
                                                                                                                content_length,
                                                                                                                accept,
                                                                                                                accept_encoding,
                                                                                                                authorization,
                                                                                                                cdnLoop,
                                                                                                                cf_connection_ip,
                                                                                                                cfIpcountry,
                                                                                                                cfRay,
                                                                                                                cfVisitor,
                                                                                                                cf_wrap_tag_id,
                                                                                                                conentType,
                                                                                                                date,
                                                                                                                digest,
                                                                                                                parentspanid,
                                                                                                                sampled,
                                                                                                                spanid,
                                                                                                                traceid,
                                                                                                                forwarded_for,
                                                                                                                forwarded_proto,
                                                                                                                correlation,
                                                                                                                payload_raw,
                                                                                                                lifecycle,
                                                                                                                executionId,
                                                                                                                locale,
                                                                                                                version,
                                                                                                                authToken,
                                                                                                                installedAppId,
                                                                                                                locationId,
                                                                                                                lightsValueType,
                                                                                                                lightsDeviceId1,
                                                                                                                lightsComponentId1,
                                                                                                                lightsDeviceId2,
                                                                                                                lightsComponentId2,
                                                                                                                switchValueType,
                                                                                                                switchDeviceId,
                                                                                                                switchComponentId,
                                                                                                                deviceConfigDeviceID,
                                                                                                                deviceConfigComponentID,
                                                                                                                ",".join(
                                                                                                                    permissions),
                                                                                                                eventTime,
                                                                                                                eventType,
                                                                                                                eventId,
                                                                                                                DeviceEventLocationId,
                                                                                                                ownerId,
                                                                                                                ownerType,
                                                                                                                deviceEventDeviceID,
                                                                                                                deviceEventComponentID,
                                                                                                                capability,
                                                                                                                attribute,
                                                                                                                deviceEventValue,
                                                                                                                deviceEventValueType,
                                                                                                                stateChange,
                                                                                                                subscriptionName,
                                                                                                                response_method,
                                                                                                                response_URL,
                                                                                                                response_val,
                                                                                                                response_x_powered_by,
                                                                                                                response_content_type,
                                                                                                                response_content_length,
                                                                                                                response_etag,
                                                                                                                response_date,
                                                                                                                response_connection,
                                                                                                                response_keep_alive,
                                                                                                                response_payload,
                                                                                                                rowNumber)

                                                                                                            ret_app_rec_events = database.executeQuery(
                                                                                                                query,
                                                                                                                True,
                                                                                                                None)

                                                                                                            if (
                                                                                                                    ret_app_rec_events):
                                                                                                                return True
                                                                                                            else:
                                                                                                                return False


# Application Responses
def application_response(response_file):
    '''
    :param response_file: response file
    :return: True/False if inserted into the database
    '''
    counter = 1
    with open(response_file, "r") as reponses:
        for line in reponses:
            # Filtering
            line = line.split("\n")[0]
            print(line)

            if ("HTTP/1.1" in line):
                response_method, response_URL, response_val = line.split(" ")
            else:
                if ("X-Powered-By" in line):
                    response_x_powered_by = line.split("X-Powered-By: ")[1]
                else:
                    if ("Content-Type: " in line):
                        response_content_type = line.split("Content-Type: ")[1]
                    else:
                        if ("Content-Length: " in line):
                            response_content_length = line.split("Content-Length: ")[1]
                        else:
                            if ("ETag: " in line):
                                response_etag = line.split("ETag: ")[1]
                            else:
                                if ("Date: " in line):
                                    response_date = line.split("Date: ")[1]
                                else:
                                    if ("Connection: " in line):
                                        response_connection = line.split("Connection: ")[1]
                                    else:
                                        if ("Keep-Alive: " in line):
                                            response_keep_alive = line.split("Keep-Alive: ")[1]
                                        else:
                                            response_payload = line

                                            return response_method, response_URL, response_val, response_x_powered_by, response_content_type, response_content_length, response_etag, response_date, response_connection, response_keep_alive, response_payload


def webSocket(file):
    '''
    :param file: text file to find application received events
    :return: True/False list of files
    '''
    with open(file, "rb") as logs_webSocket:
        for line in logs_webSocket:

            if ('"event":{"' in str(line)):

                event_in_line = str(line).split("event")

                if (len(event_in_line) > 1):
                    temp_line = None
                    line = str(line)
                    line = line[line.find('{"event":'):]
                    firstsBracket = line.find("{")
                    lastBracket = line.rfind("}")
                    line = line[firstsBracket:lastBracket+1]

                    if ("\\" in line):
                        line = line.replace("\\", "")
                    if ('"{"' in line):
                        line = line.replace('"{"', '{"')
                    if ('}"' in line):
                        line = line.replace('}"', '}')

                    try:
                        json_ = json.loads(line)
                    except:
                        print("jsdsd")

                    if (json_["event"]):
                        event_id = json_["event"]["id"]
                        hubId = json_["event"]["hubId"]
                        isVirtualHub = json_["event"]["isVirtualHub"]

                        if json_["event"]["description"] is not None:
                            description = (json_["event"]["description"]).replace("'",
                                                                                  " ")  # if quotes found in string
                        else:
                            description = ''
                        rawDescription = json_["event"]["rawDescription"]
                        displayed = json_["event"]["displayed"]
                        isStateChange = json_["event"]["isStateChange"]
                        linkText = json_["event"]["linkText"]
                        date = json_["event"]["date"]
                        unixTime = json_["event"]["unixTime"]
                        value = (str(json_["event"]["value"])).replace("'", '"')
                        viewed = json_["event"]["viewed"]
                        translatable = json_["event"]["translatable"]
                        archivable = json_["event"]["archivable"]
                        locationId = json_["event"]["locationId"]
                        eventSource = json_["event"]["eventSource"]

                        try:
                            eventType = json_["event"]["eventType"]
                        except:
                            eventType = None

                        name = None
                        try:
                            name = json_["event"]["name"]
                        except:
                            pass

                        data = None
                        try:
                            data = json.loads(json_["event"]["data"])
                        except:
                            pass

                        deviceTypeId = None
                        try:
                            deviceTypeId = json_["event"]["deviceTypeId"]
                        except:
                            pass

                        deviceId = None
                        try:
                            deviceId = json_["event"]["deviceId"]
                        except:
                            pass

                        # Inserting into the database
                        if (eventSource == "COMMAND"):
                            # Checking for any duplication
                            conditionDic = {
                                'event_id': event_id,
                                'unixTime': unixTime
                            }
                            duplication_check = database.duplication_check(
                                "device_commands_events_table",
                                conditionDic)

                            if duplication_check:
                                print("Duplicated row")
                                return False

                            print("Table: device_commands_events_table")
                            rowNumber = int(file[file.rindex('/') + 1:file.rindex('_')])
                            query = """INSERT INTO device_commands_events_table (event_id, hubId, isVirtualHub, description, rawDescription, displayed,
                                   isStateChange, linkText, date, unixTime, value, viewed, translatable, archivable, deviceId, name, locationId, eventSource,
                                   deviceTypeId, data, rowNumber)VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}',
                                   '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}')""".format(
                                event_id,
                                hubId,
                                isVirtualHub,
                                description,
                                rawDescription,
                                displayed,
                                isStateChange,
                                linkText,
                                date,
                                unixTime,
                                value,
                                viewed,
                                translatable,
                                archivable,
                                deviceId,
                                name,
                                locationId,
                                eventSource,
                                deviceTypeId,
                                data, rowNumber)
                            ret_command_events = database.executeQuery(query, True, None)

                            if (not ret_command_events):
                                return False
                            continue

                        else:
                            if eventSource == "LOCATION" and eventType == "LOCATION_MODE_CHANGE":
                                # Checking for any duplication
                                conditionDic = {
                                    'event_id': event_id,
                                    'unixTime': unixTime
                                }
                                duplication_check = database.duplication_check(
                                    "mode_events_table",
                                    conditionDic)

                                if duplication_check:
                                    print("Duplicated row")
                                    return False

                                print("Table: mode_events_table")
                                rowNumber = int(file[file.rindex('/') + 1:file.rindex('_')])
                                query = """INSERT INTO mode_events_table (event_id, hubId, isVirtualHub, description, rawDescription, displayed,
                                       isStateChange, linkText, date, unixTime, value, viewed, translatable, archivable, deviceId, name, locationId, eventSource,
                                       deviceTypeId, data, rowNumber)VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}',
                                       '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', {20})""".format(
                                    event_id, hubId, isVirtualHub, description,
                                    rawDescription, displayed, isStateChange, linkText,
                                    date, unixTime, value, viewed, translatable, archivable,
                                    deviceId, name, locationId, eventSource, deviceTypeId,
                                    data, rowNumber)
                                ret_mode_events = database.executeQuery(query, True, None)

                                if (not ret_mode_events):
                                    return False

                                continue

                            else:
                                # Inserting into: device_events_table
                                if (eventSource == "DEVICE"):
                                    # Checking for any duplication
                                    conditionDic = {
                                        'event_id': event_id,
                                        'unixTime': unixTime
                                    }
                                    duplication_check = database.duplication_check(
                                        "device_events_table",
                                        conditionDic)

                                    if (duplication_check):
                                        print("Duplicated row")
                                        return False

                                    print("Table: device_events_table")
                                    rowNumber = int(file[file.rindex('/') + 1:file.rindex('_')])
                                    query = """INSERT INTO device_events_table (event_id, hubId, isVirtualHub, description, rawDescription, displayed,
                                           isStateChange, linkText, date, unixTime, value, viewed, translatable, archivable, deviceId, name, locationId, eventSource,
                                           deviceTypeId, data, rowNumber)VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}',
                                           '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}')""".format(
                                        event_id, hubId, isVirtualHub, description,
                                        rawDescription, displayed, isStateChange, linkText,
                                        date, unixTime, value, viewed, translatable, archivable,
                                        deviceId, name, locationId, eventSource, deviceTypeId,
                                        data, rowNumber)

                                    try:
                                        ret_device_events = database.executeQuery(query, True, None)
                                    except:
                                        ret_device_events = database.executeQuery(query, True, None)

                                    if (not ret_device_events):
                                        return False
                                    continue
                                # else:
                                #     query = """INSERT INTO other_events_table (event_id, hubId, isVirtualHub, description, rawDescription, displayed,
                                #        isStateChange, linkText, date, unixTime, value, viewed, translatable, archivable, deviceId, name, locationId, eventSource,
                                #        deviceTypeId, data)VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}',
                                #        '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}')""".format(event_id, hubId, isVirtualHub, description,
                                #                                                                                  rawDescription, displayed, isStateChange, linkText,
                                #                                                                                  date, unixTime, value, viewed, translatable, archivable,
                                #                                                                                  deviceId, name, locationId, eventSource, deviceTypeId,
                                #                                                                                  data)
                                # ret_other_events = database.executeQuery(query, True, None)
                                #
                                # if(not ret_other_events):
                                #     return False

    return True


def simulatorCommands_c(file, logtxtFiles):
    with open(file, "rb") as simulator:
        for line in simulator:

            line = line.decode().split("\n")[0]

            if ("POST" in line):
                method, URL, HTTP_ver = line.split(" ")
            else:
                if ("Host: " in line):
                    host = line.split("Host: ")[1]
                else:
                    if ("User-Agent" in line):
                        user_agent = line.split("User-Agent: ")[1]
                    else:
                        if ("Content-Length" in line):
                            content_length = line.split("Content-Length: ")[1]
                        else:
                            if ("Content-Type" in line):
                                content_type = line.split("Content-Type: ")[1]
                            else:
                                if ("Accept: " in line):
                                    accept = line.split("Accept: ")[-1]
                                else:
                                    if ("Accept-Encoding: " in line):
                                        accept_encoding = line.split("Accept-Encoding: ")[1]
                                    else:
                                        if ("X-CSRF-TOKEN: " in line):
                                            x_csrf_token = line.split("X-CSRF-TOKEN: ")[1]
                                        else:
                                            if ("X-ST-Client: " in line):
                                                x_st_client = line.split("X-ST-Client: ")[1]
                                            else:
                                                if ("X-Requested-With: " in line):
                                                    x_req_with = line.split("X-Requested-With: ")[1]
                                                else:
                                                    if ("Origin: " in line):
                                                        origin = line.split("Origin: ")[1]
                                                    else:
                                                        if ("Connection: " in line):
                                                            connection = line.split("Connection: ")[1]
                                                        else:
                                                            if ("Referer: " in line):
                                                                referer = line.split("Referer: ")[1]
                                                            else:
                                                                if ("Sec-Fetch-Dest: " in line):
                                                                    secFetchDest = line.split("Sec-Fetch-Dest: ")[1]
                                                                else:
                                                                    if ("Sec-Fetch-Mode: " in line):
                                                                        secFetchMode = line.split("Sec-Fetch-Mode: ")[1]
                                                                    else:
                                                                        if ("Sec-Fetch-Site: " in line):
                                                                            secFetchSite = \
                                                                                line.split("Sec-Fetch-Site: ")[1]
                                                                        else:
                                                                            if ("&_csrf" in line):
                                                                                csrf_line = line.split("&")
                                                                                id_ = csrf_line[0].split("id=")[-1]
                                                                                command = \
                                                                                csrf_line[1].split("command=")[-1]
                                                                                csrf = csrf_line[2].split("csrf=")[-1]

    # Getting the responses
    request_file = file.split("/")[-1]
    response_file = request_file.replace("c", "s")

    # Pop the response file from the list
    logtxtFiles.remove(response_file)

    response_file_dir = file.replace("_c.txt", "_s.txt")
    simulatorCommandResponse = simulatorCommands_s(response_file_dir)

    if simulatorCommandResponse is False:
        return False

    HTTP_ver_res, res_num_res, res_res, content_type_res, date_res, server_res, x_frame_options_res, transfer_encoding_res, connection_res = simulatorCommandResponse

    # Checking for any duplication
    conditionDic = {
        'id_': id_,
        'command': command,
        'date_res': date_res
    }
    duplication_check = database.duplication_check(
        "simulator_table",
        conditionDic)

    if (duplication_check):
        print("Duplicated row")
        return False

    # Inserting into the database
    print("Table: simulator_table")
    rowNumber = int(file[file.rindex('/') + 1:file.rindex('_')])
    query = """INSERT INTO simulator_table (method, URL, HTTP_ver, host, user_agent, content_length, content_type,
                accept,accept_encoding, x_csrf_token, x_st_client, x_req_with, origin, connection, referer ,secFetchDest ,secFetchMode
                ,secFetchSite ,id_ ,command ,csrf, HTTP_ver_res, res_num_res, res_res, content_type_res, date_res, server_res, x_frame_options_res, transfer_encoding_res, connection_res, rowNumber)VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}',
                '{11}', '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}', '{21}', '{22}', '{23}', '{24}', '{25}', '{26}', '{27}', '{28}', '{29}', '{30}')""".format(
        method, URL, HTTP_ver, host,
        user_agent, content_length, content_type,
        accept, accept_encoding, x_csrf_token,
        x_st_client, x_req_with, origin, connection,
        referer, secFetchDest, secFetchMode,
        secFetchSite, id_, command, csrf, HTTP_ver_res, res_num_res, res_res, content_type_res, date_res, server_res,
        x_frame_options_res, transfer_encoding_res, connection_res, rowNumber)
    ret_simulator = database.executeQuery(query, True, None)

    if (not ret_simulator):
        return False

    return True


def simulatorCommands_s(file):
    HTTP_ver = ""
    res_num = ""
    res = ""
    content_type = ""
    date = ""
    server = ""
    x_frame_options = ""
    transfer_encoding = ""
    connection = ""
    with open(file, "rb") as simulator:
        for line in simulator:

            line = line.decode().split("\n")[0]

            if ("HTTP/1.1" in line):
                HTTP_ver, res_num, res = line.split(" ")

                if res_num != '200':
                    return False
            else:
                if ("Content-Type: " in line):
                    content_type = line.split("Content-Type: ")[1]
                else:
                    if ("Date" in line):
                        date = line.split("Date: ")[1]
                        date = date.replace('\r', '')
                    else:
                        if ("Server" in line):
                            server = line.split("Server: ")[1]
                        else:
                            if ("X-Frame-Options" in line):
                                x_frame_options = line.split("X-Frame-Options: ")[1]
                            else:
                                if ("transfer-encoding: " in line):
                                    transfer_encoding = line.split("transfer-encoding: ")[-1]
                                else:
                                    if ("Connection: " in line):
                                        connection = line.split("Connection: ")[1]

    return (HTTP_ver, res_num, res, content_type, date, server, x_frame_options, transfer_encoding, connection)


def notification_request(file, logtxtFiles):
    '''
    :param file: text file to find notification request
    :return: True/False list of files
    '''
    print("Start processing: " + file)

    # Start processing the file which is related to application commands
    with open(file) as notif_req:
        for line_req in notif_req:
            line_req = line_req.split("\n")[0]

            # Getting the needed information from each line
            if ("POST" in line_req):
                post_req = line_req
            else:
                if ("Accept: " in line_req):
                    accept_req = line_req.split("Accept: ")[1]
                else:
                    if ("Content-Type: " in line_req):
                        content_req = line_req.split("Content-Type: ")[1]
                    else:
                        if ("Accept-Language: " in line_req):
                            accept_language_req = line_req.split("Accept-Language: ")[1]
                        else:
                            if ("Authorization" in line_req):
                                authorization_req = line_req.split("Authorization: ")[1]
                            else:
                                if ("User-Agent: " in line_req):
                                    user_agent_req = line_req.split("User-Agent: ")[1]
                                else:
                                    if ("Content-Length: " in line_req):
                                        content_length_req = line_req.split("Content-Length: ")[1]
                                    else:
                                        if ("host" in line_req):
                                            host_req = line_req.split("host: ")[1]
                                        else:
                                            if ("Connection: " in line_req):
                                                connection_req = line_req.split("Connection: ")[1]
                                            else:
                                                if ("messages" in line_req):
                                                    cmd = ast.literal_eval(line_req)

                                                    locationId_req = cmd['locationId']
                                                    type_req = cmd['type']
                                                    title_req = cmd["messages"][0]['default']['title']
                                                    body_req = json.dumps(cmd["messages"][0]['default']['body'])

    # Getting the response file
    request_file = file.split("/")[-1]
    response_file = request_file.replace("c", "s")

    # Pop the response file from the list
    logtxtFiles.remove(response_file)

    response_file_dir = file.replace("_c.txt", "_s.txt")

    # Getting the response
    notificationResponse = notification_response(response_file_dir)

    if notificationResponse is False:
        return notificationResponse

    HTTP_res, date_res, content_type_res, content_length_res, connection_res, server_res, x_rateLimit_limit_res, x_rateLimit_remaining_res, x_rateLimit_reset_res, access_control_allow_origin_res, access_control_allow_methods_res, access_control_allow_headers_res, body_res = notificationResponse

    # Checking for any duplication
    conditionDic = {
        'authorization_req': authorization_req,
        'date_res': date_res,
        'body_req': body_req
    }
    duplication_check = database.duplication_check(
        "notifications",
        conditionDic)

    if (duplication_check):
        print("Duplicated row")
        return False

    # Database related operations
    print("Table: notification")
    rowNumber = int(file[file.rindex('/') + 1:file.rindex('_')])
    query = """INSERT INTO notifications (post_req, accept_req, content_req, accept_language_req, authorization_req, user_agent_req, content_length_req, host_req, connection_req, locationId_req, body_req, title_req, type_req, HTTP_res, date_res, content_type_res, content_length_res, connection_res, server_res, x_rateLimit_limit_res, x_rateLimit_remaining_res, x_rateLimit_reset_res, access_control_allow_origin_res, access_control_allow_methods_res, access_control_allow_headers_res, body_res, rowNumber) VALUES('{0}','{1}','{2}','{3}','{4}','{5}','{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}', '{21}', '{22}', '{23}', '{24}', '{25}', '{26}')""".format(
        post_req, accept_req, content_req, accept_language_req, authorization_req, user_agent_req, content_length_req,
        host_req, connection_req, locationId_req, body_req, title_req, type_req, HTTP_res, date_res, content_type_res,
        content_length_res, connection_res, server_res, x_rateLimit_limit_res, x_rateLimit_remaining_res,
        x_rateLimit_reset_res, access_control_allow_origin_res, access_control_allow_methods_res,
        access_control_allow_headers_res, body_res, rowNumber)

    ret_notification = database.executeQuery(query, True, None)

    if (ret_notification):
        return True

    return False


def notification_response(file):
    with open(file) as responses:
        for line in responses:
            # Filtering
            line = line.split("\n")[0]

            if ("HTTP/1.1" in line):
                HTTP_res = line.split("\n")[0]

                if HTTP_res != 'HTTP/1.1 200':
                    return False
            else:
                if ("Date" in line):
                    date_res = line.split("Date: ")[1]
                else:
                    if ("Content-Type: " in line):
                        content_type_res = line.split("Content-Type: ")[1]
                    else:
                        if ("Content-Length: " in line):
                            content_length_res = line.split("Content-Length: ")[1]
                        else:
                            if ("Connection: " in line):
                                connection_res = line.split("Connection: ")[1]
                            else:
                                if ("Server: " in line):
                                    server_res = line.split("Server: ")[1]
                                else:
                                    if ("X-RateLimit-Limit: " in line):
                                        x_rateLimit_limit_res = line.split("X-RateLimit-Limit: ")[1]
                                    else:
                                        if ("X-RateLimit-Remaining: " in line):
                                            x_rateLimit_remaining_res = line.split("X-RateLimit-Remaining: ")[1]
                                        else:
                                            if ("X-RateLimit-Reset: " in line):
                                                x_rateLimit_reset_res = line.split("X-RateLimit-Reset: ")[1]
                                            else:
                                                if ("Access-Control-Allow-Origin: " in line):
                                                    access_control_allow_origin_res = \
                                                        line.split("Access-Control-Allow-Origin: ")[1]
                                                else:
                                                    if ("Access-Control-Allow-Methods: " in line):
                                                        access_control_allow_methods_res = \
                                                            line.split("Access-Control-Allow-Methods: ")[1]
                                                    else:
                                                        if ("Access-Control-Allow-Headers: " in line):
                                                            access_control_allow_headers_res = \
                                                                line.split("Access-Control-Allow-Headers: ")[1]
                                                        else:
                                                            body_res = json.dumps(line)

    return (HTTP_res, date_res, content_type_res, content_length_res, connection_res, server_res,
            x_rateLimit_limit_res, x_rateLimit_remaining_res, x_rateLimit_reset_res,
            access_control_allow_origin_res, access_control_allow_methods_res,
            access_control_allow_headers_res, body_res)


# Request: Application set mode
def application_install_update_requests(request, response):
    '''
    :param file: text file to find request
    :return: True/False list of files
    '''
    print("Start processing: " + request)

    client = None
    updateData = '{}'
    installData = '{}'

    # Start processing the file which is related to application commands
    with open(request) as app_req:
        for line_req in app_req:
            line_req = line_req.split("\n")[0]

            # Getting the needed information from each line
            if ("POST" in line_req):
                post_req = line_req
            else:
                if ("Host: " in line_req):
                    host_req = line_req.split("Host: ")[1]
                else:
                    if ("User-Agent: " in line_req):
                        user_agent_req = line_req.split("User-Agent: ")[1]
                    else:
                        if ("Content-Length: " in line_req):
                            content_length_req = line_req.split("Content-Length: ")[1]
                        else:
                            if ("Accept:" in line_req):
                                accept_req = line_req.split("Accept: ")[1]
                            else:
                                if ("Accept-Encoding: " in line_req):
                                    accept_encoding_req = line_req.split("Accept-Encoding: ")[1]
                                else:
                                    if ("Authorization: " in line_req):
                                        authorization_req = line_req.split("Authorization: ")[1]
                                    else:
                                        if ("Cdn-Loop: " in line_req):
                                            cdn_loop_req = line_req.split("Cdn-Loop: ")[1]
                                        else:
                                            if ("Cf-Connecting-Ip" in line_req):
                                                cf_connection_ip_req = line_req.split("Cf-Connecting-Ip: ")[1]
                                            else:
                                                if ("Cf-Ipcountry: " in line_req):
                                                    cf_IPcountry_req = line_req.split("Cf-Ipcountry: ")[1]
                                                else:
                                                    if ("Cf-Ray" in line_req):
                                                        cf_ray_req = line_req.split("Cf-Ray: ")[1]
                                                    else:
                                                        if ("Cf-Visitor: " in line_req):
                                                            cf_visitor_req = line_req.split("Cf-Visitor: ")[1]
                                                        else:
                                                            if ("Cf-Warp-Tag-Id" in line_req):
                                                                cf_wrap_tag_id_req = line_req.split("Cf-Warp-Tag-Id: ")[
                                                                    1]
                                                            else:
                                                                if ("Connection: " in line_req):
                                                                    connection_req = line_req.split("Connection: ")[1]
                                                                else:
                                                                    if ("Content-Type" in line_req):
                                                                        content_type_req = \
                                                                        line_req.split("Content-Type: ")[1]
                                                                    else:
                                                                        if ("Date: " in line_req):
                                                                            date_req = line_req.split("Date: ")[1]
                                                                        else:
                                                                            if ("Digest" in line_req):
                                                                                digest_req = line_req.split("Digest: ")[
                                                                                    1]
                                                                            else:
                                                                                if ("X-B3-Parentspanid: " in line_req):
                                                                                    x_b3_Parentspanid_req = \
                                                                                    line_req.split(
                                                                                        "X-B3-Parentspanid: ")[1]
                                                                                else:
                                                                                    if ("X-B3-Sampled" in line_req):
                                                                                        x_b3_sampled_req = \
                                                                                        line_req.split(
                                                                                            "X-B3-Sampled: ")[1]
                                                                                    else:
                                                                                        if (
                                                                                                "X-B3-Spanid: " in line_req):
                                                                                            x_3_spanid_req = \
                                                                                            line_req.split(
                                                                                                "X-B3-Spanid: ")[1]
                                                                                        else:
                                                                                            if (
                                                                                                    "X-B3-Traceid" in line_req):
                                                                                                x_b3_traceid_req = \
                                                                                                line_req.split(
                                                                                                    "X-B3-Traceid: ")[1]
                                                                                            else:
                                                                                                if (
                                                                                                        "X-Forwarded-For: " in line_req):
                                                                                                    x_forwarded_for_req = \
                                                                                                    line_req.split(
                                                                                                        "X-Forwarded-For: ")[
                                                                                                        1]
                                                                                                else:
                                                                                                    if (
                                                                                                            "X-Forwarded-Proto" in line_req):
                                                                                                        x_forwarded_for_proto = \
                                                                                                        line_req.split(
                                                                                                            "X-Forwarded-Proto: ")[
                                                                                                            1]
                                                                                                    else:
                                                                                                        if (
                                                                                                                "X-St-Correlation: " in line_req):
                                                                                                            x_st_correlation_req = \
                                                                                                            line_req.split(
                                                                                                                "X-St-Correlation: ")[
                                                                                                                1]
                                                                                                        else:
                                                                                                            if (
                                                                                                                    len(line_req) > 20):
                                                                                                                jsonify = json.loads(
                                                                                                                    line_req)

                                                                                                                lifecycle = (
                                                                                                                    str(json.dumps(
                                                                                                                        jsonify[
                                                                                                                            "lifecycle"]))).replace(
                                                                                                                    '"',
                                                                                                                    '')
                                                                                                                executionId = (
                                                                                                                    str(json.dumps(
                                                                                                                        jsonify[
                                                                                                                            "executionId"]))).replace(
                                                                                                                    '"',
                                                                                                                    '')
                                                                                                                appId = (
                                                                                                                    str(json.dumps(
                                                                                                                        jsonify[
                                                                                                                            "appId"]))).replace(
                                                                                                                    '"',
                                                                                                                    '')
                                                                                                                locale = (
                                                                                                                    str(json.dumps(
                                                                                                                        jsonify[
                                                                                                                            "locale"]))).replace(
                                                                                                                    '"',
                                                                                                                    '')
                                                                                                                version = (
                                                                                                                    str(json.dumps(
                                                                                                                        jsonify[
                                                                                                                            "version"]))).replace(
                                                                                                                    '"',
                                                                                                                    '')

                                                                                                                if (
                                                                                                                        "client" in line_req):
                                                                                                                    client = str(
                                                                                                                        json.dumps(
                                                                                                                            jsonify[
                                                                                                                                "client"]))

                                                                                                                if (
                                                                                                                        "updateData" in line_req):
                                                                                                                    updateData = str(
                                                                                                                        json.dumps(
                                                                                                                            jsonify[
                                                                                                                                "updateData"]))

                                                                                                                if (
                                                                                                                        "installData" in line_req):
                                                                                                                    installData = str(
                                                                                                                        json.dumps(
                                                                                                                            jsonify[
                                                                                                                                "installData"]))

    # Getting the response
    modeCommandResponse = application_install_update_response(response)

    if modeCommandResponse is False:
        return False

    http_details_res, x_powered_by_res, content_type_res, content_length_res, etag_res, date_res, connection_res, keep_alive_res, response_body_res = modeCommandResponse

    # TODO: Duplication check

    # Database related operations
    print("Table: apps_install_update_table")

    rowNumber = int(request[request.rindex('/') + 1:request.rindex('_')])
    query = """INSERT INTO apps_install_update_table (lifecycle, executionId, appId, locale, version, client, updateData, installData, post_req, host_req, user_agent_req, content_length_req, accept_req, accept_encoding_req, authorization_req, cdn_loop_req, cf_connection_ip_req, cf_IPcountry_req, cf_ray_req, cf_visitor_req, cf_wrap_tag_id_req, connection_req, content_type_req, date_req, digest_req, x_b3_Parentspanid_req, x_b3_sampled_req, x_3_spanid_req, x_b3_traceid_req, x_forwarded_for_req, x_forwarded_for_proto, x_st_correlation_req, http_details_res, x_powered_by_res, content_type_res, content_length_res, etag_res, date_res, connection_res, keep_alive_res, response_body_res, rowNumber) VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}', '{21}', '{22}', '{23}', '{24}', '{25}', '{26}', '{27}', '{28}', '{29}', '{30}', '{31}', '{32}', '{33}', '{34}', '{35}', '{36}', '{37}', '{38}', '{39}', '{40}', '{41}')""".format(
        lifecycle, executionId, appId, locale, version, client, updateData, installData, post_req, host_req,
        user_agent_req, content_length_req, accept_req, accept_encoding_req, authorization_req, cdn_loop_req,
        cf_connection_ip_req, cf_IPcountry_req, cf_ray_req, cf_visitor_req, cf_wrap_tag_id_req, connection_req,
        content_type_req, date_req, digest_req, x_b3_Parentspanid_req, x_b3_sampled_req, x_3_spanid_req,
        x_b3_traceid_req, x_forwarded_for_req, x_forwarded_for_proto, x_st_correlation_req, http_details_res,
        x_powered_by_res, content_type_res, content_length_res, etag_res, date_res, connection_res, keep_alive_res,
        response_body_res, rowNumber)

    ret = database.executeQuery(query, True, None)

    if (ret):
        return True

    return False


# Response: Application set mode
def application_install_update_response(response):
    with open(response) as app_res:

        http_details = x_powered_by = content_type = content_length = etag = date_ = connection = keep_alive = response_body = None

        for line in app_res:
            line = line.split("\n")[0]

            if ("HTTP/1.1" in line):
                HTTP_res = line.split("\n")[0]

                if HTTP_res != 'HTTP/1.1 200 OK':
                    return False

            # Getting the needed information from each line
            if ("POST" in line):
                http_details = line
            else:
                if ("X-Powered-By: " in line):
                    x_powered_by = line.split("X-Powered-By: ")[1]
                else:
                    if ("Content-Type: " in line):
                        content_type = line.split("Content-Type: ")[1]
                    else:
                        if ("Content-Length: " in line):
                            content_length = line.split("Content-Length: ")[1]
                        else:
                            if ("ETag:" in line):
                                etag = line.split("ETag: ")[1]
                            else:
                                if ("Date:" in line):
                                    date_ = line.split("Date: ")[1]
                                else:
                                    if ("Connection:" in line):
                                        connection = line.split("Connection: ")[1]
                                    else:
                                        if ("Keep-Alive:" in line):
                                            keep_alive = line.split("Keep-Alive: ")[1]
                                        else:
                                            response_body = line

    return (
    http_details, x_powered_by, content_type, content_length, etag, date_, connection, keep_alive, response_body)


# Request: Application last inistallation phase
def application_app_mode_commands_request(request, response, logtxtFiles):
    '''
    :param file: text file to find request
    :return: True/False list of files
    '''
    method = link = http = accept_req = content_type_req = accept_language_req = authorization_req = user_agent_req = content_length_req = host_req = connection_req = payload = None

    # Start processing the file which is related to application commands
    with open(response) as app_req:
        for line_req in app_req:
            line_req = line_req.split("\n")[0]

            # Getting the needed information from each line
            if ("PUT" in line_req):
                try:
                    method, link, http = line_req.split(" ")
                except:
                    pass
            else:
                if ("Accept: " in line_req):
                    accept_req = line_req.split("Accept: ")[1]
                else:
                    if ("Content-Type: " in line_req):
                        content_type_req = line_req.split("Content-Type: ")[1]
                    else:
                        if ("Accept-Language: " in line_req):
                            accept_language_req = line_req.split("Accept-Language: ")[1]
                        else:
                            if ("Authorization:" in line_req):
                                authorization_req = line_req.split("Authorization: ")[1]
                            else:
                                if ("User-Agent: " in line_req):
                                    user_agent_req = line_req.split("User-Agent: ")[1]
                                else:
                                    if ("Content-Length: " in line_req):
                                        content_length_req = line_req.split("Content-Length: ")[1]
                                    else:
                                        if ("host: " in line_req):
                                            host_req = line_req.split("host: ")[1]
                                        else:
                                            if ("Connection: " in line_req):
                                                connection_req = line_req.split("Connection: ")[1]
                                            else:
                                                payload = line_req

    # Getting the response
    installationResponse = application_mode_commands_response(request)

    if installationResponse is False:
        return False

    HTTP_res, date_res, content_type_res, content_length_res, connection_res, server_res, x_rateLimit_limit_res, x_rateLimit_remaining_res, x_rateLimit_reset_res, access_control_allow_origin_res, access_control_allow_methods_res, access_control_allow_headers_res, body_res = installationResponse

    # Removing the response from the list
    request_fileName = request.split("/")[-1]
    logtxtFiles.remove(request_fileName)

    # TODO: Duplication check

    # Database related operations
    print("Table: apps_mode_commands_table")

    rowNumber = int(request[request.rindex('/') + 1:request.rindex('_')])
    query = """INSERT INTO apps_mode_commands_table (method, link, http, accept_req, content_type_req, accept_language_req, authorization_req, user_agent_req, content_length_req, host_req, connection_req, payload, HTTP_res, date_res, content_type_res, content_length_res, connection_res, server_res, x_rateLimit_limit_res, x_rateLimit_remaining_res, x_rateLimit_reset_res, access_control_allow_origin_res, access_control_allow_methods_res, access_control_allow_headers_res, body_res, rowNumber) VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}', '{21}', '{22}', '{23}', '{24}', '{25}')""".format(
        method, link, http, accept_req, content_type_req, accept_language_req, authorization_req, user_agent_req,
        content_length_req, host_req, connection_req, payload, HTTP_res, date_res, content_type_res, content_length_res,
        connection_res, server_res, x_rateLimit_limit_res, x_rateLimit_remaining_res, x_rateLimit_reset_res,
        access_control_allow_origin_res, access_control_allow_methods_res, access_control_allow_headers_res, body_res,
        rowNumber)

    ret = database.executeQuery(query, True, None)

    if (ret):
        return True
    else:
        return False


# Response: Application last inistallation phase
def application_mode_commands_response(response):
    '''
    :param file: text file to find request
    :return: True/False list of files
    '''
    HTTP_res = date_res = content_type_res = content_length_res = connection_res = server_res = x_rateLimit_limit_res = x_rateLimit_remaining_res = x_rateLimit_reset_res = access_control_allow_origin_res = access_control_allow_methods_res = access_control_allow_headers_res = body_res = None

    with open(response) as responses:
        for line in responses:
            # Filtering
            line = line.split("\n")[0]

            if ("HTTP/1.1" in line):
                HTTP_res = line.split("\n")[0]

                if HTTP_res != 'HTTP/1.1 200 OK':
                    return False
            else:
                if ("Date" in line):
                    date_res = line.split("Date: ")[1]
                else:
                    if ("Content-Type: " in line):
                        content_type_res = line.split("Content-Type: ")[1]
                    else:
                        if ("Content-Length: " in line):
                            content_length_res = line.split("Content-Length: ")[1]
                        else:
                            if ("Connection: " in line):
                                connection_res = line.split("Connection: ")[1]
                            else:
                                if ("Server: " in line):
                                    server_res = line.split("Server: ")[1]
                                else:
                                    if ("X-RateLimit-Limit: " in line):
                                        x_rateLimit_limit_res = line.split("X-RateLimit-Limit: ")[1]
                                    else:
                                        if ("X-RateLimit-Remaining: " in line):
                                            x_rateLimit_remaining_res = line.split("X-RateLimit-Remaining: ")[1]
                                        else:
                                            if ("X-RateLimit-Reset: " in line):
                                                x_rateLimit_reset_res = line.split("X-RateLimit-Reset: ")[1]
                                            else:
                                                if ("Access-Control-Allow-Origin: " in line):
                                                    access_control_allow_origin_res = \
                                                    line.split("Access-Control-Allow-Origin: ")[1]
                                                else:
                                                    if ("Access-Control-Allow-Methods: " in line):
                                                        access_control_allow_methods_res = \
                                                        line.split("Access-Control-Allow-Methods: ")[1]
                                                    else:
                                                        if ("Access-Control-Allow-Headers: " in line):
                                                            access_control_allow_headers_res = \
                                                            line.split("Access-Control-Allow-Headers: ")[1]
                                                        else:
                                                            body_res = line

    return (HTTP_res, date_res, content_type_res, content_length_res, connection_res, server_res, x_rateLimit_limit_res,
            x_rateLimit_remaining_res, x_rateLimit_reset_res, access_control_allow_origin_res,
            access_control_allow_methods_res, access_control_allow_headers_res, body_res)


# simulator_mode_commands
def simulator_mode_commands_request(request, response, logtxtFiles):
    '''
    :param file: text file to find request
    :return: True/False list of files
    '''
    print("Start processing: " + request)

    post_req = host_req = user_agent_req = content_length_req = content_type_req = accept_req = accept_language_req = accept_encoding_req = origin_req = connection_req = referer_req = cookie_req = upgrade_insecure_requests_req = sec_fetch_dest_req = sec_fetch_mode_req = sec_fetch_site_req = sec_fetch_user_req = csrf = id_ = version = name = ocfDefaultLocation = accountId = mode_id = temperatureScale = locale = action_update = None

    # Start processing the file which is related to application commands
    with open(request) as app_req:
        for line_req in app_req:
            line_req = line_req.split("\n")[0]

            # Getting the needed information from each line
            if ("POST" in line_req):
                post_req = line_req
            else:
                if ("Host: " in line_req):
                    host_req = line_req.split("Host: ")[1]
                else:
                    if ("User-Agent: " in line_req):
                        user_agent_req = line_req.split("User-Agent: ")[1]
                    else:
                        if ("Content-Length: " in line_req):
                            content_length_req = line_req.split("Content-Length: ")[1]
                        else:
                            if ("Content-Type: " in line_req):
                                content_type_req = line_req.split("Content-Type: ")[1]
                            else:
                                if ("Accept:" in line_req):
                                    accept_req = line_req.split("Accept: ")[1]
                                else:
                                    if ("Accept-Language: " in line_req):
                                        accept_language_req = line_req.split("Accept-Language: ")[1]
                                    else:
                                        if ("Accept-Encoding: " in line_req):
                                            accept_encoding_req = line_req.split("Accept-Encoding: ")[1]
                                        else:
                                            if ("Origin: " in line_req):
                                                origin_req = line_req.split("Origin: ")[1]
                                            else:
                                                if ("Connection: " in line_req):
                                                    connection_req = line_req.split("Connection: ")[1]
                                                else:
                                                    if ("Referer" in line_req):
                                                        referer_req = line_req.split("Referer: ")[1]
                                                    else:
                                                        if ("Cookie: " in line_req):
                                                            cookie_req = line_req.split("Cookie: ")[1]
                                                        else:
                                                            if ("Upgrade-Insecure-Requests" in line_req):
                                                                upgrade_insecure_requests_req = \
                                                                line_req.split("Upgrade-Insecure-Requests: ")[1]
                                                            else:
                                                                if ("Sec-Fetch-Dest: " in line_req):
                                                                    sec_fetch_dest_req = \
                                                                    line_req.split("Sec-Fetch-Dest: ")[1]
                                                                else:
                                                                    if ("Sec-Fetch-Mode" in line_req):
                                                                        sec_fetch_mode_req = \
                                                                        line_req.split("Sec-Fetch-Mode: ")[1]
                                                                    else:
                                                                        if ("Sec-Fetch-Site: " in line_req):
                                                                            sec_fetch_site_req = \
                                                                            line_req.split("Sec-Fetch-Site: ")[1]
                                                                        else:
                                                                            if ("Sec-Fetch-User: " in line_req):
                                                                                sec_fetch_user_req = \
                                                                                line_req.split("Sec-Fetch-User: ")[1]
                                                                            else:
                                                                                if ("_csrf=" in line_req):
                                                                                    items = line_req.split("&")
                                                                                    csrf = items[0].split("_csrf=")[1]
                                                                                    id_ = items[1].split("id=")[1]
                                                                                    version = \
                                                                                    items[2].split("version=")[1]
                                                                                    name = items[3].split("name=")[1]
                                                                                    ocfDefaultLocation = items[4].split(
                                                                                        "ocfDefaultLocation=")[1]
                                                                                    accountId = \
                                                                                    items[5].split("accountId=")[1]
                                                                                    mode_id = \
                                                                                    items[6].split("mode.id=")[1]
                                                                                    temperatureScale = \
                                                                                    items[7].split("temperatureScale=")[
                                                                                        1]
                                                                                    locale = items[8].split("locale=")[
                                                                                        1]
                                                                                    action_update = \
                                                                                    items[9].split("_action_update=")[1]

    # Getting the response
    simulatorModeCommandResponse = simulator_mode_commands_response(response)

    if simulatorModeCommandResponse is False:
        return False

    HTTP_res, date_res, content_type_res, content_length_res, server_res, x_frame_option_res, connection_res = simulatorModeCommandResponse

    # Removing the response from the list
    request_fileName = request.split("/")[-1]
    logtxtFiles.remove(request_fileName)

    # TODO: Duplication check

    # Database related operations
    print("Table: simulator_mode_commands_table")

    query = """INSERT INTO simulator_mode_commands_table (post_req, host_req, user_agent_req, content_length_req, content_type_req, accept_req, accept_language_req, accept_encoding_req, origin_req, connection_req, referer_req, cookie_req, upgrade_insecure_requests_req, sec_fetch_dest_req, sec_fetch_mode_req, sec_fetch_site_req, sec_fetch_user_req, csrf, id_, version, name, ocfDefaultLocation, accountId, mode_id, temperatureScale, locale, action_update, HTTP_res, date_res, content_type_res, content_length_res, server_res, x_frame_option_res, connection_res) VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}', '{21}', '{22}', '{23}', '{24}', '{25}', '{26}', '{27}', '{28}', '{29}', '{30}', '{31}', '{32}', '{33}')""".format(
        post_req, host_req, user_agent_req, content_length_req, content_type_req, accept_req, accept_language_req,
        accept_encoding_req, origin_req, connection_req, referer_req, cookie_req, upgrade_insecure_requests_req,
        sec_fetch_dest_req, sec_fetch_mode_req, sec_fetch_site_req, sec_fetch_user_req, csrf, id_, version, name,
        ocfDefaultLocation, accountId, mode_id, temperatureScale, locale, action_update, HTTP_res, date_res,
        content_type_res, content_length_res, server_res, x_frame_option_res, connection_res)

    ret = database.executeQuery(query, True, None)

    if (ret):
        return True
    else:
        return False


def simulator_mode_commands_response(response):
    '''
    :param file: text file to find request
    :return: True/False list of files
    '''
    HTTP_res = date_res = content_type_res = content_length_res = server_res = x_frame_option_res = connection_res = None

    with open(response) as responses:
        for line in responses:
            # Filtering
            line = line.split("\n")[0]

            if ("HTTP/1.1" in line):
                HTTP_res = line.split("\n")[0]

                if HTTP_res != 'HTTP/1.1 302 Found':
                    return False
            else:
                if ("Date" in line):
                    date_res = line.split("Date: ")[1]
                else:
                    if ("Location: " in line):
                        content_type_res = line.split("Location: ")[1]
                    else:
                        if ("Content-Length: " in line):
                            content_length_res = line.split("Content-Length: ")[1]
                        else:
                            if ("Server: " in line):
                                server_res = line.split("Server: ")[1]
                            else:
                                if ("X-Frame-Options: " in line):
                                    x_frame_option_res = line.split("X-Frame-Options: ")[1]
                                else:
                                    if ("Connection: " in line):
                                        connection_res = line.split("Connection: ")[1]

    return (HTTP_res, date_res, content_type_res, content_length_res, server_res, x_frame_option_res, connection_res)


def processing_logs_():
    global tempFolder_logs

    if not DEBUG:
        # Getting the directory of the log files
        LogFileDir = input("Log Files Directory (absolute path): ")

        if os.path.exists(LogFileDir) == False:
            print("Invalid directory!\n")
            return processing_logs_()

        print(LogFileDir)

        # Making a directory for extracted logs
        if not os.path.exists(tempFolder_logs):
            os.makedirs(tempFolder_logs)

        # Changing the extension, extracting, moving the actual log file
        logs_processed = logsProcessing(LogFileDir)

        if (not logs_processed): sys.exit()

    # Getting the list of log folders
    logFolders = [f.path for f in os.scandir(tempFolder_logs) if f.is_dir()]
    print(logFolders)
    # If logs.saz extracted
    for logFolder in logFolders:
        print(logFolder)
        print("-------------------")
        if True:

            # Getting the list of files that ends with "_c"
            # logFiles = gather_files_pattern("*.txt")
            logtxtFiles = []
            for file in os.listdir(logFolder + "/raw/"):
                if file.endswith(".txt"):
                    logtxtFiles.append(file)

            for file in logtxtFiles:
                print(file)
                print("-------------------")

                # Reading each of the filess
                with open(logFolder + "/raw/" + file, "rb") as logs:
                    for line in logs:
                        try:
                            line = line.decode().split("\n")[0]
                        except:
                            print("\033[91mAn Unsupported file is detected: " + file)
                            ignoreFile = input("\n\033[0mDo you want to ignore this file? (y/n): ")

                            if ignoreFile == 'y':
                                break
                            else:
                                sys.exit()

                        # Aplication commands can be found by a specific strings
                        # 1. host: api.smartthings.com 2. commands
                        if ("host: api.smartthings.com" in line):
                            for line2 in logs:
                                line2 = line2.decode().split("\n")[0]
                                if ("commands" in line2):
                                    print("Application command: " + file)

                                    app_cmd = application_commands(logFolder + "/raw/" + file, logtxtFiles)

                                    if (app_cmd):
                                        print("Done\n")
                                    else:
                                        print("Error\n")

                                    break



                        else:
                            # Application received events
                            if ("127.0.0.1:" in line):
                                # Getting the URL
                                _, URL = (line.split(" HTTP/1.1")[0]).split(" ")

                                # Searching for the port number
                                m = re.search('(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*', URL)
                                port = int(m.group('port'))

                                # Checking whether if the port is in the acceptable range
                                if (port in acceptableRange):
                                    print("Application received events: " + file)

                                    request = logFolder + "/raw/" + file

                                    # Getting the response
                                    response_name = file.split("_c.txt")[0]
                                    response_file = response_name + "_s.txt"
                                    response = logFolder + "/raw/" + response_file

                                    app_rec_events = application_received_events(request, response)

                                    #
                                    # Both "Application received" file and "application_set_mode_command" file
                                    # got 127.0.0.1:port in their texts, one of the differences is this: "lifecycle":"UPDATE"
                                    #
                                    # So while processing the "Application received" file:
                                    # If the differentiator discovered, the return "Not the related file"
                                    # if the differentiator NOT discovered, the return True/False
                                    #
                                    if (app_rec_events == True):
                                        print("Done\n")
                                        break
                                    else:
                                        if (app_rec_events == False):
                                            print("Error\n")
                                            break
                                        else:
                                            print("Not the related file\n")

                            else:
                                # Simulator (*_c.txt)
                                if ("https://graph-eu01-euwest1.api.smartthings.com/ide/device/executeCommand" in line):
                                    print("Simulator (*_c.txt): " + file)
                                    ret_simulator_status = simulatorCommands_c(logFolder + "/raw/" + file, logtxtFiles)

                                    if (ret_simulator_status):
                                        print("Done\n")
                                    else:
                                        print("Error\n")

                                    break

                                # Simulator (*_s.txt)
                                else:
                                    # Websocket
                                    if ("_w" in file):
                                        print("Websocket: " + file)

                                        ret_webSocket = webSocket(logFolder + "/raw/" + file)
                                        if (ret_webSocket):
                                            print("Done\n")
                                        else:
                                            print("Error\n")

                                        break

                                    # Notification processing
                                    else:
                                        if ("notification " in line):
                                            print("Notification: " + file)

                                            ret_notification = notification_request(logFolder + "/raw/" + file,
                                                                                    logtxtFiles)

                                            if (ret_notification):
                                                print("Done\n")
                                            else:
                                                print("Error\n")

                                        # application_set_mode_command 
                                        else:
                                            if ('"lifecycle":"UPDATE"' in line or '"lifecycle":"INSTALL"' in line):
                                                print("Application set mode command: " + file)

                                                request = logFolder + "/raw/" + file

                                                # Getting the response
                                                response_name = file.split("_c.txt")[0]
                                                response_file = response_name + "_s.txt"
                                                response = logFolder + "/raw/" + response_file

                                                status = application_install_update_requests(request, response)

                                                if (status):
                                                    print("Done\n")
                                                else:
                                                    print("Error\n")

                                            # Application last inistallation phase
                                            else:
                                                if ("PUT https://api.smartthings.com/locations/" in line):
                                                    print("Application last inistallation phase: " + file)

                                                    request = logFolder + "/raw/" + file

                                                    ## Getting the response
                                                    # if the files were generated out of order
                                                    if ("_s.txt" in request):
                                                        response_name = file.split("_s.txt")[0]
                                                        response_file = response_name + "_c.txt"
                                                        response = logFolder + "/raw/" + response_file
                                                    else:
                                                        log_number = file.split("_c.txt")[0]
                                                        request = logFolder + "/raw/" + log_number + "_s.txt"
                                                        response = logFolder + "/raw/" + log_number + "_c.txt"

                                                    status = application_app_mode_commands_request(request,
                                                                                                   response,
                                                                                                   logtxtFiles)

                                                    if (status):
                                                        print("Done\n")
                                                    else:
                                                        print("Error\n")

                                                else:
                                                    if (
                                                            "POST https://graph-eu01-euwest1.api.smartthings.com/location/list HTTP/1.1" in line):
                                                        print("Simulator Mode Commands Request: " + file)

                                                        request = logFolder + "/raw/" + file

                                                        # Getting the response
                                                        response_name = file.split("_c.txt")[0]
                                                        response_file = response_name + "_s.txt"
                                                        response = logFolder + "/raw/" + response_file

                                                        status = simulator_mode_commands_request(request, response,
                                                                                                 logtxtFiles)

                                                        if (status):
                                                            print("Done\n")
                                                        else:
                                                            print("Error\n")

    print("All the logs are processed.")

    if (not DEBUG):
        print("Deleting the unpacked logs...", end="")
        shutil.rmtree(tempFolder_logs)
        print("Done\n\n")


def startForenLog():
    while True:

        operation = input(
            "Select: \n [1] Log Files Processing \n [2] Delete Records of Tables \n [3] Back \n [4] Exit \ninput:")

        if operation == "1":
            processing_logs_()

        elif operation == "2":
            secondAsk = input("Are you sure that you want to clear all tables? (y/n):")

            if secondAsk == 'y':
                print("Deleting the records in the tables...")

                tbls_list = database.executeQuery("select name from sqlite_sequence", False).fetchall()

                for item in tbls_list:
                    print("\tTable: {} ... ".format(item), end="")
                    del_query = "DELETE FROM " + item[0]
                    ret_del_query = database.executeQuery(del_query, False, None)
                    print("Done")

                print("All the tables cleared")
                print("-----------------------------------\n")
                return startForenLog()
            else:
                return startForenLog()
        elif operation == "3":
            return
        elif operation == "4":
            database.closeConnectionCursor()
            quit()
        else:
            return startForenLog()


if __name__ == "__main__":
    startForenLog()
