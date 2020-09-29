#!/usr/bin/env python3

import csv
# from typing import Dict
from difflib import SequenceMatcher
from typing import List

from pydriller import RepositoryMining
from pydriller.domain.commit import Method, ModificationType
from utils.change import ChangedFile, ChangedMethod, Commit, Modification
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
    # print('before pop: ', files)
    current_c_file = files.pop(old_full_path, None)
    # print('after pop: ', files)
    # print(current_c_file)

    if current_c_file is None:
        c_file = ChangedFile(filename, new_full_path)
        files[new_full_path] = c_file
        return c_file
    else:
        current_c_file.filename = filename
        current_c_file.full_path = new_full_path
        current_c_file.old_paths.append(old_full_path)
        # print('it was changed and added', current_c_file)
        files[new_full_path] = current_c_file
        # print(files)
        return current_c_file


# def search_changed_method_or_create(changed_file: ChangedFile, name: str):
#     m_key = str(changed_file.full_path) + ':' + name
#     if m_key in changed_methods:
#         return changed_methods[m_key]
#     else:
#         new_c_met = ChangedMethod(name, changed_file)
#         changed_methods[m_key] = new_c_met
#         return new_c_met


def split_method_long_name(long_name):
    start_of_name = long_name.rfind('::')
    if start_of_name < 0:
        raise Exception('Invalid method name ', long_name)
    start_of_name += 2  # add length of separator
    return long_name[start_of_name:], long_name[:start_of_name]


def update_or_create_method_using_str(changed_file: ChangedFile, method_long_name, commit: Commit):
    matches = [v for v in changed_file.methods if (v.class_path + v.name) == method_long_name]

    if len(matches) == 1:
        matches[0].commits.append(commit)
    elif len(matches) == 0:
        method_signature, class_path = split_method_long_name(method_long_name)
        m = ChangedMethod(method_signature, class_path)
        m.commits.append(commit)
        changed_file.methods.append(m)
        changed_file.classes.add(class_path)
    else:
        raise Exception("Methods with the same long name in a file ", [m.name for m in changed_file.methods])


def update_or_create_method(changed_file: ChangedFile, method: Method, commit: Commit):
    update_or_create_method_using_str(changed_file, method.long_name, commit)


def add_methods(changed_file: ChangedFile, methods: List[Method], commit: Commit):
    for m in methods:
        update_or_create_method(changed_file, m, commit)


def update_methods_with_new_class(c_file: ChangedFile, current_path, new_class_path):
    for m in c_file.methods:
        if m.class_path == current_path:
            m.class_path = new_class_path
    c_file.classes.add(new_class_path)

def update_method_with_new_class(c_file: ChangedFile, method_name, current_path, new_class_path):
    for m in c_file.methods:
        if (m.class_path == current_path) and (m.name == method_name):
            m.class_path = new_class_path
    c_file.classes.add(new_class_path)


def search_old_method(c_file, m, methods_before):
    sig, class_path = split_method_long_name(m.long_name)
    for old_m in methods_before:
        sig2, old_class_path = split_method_long_name(old_m.long_name)
        if (sig == sig2) and (m.start_line in range(old_m.start_line - 10, old_m.start_line + 10)):
            update_method_with_new_class(c_file, sig, old_class_path, class_path)
            return


def check_class_rename(c_file, mod):
    if len(mod.changed_methods) == 0:
        # check the current methods if they have a class path not included for this file
        if len(c_file.classes) == 1:
            # it is enough to check only one method
            _, class_path = split_method_long_name(mod.methods[0].long_name)
            if class_path not in c_file.classes:
                current_class = c_file.classes.pop()
                update_methods_with_new_class(c_file, current_class, class_path)
        else:
            # the methods are in the order they appear in the file (should work if no other change was done)
            for i in range(len(mod.methods)):
                sig, old_class = split_method_long_name(mod.methods_before[i].long_name)
                _, new_class = split_method_long_name(mod.methods[i].long_name)
                update_method_with_new_class(c_file, sig, old_class, new_class)
    else:
        # current_class_paths = set()
        for m in mod.methods:
            sig, class_path = split_method_long_name(m.long_name)
            # current_class_paths.add(class_path)
            search_old_method(c_file, m, mod.methods_before)


def remove_methods(c_file, obsolete_methods):
    to_remove = [m for m in c_file.methods if (m.class_path + m.name) in obsolete_methods]
    c_file.methods = [m for m in c_file.methods if m not in to_remove]


