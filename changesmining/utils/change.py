#!/usr/bin/env python3

from enum import Enum


class ChangedFile:
    def __init__(self, filename, full_path):
        self.filename = filename
        self.full_path = full_path
        self.old_paths = []
        self.methods = []
        self.classes = set()

    def set_filename(self, filename):
        self.filename = filename

    def set_full_path(self, full_path):
        self.full_path = full_path

    def add_old_full_path(self, old_full_path):
        self.old_paths.append(old_full_path)


class ChangedMethod:
    def __init__(self, name, class_path):
        self.name = name
        self.class_path = class_path
        self.commits = []


class ModificationType(Enum):
    ADD = 1
    COPY = 2
    RENAME = 3
    DELETE = 4
    MODIFY = 5
    UNKNOWN = 6


class Commit:
    def __init__(self, date, author, msg, c_hash):
        self.date = date
        self.author = author
        self.msg = msg
        self.commit_hash = c_hash


class Modification:
    def __init__(self, commit: Commit, mod_type: ModificationType):
        self.commit = commit
        self.mod_type = mod_type


class MethodsSplit:
    def __init__(self, modification):
        self.changed = modification.changed_methods
        self.before = modification.methods_before
        self.current = modification.methods

        self.obsolete = [m for m in self.changed if m not in self.current]
        self.new = [m for m in self.changed if m not in self.before]
        self.updated = [m for m in self.changed if (m in self.before) and (m in self.current)]

        self.names_before_without_obsolete = [m.long_name for m in self.before if m not in self.obsolete]
        self.names_current_without_new = [m.long_name for m in self.current if m not in self.new]

        self.names_obsolete = [m.long_name for m in self.obsolete]
        self.names_new = [m.long_name for m in self.new]
        self.names_updated = [m.long_name for m in self.updated]
