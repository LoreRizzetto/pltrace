import sys
import inspect
from pathlib import Path
import runpy
import builtins

# this is really bad code with many hacks
# since we must overwrite __import__ and do ugly things with classes
# to intercept pretty much everything that can be done with a library
# I don't think there is a point in trying to keep the code clean and organized
#
# some notes:
# - the sys.modules cache is not an issue, it's completely handled by the real
#   __import__ implementation thus the modules in sys.modules are "clean", this code
#   simply re-wraps them every time they are imported.
# - breakpoint() shouldn't be called inside new_import because it imports the debugger
#   (pdb or the one pointed to with env vars) so it'll cause infinite recursion
# - this was originally meant to be used on "malicious" (or, better, untrustworthy)
#   code but since it decides whether to intercept or not by looking and the
#   global variables of the module invoking import "malicious" scripts could "evade"
#   interceptions by simply overwriting the __name__ global variable (or by manually
#   invoking __import__("name")).
#   There are more complex and esoteric solutions such as looking at the stack
#   and various attributes of the frames but it's a waste of time since most of the
#   low hanging solutions are easily gamed (as an example by creating a function
#   / code object from scatch: type(lambda: 1)(type((lambda: 1).__code__)(...), ...) )

def wrap(name: str, target: object):
    if not inspect.isbuiltin(target) or inspect.ismodule(target) or callable(target):
        return Wrapped(name, target)
    else:
        print(f"<- B {name} = {target}")
        return target

class Wrapped():
    def __init__(self, name: str, target: object, *a, **k):
        if len(a) != 0 or len(k) != 0:
            print("=" * 10)
            print(name, target, a, k)
            print("=" * 10)
            breakpoint()
            exit(1)
        self.name = name
        self.target = target

    def __call__(self, *arg, **kwarg):
        cname = f"{self.name}({', '.join(map(repr, arg))}, {', '.join(f'{a}={b!r}' for (a, b) in kwarg.items())})"
        print(f"-> {cname}")
        ret = self.target(*arg, **kwarg)
        print(f"<- {ret}") 
        return wrap(cname, ret)

    def __getitem__(self, key: str):
        real_value = self.target[key]
        cname = f"{self.name}[{key!r}]"
        print(f"<- {cname} = {real_value}")
        return wrap(cname, real_value)

    def __getattr__(self, key: str):
        if key in self.__dict__:
            return self.__dict__[key]
        real_value = getattr(self.target, key)
        cname = f"{self.name}.{key}"
        print(f"<- {cname} = {real_value}")
        return wrap(cname, real_value)


def hijack(old_import):
    def new_import(name, globals_=None, locals_=None, fromlist=(), level=0):
        # intercepting every single library would be madness, we must somehow
        # decide what to intercept and what to ignore
        # in this case I've decided to intercept everything that is imported by
        # __main__ or that is imported from a file not in sys.path
        real = old_import(name, globals_, locals_, fromlist, level)

        if globals_ is not None and (
            globals_["__name__"] == "__main__"
            or (
                "__file__" in globals_
                and any(
                    map(lambda x: x in sys.path, Path(globals_["__file__"]).parents)
                )
            )
        ):
            real = wrap(name, real)

        return real

    return new_import


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.executable} {sys.argv[0]} [-m] script_or_package")
        return 1

    builtins.__import__ = hijack(__import__)

    sys.argv.pop(0)  # remove this script path

    if sys.argv[0] == "-m":
        sys.argv.pop(0)  # remove -m
        runpy.run_module(sys.argv[0], run_name="__main__")
    else:
        runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    exit(main())
