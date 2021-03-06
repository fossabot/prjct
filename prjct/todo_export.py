#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""Export Todo and Done items."""

import json
import sys

import timestring
from topydo.lib import TodoFile, TodoList
from topydo.lib.Config import config as topydo_config
from topydo.lib.Config import ConfigError
from topydo.lib.Filter import HiddenTagFilter
from topydo.lib.printers.Json import JsonPrinter
from topydo.lib.Sorter import Sorter
from topydo.ui.CLIApplicationBase import error

from . import config as prjct_config
from . import __version__
from .util import sort_project_list

# First thing is to poke the configuration and check whether it's sane
# The modules below may already read in configuration upon import, so
# make sure to bail out if the configuration is invalid.
try:
    topydo_config()
except ConfigError as config_error:
    error(str(config_error))
    sys.exit(1)



def sorted_todos_by_project(cfg, todo_cfg=None):
    """
    Takes our todo list, and returns two dictionaries of where the keys equal
    to the project name, and the value is a list of todo items under that
    project.

    - Note that a todo item may be appended to multiple second level HTML lists
        if the item is listed under multiple projects.
    - Note that todo items without a project are discarded.
    - Note that completed items beyond `completion_cutoff` (measured in days)
        are discarded.

    todo_cfg is called to topydo.config directs as the path of the test
        configuration. Setting this to None will use the normal configuration.
    """
    '''
    print(type(cfg))
    print(cfg)
    print(type(cfg['todo']), cfg['todo'])
    print(type(cfg['todo']['completion_cutoff']), cfg['todo']['completion_cutoff'])
    '''
    completion_range = timestring.Range('last {!s} days'.format(cfg['todo']['completion_cutoff']))

    my_sorter = Sorter(p_sortstring=cfg['todo']['sort_string'])

    todofile = TodoFile.TodoFile(topydo_config(todo_cfg).todotxt())
    # print('Loaded todo file from {}'.format(todofile.path))
    todotodos = TodoList.TodoList(todofile.read())
    # todolist = my_sorter.sort(todolist)            # in topydo v0.10
    # json_str = JsonPrinter().print_list(todolist)  # in topydo v0.10
    todolist = my_sorter.sort(todotodos.todos())    # sort before filters
    # filters return a list, so apply them all at once?
    todolist = HiddenTagFilter().filter(todolist)
    todo_json_str = JsonPrinter().print_list(todolist)
    todo_json = json.loads(todo_json_str)

    donefile = TodoFile.TodoFile(topydo_config(todo_cfg).archive())
    # print('Loaded done file from {}'.format(donefile.path))
    donetodos = TodoList.TodoList(donefile.read())
    donelist = my_sorter.sort(donetodos.todos())
    donelist = HiddenTagFilter().filter(donelist)
    done_json_str = JsonPrinter().print_list(donelist)
    done_json = json.loads(done_json_str)

    active_todos = {}
    completed_todos = {}

    for my_json in [todo_json, done_json]:
        for todo in my_json:
            if not todo['completed']:
                for project in todo['projects']:
                    try:
                        active_todos[project].append(todo['source'])
                    except KeyError:
                        active_todos[project] = [todo['source']]
            else:
                completion_date = timestring.Date(todo['completion_date'])
                if completion_date in completion_range:
                    for project in todo['projects']:
                        try:
                            completed_todos[project].append(todo['source'])
                        except KeyError:
                            completed_todos[project] = [todo['source']]

    return active_todos, completed_todos


def to_html_dicts(*, indent='', open_icon='<i class="fa fa-square-o"></i> ',
                                done_icon='<i class="fa fa-check-square-o"></i> '):
    """
    Takes our todo list, and returns two dictionaries of where the keys equal
    to the project name, and the value is a string of the todo items for that
    project as an HTML unordered list.

    - Note that a todo item may be appended to multiple second level HTML lists
        if the item is listed under multiple projects.
    - Note that todo items without a project are discarded.
    - Note that completed items beyond `completion_cutoff` (measured in days)
        are discarded.

    To make use of the default checkboxes, install FontAwesome in your page.

    Alternate icons:

    ```
    open_icon = '<input type="checkbox" disabled> '
    done_icon = '<input type="checkbox" disabled checked> '

    ```

    Args:
        indent  each line of the output is indented by this
    """
    cfg = prjct_config.load_or_install_prjct()

    active_todos, completed_todos = sorted_todos_by_project(cfg)

    todo_html = {
        project.lower(): '{0}<ul class="prjct-task-list">\n\
                          {0}    <li class="prjct-task-list-item">{1}'.format(indent, open_icon) + \
                         '</li>\n{0}    <li class="prjct-task-list-item">{1}'.format(indent, open_icon).join(todo_list) + \
                         '</li>\n{0}</ul>'.format(indent)
        for project, todo_list in active_todos.items()
    }
    done_html = {
        project.lower(): '{0}<ul class="prjct-task-list">\n\
                          {0}    <li class="prjct-task-list-item">{1}'.format(indent, done_icon) + \
                         '</li>\n{0}    <li class="prjct-task-list-item">{1}'.format(indent, done_icon).join([todo[2:] for todo in todo_list]) + \
                         '</li>\n{0}</ul>'.format(indent)
        for project, todo_list in completed_todos.items()
    }

    return todo_html, done_html


def project_list(todo_cfg=None):
    """
    Provide a full (Python) list of all projects.

    Takes our todo list and our done list, and returns a (Python) list of all
    projects found.
    """
    todofile = TodoFile.TodoFile(topydo_config(todo_cfg).todotxt())
    # print('Loaded todo file from {}'.format(todofile.path))
    todotodos = TodoList.TodoList(todofile.read())
    todo_projects = todotodos.projects()

    donefile = TodoFile.TodoFile(topydo_config(todo_cfg).archive())
    # print('Loaded done file from {}'.format(donefile.path))
    donetodos = TodoList.TodoList(donefile.read())
    done_projects = donetodos.projects()

    # operator called 'join' and gives the union of the two sets
    all_projects_list = list(todo_projects | done_projects)
    return sort_project_list(all_projects_list)


def all_projects_entry():
    """Create a (basic) markdown entry that is tagged with all projects."""
    all_tags_str = ', '.join(project_list())
    cfg = prjct_config.load()

    my_entry = """\
title: All Projects
date: {}
tags: {}

This is a placeholder entry created by *prjct* v.{}, tagged with all projects
listed on your todo and done lists.
""".format(cfg['export']['all_projects_date'], all_tags_str, __version__)

    return my_entry
