import sqlite3
import os.path


def executeQuery(query, insert=True, extra=None):
    """
    :param query: the query
    :param insert: True if it is inserting and False if it is fetching
    :return: True/False of the related operation
    """

    __BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    __db_path = os.path.join(__BASE_DIR, "database.db")
    __connection = sqlite3.connect(__db_path)
    # __connection.row_factory = sqlite3.Row
    __cursor = __connection.cursor()

    if (insert):
        __cursor.execute(query)
        __connection.commit()
        return True

    if extra is None:
        result = __cursor.execute(query)
        __connection.commit()
    else:
        result = __cursor.execute(query, extra)

    return result


def closeConnectionCursor():
    """
    :return: True/False if the cursor and connection closed
    """
    try:
        __cursor.close()
        __connection.close()
        return True
    except:
        return False


# TODO
def createTables():
    """
    :return: True/False if the cursor and connection closed
    """
    return True


# TODO
def duplication_check(table, conditionDictionary):
    """
    :return: True if something found, otherwise it will return False
    """
    if table is None:
        raise Exception("Duplicate check cannot be done without table name!")

    if conditionDictionary is None:
        raise Exception("Duplicate check cannot be done without conditions!")

    conditions = 'where '
    query = "select * from " + table + ' '
    parameters = []

    for key, val in conditionDictionary.items():
        if conditions == 'where ':
            conditions = conditions + str(key) + ' = ? '
        else:
            conditions = conditions + ' and ' + str(key) + ' = ? '

        parameters.append(val)

    parameters = tuple(parameters)

    query = query + conditions

    row = executeQuery(query, False, parameters).fetchall()

    if len(row) > 0:
        return True

    return False
