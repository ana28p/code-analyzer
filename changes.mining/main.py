#!/usr/bin/env python3

# from typing import Dict
from pydriller import RepositoryMining
from utils.change import ChangedFile, ChangedMethod, Commit, Modification, ModificationType
# from changes.mining.utils.change import Chan

changed_methods = {}
files = {}


def search_modified_file_or_create(filename, full_path) -> ChangedFile:
    if full_path in files:
        return files[full_path]
    else:
        c_file = ChangedFile(filename, full_path)
        files[full_path] = c_file
        return c_file


def update_modified_file(filename, old_full_path, new_full_path) -> ChangedFile:
    current_c_file = files.pop(old_full_path, None)

    if current_c_file is None:
        c_file = ChangedFile(filename, new_full_path)
        files[new_full_path] = c_file
        return c_file
    else:
        current_c_file.filename = filename
        current_c_file.full_path = new_full_path
        current_c_file.old_paths.append(old_full_path)
        files[new_full_path] = current_c_file
        return current_c_file


def remove_methods_of_file(changed_file):
    # to_remove = []
    # for cm in changed_methods:
    #     if cm.changed_file is file:
    #         to_remove.append(cm)
    return {key: value for key, value in changed_methods.items() if value.changed_file != changed_file}


def search_changed_method_or_create(changed_file: ChangedFile, name: str):
    m_key = str(changed_file.full_path) + ':' + name
    if m_key in changed_methods:
        return changed_methods[m_key]
    else:
        new_c_met = ChangedMethod(name, changed_file)
        changed_methods[m_key] = new_c_met
        return new_c_met


# for c in RepositoryMining('C:/Users/aprodea/work/deloitte-tax-compare/.git').traverse_commits():
for c in RepositoryMining('https://github.com/ana28p/testing-with-csharp.git').traverse_commits():
    # print(commit.msg)
    commit = Commit(c.committer_date, c.committer, c.hash)

    for mod in c.modifications:
        modification = Modification(commit, ModificationType(mod.change_type.value))

        old_file = None
        file = None
        if mod.old_path is None:
            file = search_modified_file_or_create(mod.filename, mod.new_path)
        elif mod.new_path is None:
            files.pop(mod.old_path)
            changed_methods = remove_methods_of_file(file)
        elif mod.old_path is not mod.new_path:
            old_file = search_modified_file_or_create(mod.filename, mod.old_path)
            file = update_modified_file(mod.filename, mod.old_path, mod.new_path)

        if file is not None:
            for c_met in mod.changed_methods:
                my_met = search_changed_method_or_create(file, c_met.name)
                my_met.modifications.append(modification)


# for k, m in changed_methods.items():
#     print(k, ' name: ', m.name, ' modifications:', len(m.modifications))

