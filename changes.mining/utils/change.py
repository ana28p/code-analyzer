#!/usr/bin/env python3

from enum import Enum


class ChangedFile:
    def __init__(self, filename, full_path):
        self.filename = filename
        self.full_path = full_path
        self.old_paths = []

    def set_filename(self, filename):
        self.filename = filename

    def set_full_path(self, full_path):
        self.full_path = full_path

    def add_old_full_path(self, old_full_path):
        self.old_paths.append(old_full_path)


class ChangedMethod:
    def __init__(self, name, changed_file: ChangedFile):
        self.name = name
        self.changed_file = changed_file
        self.modifications = []


class ModificationType(Enum):
    ADD = 1
    COPY = 2
    RENAME = 3
    DELETE = 4
    MODIFY = 5
    UNKNOWN = 6


class Commit:
    def __init__(self, date, author, c_hash):
        self.date = date
        self.author = author
        self.commit_hash = c_hash


class Modification:
    def __init__(self, commit: Commit, mod_type: ModificationType):
        self.commit = commit
        self.mod_type = mod_type

