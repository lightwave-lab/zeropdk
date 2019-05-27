""" Utils to inspect klayout.db and create a tree of classes and methods."""

import inspect
from textwrap import indent, fill

# print4 = lambda str: print(indent(fill(str, 100, replace_whitespace=False), ' ' * 4))
# print8 = lambda str: print(indent(fill(str, 100, replace_whitespace=False), ' ' * 8))

# print4 = lambda str: print(indent(str, ' ' * 4))
# print8 = lambda str: print(indent(str, ' ' * 8))


def wrapfill(str, width):
    paragraphs = []
    for section in str.split("\n\n"):
        paragraphs.append(fill(section.replace("\\", "\\\\"), width))
    return "\n\n".join(paragraphs)


print4 = lambda str: print(indent(wrapfill(str, 100 - 4), " " * 4))
print8 = lambda str: print(indent(wrapfill(str, 100 - 8), " " * 8))


def inspect_module(module):
    class_dict = dict(inspect.getmembers(module, inspect.isclass))
    for name, klass in class_dict.items():
        print("class {name}:".format(name=name))
        print4("'''" + inspect.getdoc(klass) + "\n'''")
        inspect_class(klass)
        print("")


def inspect_class(klass):
    """ This was designed specifically for klayout.db"""

    # typically methods
    method_dict = dict(inspect.getmembers(klass, inspect.ismethoddescriptor))

    # typically static methods
    builtin_dict = dict(inspect.getmembers(klass, inspect.isbuiltin))

    # typically attributes
    getset_dict = dict(inspect.getmembers(klass, inspect.isgetsetdescriptor))

    print4("# Attributes")
    for name, attribute in getset_dict.items():
        try:
            print4("'''" + inspect.getdoc(attribute) + "'''")
        except Exception:
            print8("pass")
        print4("{name} = None".format(name=name))
        print("")

    print4("# Methods")
    for name, method in method_dict.items():
        print4("def {name}(self, ...):".format(name=name))
        try:
            print8("'''" + inspect.getdoc(method) + "'''")
        except Exception:
            print8("pass")
        print("")

    print4("Static Methods")
    for name, method in builtin_dict.items():
        print4("@classmethod")
        print4("def {name}(cls, ...):".format(name=name))
        try:
            print8("'''" + inspect.getdoc(method) + "'''")
        except Exception:
            print8("pass")
        print("")


if __name__ == "__main__":
    import klayout.db

    inspect_module(klayout.db)
