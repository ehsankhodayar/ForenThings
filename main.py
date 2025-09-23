# This is ForenThings ProtoType.
import sys

sys.path.append('..')

import frontend.cmdInterface


def runTool():
    return frontend.cmdInterface.chooseOperation()


if __name__ == '__main__':
    runTool()
