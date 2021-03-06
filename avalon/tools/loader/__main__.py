"""Main entrypoint for standalone debugging"""
"""
    Used for running 'avalon.tool.loader.__main__' as a module (-m), useful for
    debugging without need to start host.

    Modify AVALON_MONGO accordingly
"""
from . import cli


def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print(exctype, value, traceback)
    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


if __name__ == '__main__':
    import os
    os.environ["AVALON_MONGO"] = "mongodb://localhost:27017"
    os.environ["PYPE_MONGO"] = "mongodb://localhost:27017"
    os.environ["AVALON_DB"] = "avalon"
    os.environ["AVALON_TIMEOUT"] = '3000'
    os.environ["PYPE_DEBUG"] = "3"
    os.environ["AVALON_CONFIG"] = "pype"
    os.environ["AVALON_ASSET"] = "Jungle"


    import sys

    # Set the exception hook to our wrapping function
    sys.excepthook = my_exception_hook

    sys.exit(cli(sys.argv[1:]))
