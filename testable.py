#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module analyzes Python files in a directory structure
and generates JSON data representing classes and functions
that probably require unit tests.
"""

import os
import pyclbr
import json
import click


class Result:
    """
    The following defines attributes of an object returned by pyclbr search:
    ('file', 'lineno', 'module', 'name')
    """
    def __init__(self, obj, **kwargs):
        """
        Class signature expecting an object from a pyclbr search.  Sets the
        object type; override by providing a 'type' keyword argument.
        :param obj: a pyclbr object
        :param kwargs: optional 'type' argument
        :return: None
        """
        self.obj = obj
        self.routes = []

        if 'type' in kwargs:
            self.obj_type = kwargs.pop('type')
        else:
            self.obj_type = obj.__class__.__name__


class ResultJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Result):
            return {
                obj.obj.file: {
                    'type': obj.obj_type,
                    'name': obj.obj.name,
                    'lineno': obj.obj.lineno,
                    'routes': obj.routes,
                }
            }
        return super().default(obj)


class Testable:
    def __init__(self, top_dir='.'):
        if '~' in top_dir:
            top_dir = os.path.expanduser(top_dir)
        self.top_dir = os.path.abspath(top_dir)

    def get_routes(self, contents, lineno):
        """
        In Flask, routes are expressed as decorators.  Since they precede
        the function definition, walk backwards through the module contents,
        starting with preceding line, looking for lines that start with an
        at sign (@).
        :param contents: list of strings representing contents of a Python module
        :param lineno: integer (not zero-based)
        :return: list of strings representing route decorators
        """
        routes = []
        lineno = lineno - 1
        while True:
            lineno = lineno - 1
            if lineno < 0: break
            if contents[lineno].startswith('@'):
                if '.route(' in contents[lineno]:
                    routes.append(contents[lineno].strip())
            else:
                break
        return routes

    def find(self, extensions=None):
        if extensions is None:
            extensions = ('.py', '.sh')

        results = {}

        for parent_dir, sub_dirs, filenames in os.walk(self.top_dir, topdown=False):
            parent_dir = os.path.abspath(parent_dir)

            for filename in filenames:
                if filename == __file__: continue

                if filename.endswith(extensions):
                    fn, ext = os.path.splitext(filename)
                    full_path = os.path.join(parent_dir, filename)
                    if full_path not in results:
                        results[full_path] = []

                    with open(full_path, 'r') as f:
                        contents = f.readlines()

                    module_data  = pyclbr.readmodule_ex(fn, [parent_dir])

                    for name, obj in module_data.items():
                        if not obj.file.startswith(self.top_dir):
                            continue
                        if obj.file != full_path:
                            continue

                        result = Result(obj)
                        results[full_path].append(result)
                        result.routes = self.get_routes(contents, obj.lineno)

        return results


@click.command()
@click.option(
    '--path', 'top_dir',
    default='.',
    type=click.Path(exists=True),
    help="Top-level directory to analyze"
)
@click.option(
    '--extensions',
    default=('.py', '.sh'),
    help="List of file types (e.g., .py, .sh)"
)
def analyze(top_dir, extensions):
    testable = Testable(top_dir)
    results = testable.find(extensions)
    data = json.dumps(results, cls=ResultJSONEncoder, indent=4)
    print(data)


if __name__ == '__main__':
    analyze()
