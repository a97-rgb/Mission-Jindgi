# TOOL: hello — greet someone by name
# DESCRIPTION: Takes a name and returns a greeting. Example: hello Ayush
# USAGE: hello <name>

import sys

def run(args):
    name = " ".join(args) if args else "stranger"
    return f"Hello, {name}. Rajesh here."

if __name__ == "__main__":
    print(run(sys.argv[1:]))
