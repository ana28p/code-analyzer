from enum import Enum


class ChangedFile:
    def __init__(self, filename, full_path):
        self.filename = filename
        self.full_path = full_path
        self.old_paths = []


class ChangedMethod:
    def __init__(self, name, changed_file):
        self.name = name
        self.changedFile = changed_file
        self.modifications = []


class Modification:
    def __init__(self, commit, type):
        self.commit = commit
        self.type = type


class Commit:
    def __init__(self, date, author, c_hash):
        self.date = date
        self.author = author
        self.commit_hash = c_hash


class ModificationType(Enum):
    ADD = 1
    COPY = 2
    RENAME = 3
    DELETE = 4
    MODIFY = 5
    UNKNOWN = 6
