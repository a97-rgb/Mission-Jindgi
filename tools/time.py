# TOOL: time — current date and time
# DESCRIPTION: Returns the current date and time.
# USAGE: time

import sys
import datetime

def run(args):
    now = datetime.datetime.now()
    return f"Right now it is {now.strftime('%A, %d %B %Y — %H:%M:%S')}."

if __name__ == "__main__":
    print(run(sys.argv[1:]))