def replace_method(c_file, commit, old_long_name, new_long_name):
    matches = [m for m in c_file.methods if (m.class_path + m.name) == old_long_name]
    if len(matches) == 1:
        signature, class_path = split_method_long_name(new_long_name)
        matches[0].name = signature
        matches[0].class_path = class_path
        matches[0].commits.append(commit)
    else:
        raise Exception('The method was not found (should be present) or too many matches', matches, old_long_name)


def check_and_update_methods(c_file, commit, modification):
    obsolete_methods = [m.long_name for m in modification.changed_methods if m not in modification.methods]
    new_methods = [m.long_name for m in modification.changed_methods if m not in modification.methods_before]
    updated_methods = [m.long_name for m in modification.changed_methods
                       if (m in modification.methods_before) and (m in modification.methods)]

    # print('obs: ', obsolete_methods)
    # print('new: ', new_methods)
    # print('updated: ', updated_methods)

    if len(obsolete_methods) > 0:  # removed or renamed
        if len(new_methods) == 0:
            remove_methods(c_file, obsolete_methods)
        else:
            updated_obs = []
            for om in obsolete_methods:
                max_sim = ['', '', 0]
                for nm in new_methods:
                    sig_m1, _ = split_method_long_name(om)
                    sig_m2, _ = split_method_long_name(nm)
                    sim = SequenceMatcher(None, sig_m1, sig_m2).ratio()
                    if sim > max_sim[2]:
                        max_sim = [om, nm, sim]
                if max_sim[2] >= 0.75:
                    replace_method(c_file, commit, max_sim[0], max_sim[1])
                    new_methods.remove(max_sim[1])
                    updated_obs.append(max_sim[0])
            if len(updated_obs) != len(obsolete_methods):
                to_remove = [val for val in obsolete_methods if val not in updated_obs]
                remove_methods(c_file, to_remove)
    if len(new_methods) > 0:
        for m in new_methods:
            update_or_create_method_using_str(c_file, m, commit)

    if len(updated_methods) > 0:
        for m in updated_methods:
            update_or_create_method_using_str(c_file, m, commit)


def print_actual_files():
    for key, v_f in files.items():
        print('ooooooooooo', key)
        print(v_f.filename, v_f.full_path)
        for mp in v_f.methods:
            print(mp.class_path + mp.name, ' nr of commits: ', len(mp.commits))


def write_to_csv(list):
    with open('C:/Users/aprodea/work/metrics-tax-compare/commits/commits_tax_compare.csv', 'w') as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',')
        for key, v_f in list.items():
            for mp in v_f.methods:
                method_full_name = (mp.class_path + mp.name)
                filewriter.writerow([v_f.full_path, v_f.filename, method_full_name, len(mp.commits)])


def mine(repo):
    # for c in RepositoryMining('C:/Users/aprodea/work/deloitte-tax-compare/.git').traverse_commits():
    for c in RepositoryMining(repo, only_modifications_with_file_types=['.cs']).traverse_commits():
        # print('--->', c.msg)
        commit = Commit(c.committer_date, c.committer, c.msg, c.hash)

        # print(c.modifications)
        for mod in c.modifications:
            # print(mod.change_type)
            if mod.change_type == ModificationType.ADD:
                # add all methods for file
                c_file = search_modified_file_or_create(mod.filename, mod.new_path)
                add_methods(c_file, mod.methods, commit)
            elif mod.change_type == ModificationType.DELETE:
                # delete file (and its methods)
                files.pop(mod.old_path)
            else:
                # print('not add or delete')
                # print(mod.change_type == ModificationType.RENAME)
                if mod.change_type == ModificationType.RENAME:
                    # print('rename', mod.filename, mod.old_path, mod.new_path)
                    c_file = update_modified_file(mod.filename, mod.old_path, mod.new_path)
                else:
                    c_file = search_modified_file_or_create(mod.filename, mod.new_path)
                # check if the class was renamed; the changed_methods list can be empty
                if len(mod.methods) > 0:
                    check_class_rename(c_file, mod)

                #  check if there are changed_methods
                if len(mod.changed_methods) > 0:
                    check_and_update_methods(c_file, commit, mod)
        # print_actual_files()


mine('C:/Users/aprodea/work/deloitte-tax-compare/.git')
# mine('https://github.com/ana28p/testing-with-csharp.git')
# for k, m in changed_methods.items():
#     print(k, ' name: ', m.name, ' modifications:', len(m.modifications))
write_to_csv(files)
# print_actual_files()
