# pltrace
Ltrace for python

# TODO
~~- [ ] Make subclasses work (`__init__` fuckery) ~~
~~- [ ] Wrap _all_ magic methods ~~
- [ ] Create new copies of the objects with type() (unset `__dict__`, "hook" all the functions and write a custom getattr) 
- [ ] Fix circular dependencies
- [ ] Figure out fix for classes that can't be subclassed
