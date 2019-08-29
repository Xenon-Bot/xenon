class BooleanArgs:
    def __init__(self, args):
        self._args = {}
        for arg in args:
            arg = arg.lower()

            if arg == "-":
                self._args = {}

            if arg.startswith("!"):
                self._args[arg.strip("!")] = False

            else:
                self._args[arg] = True

    def get(self, item):
        return self._args.get(item, False)

    def __getattr__(self, item):
        return self.get(item)
