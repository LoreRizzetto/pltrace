import sys
import types
import inspect
from pathlib import Path
import runpy
import builtins

builtin_function_or_method = type(open)

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
# TODO when done, check if this comment still applies


def decorate(name: str, fun):
    def decorator(*args, **kwargs):
        nname = f"{name}({', '.join(map(str, args))}, {', '.join(f'{k}={v!r}' for (k,v) in kwargs.items())})"
        print(nname)
        return fun(*args, **kwargs)

    return decorator


def wrap(name: str, target: object) -> object:
    if type(target).__module__ != "builtins" or inspect.ismodule(target) or callable(target):
        if isinstance(target, types.FunctionType) or isinstance(
            target, builtin_function_or_method
        ):
            # if it's a function, decorate it
            return decorate(name, target)
        elif isinstance(target, types.MethodType):
            # if it's a method, decorate the function and rebind it to the instance
            return types.MethodType(decorate(name, target.__func__), target.__self__)
        else:
            # else we can just create a generic class with wrapped attributes
            # the difference between classes and instances is negligible
            try:
                return type(
                    target.__class__.__name__,  # name of the class
                    target.__mro__
                    if hasattr(target, "__mro__")
                    else target.__class__.__mro__,
                    {
                        key: wrap(f"{name}.{key}", value)
                        for (key, value) in target.__dict__.items()
                    } if hasattr(target, "__dict__") else {},
                )
            except TypeError:
                print(f"Bailing on {name}")
                return target
    else:
        # it's a builtin, it can't be instanciated nor it can be called.
        # safe to assume it's an instance of an int, bool, str...
        print(f"<- B {name} = {target}")
        return target


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
