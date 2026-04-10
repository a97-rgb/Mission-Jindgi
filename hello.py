# DESCRIPTION: Say hello to someone by name
# USAGE: hello <name>

def run(args):
    name = " ".join(args) if args else "there"
    return f"Hello, {name}."
