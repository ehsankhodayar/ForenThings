import re

idList = []


class BotClass:
    """
    To generate IoT Bots or Application Bots, you should use this class.
    """

    def __init__(self, bot_id):
        """
        :param bot_id: The unique device or application ID
        """
        self.__botId = bot_id

        self.__validateBotId()

    def __validateBotId(self):
        """
        Checks if the given Bot ID is a valid and unique ID
        """

        for id in idList:
            if self.__botId == id:
                raise Exception("The Bot ID has been used before!")

        if not self.checkIdFormat(self.getBotId()):
            raise Exception("The Bot ID's format is not valid")
        else:
            idList.append(self.__botId)

    def checkIdFormat(self, signature_string):
        """
        Checks the format of Bot ID
        """

        if re.match("^[a-zA-Z0-9]{8}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{12}$", signature_string):
            return True
        else:
            return False

    def validateTimestampFormat(self, timestamp):
        if re.match("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}", timestamp):
            return True
        else:
            raise Exception("The given timestamp " + timestamp + " is not a valid timestamp.")

    def getBotId(self):
        return self.__botId
