#!/usr/bin/env python3

class ChangedFile:
    def __init__(self, filename, full_path):
        self.filename = filename
        self.full_path = full_path
        self.methods = []

    def set_filename(self, filename):
        self.filename = filename

    def set_full_path(self, full_path):
        self.full_path = full_path


class ChangedMethod:
    def __init__(self, name, class_path):
        self.name = name
        self.class_path = class_path
        self.commits = []
        self.previous_long_name = ''


class Commit:
    def __init__(self, date, author, msg, c_hash):
        self.date = date
        self.author = author
        self.msg = msg
        self.commit_hash = c_hash
        self.changed_lines = 0


class MethodsSplit:
    def __init__(self, modification):
        self.changed = modification.changed_methods
        self.before = modification.methods_before
        self.current = modification.methods

        before_long_names = [m.long_name for m in self.before]
        current_long_names = [m.long_name for m in self.current]

        self.obsolete = [m for m in self.changed if m.long_name not in current_long_names]
        self.new = [m for m in self.changed if m.long_name not in before_long_names]
        self.updated = [m for m in self.changed if (m.long_name in before_long_names) and (m.long_name in current_long_names)]

        self.names_obsolete = [m.long_name for m in self.obsolete]
        self.names_new = [m.long_name for m in self.new]
        self.names_updated = [m.long_name for m in self.updated]

        self.names_before_without_obsolete = [name_m for name_m in before_long_names if name_m not in self.names_obsolete]
        self.names_current_without_new = [name_m for name_m in current_long_names if name_m not in self.names_new]

    def exist_new(self):
        return len(self.new) > 0

    def exist_obsolete(self):
        return len(self.obsolete) > 0

    def exist_updated(self):
        return len(self.updated) > 0
