#!/usr/bin/env python3

import csv
from difflib import SequenceMatcher, Differ
from typing import List
from pprint import pprint
import re
import time
import copy

from pydriller import RepositoryMining
from pydriller.domain.commit import Method, Modification, ModificationType
from utils.change import ChangedFile, ChangedMethod, Commit, MethodsSplit


start_time = time.time()

changed_methods = {}
files = {}
PATTERN = re.compile("(?:namespace|class|struct)\\s(.*?)(?:\\s|\\s?{)")


def search_modified_file_or_create(filename: str, full_path: str) -> ChangedFile:
    if full_path in files:
        return files[full_path]
    else:
        c_file = ChangedFile(filename, full_path)
        files[full_path] = c_file
        return c_file


def update_modified_file(filename: str, old_full_path: str, new_full_path: str) -> ChangedFile:
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


def split_method_long_name(long_name: str) -> (str, str):
    start_of_name = long_name.rfind('::')
    if start_of_name < 0:
        raise Exception('Invalid method name ', long_name)
    start_of_name += 2  # add length of separator
    return long_name[start_of_name:], long_name[:start_of_name]


def update_or_create_method_using_str(changed_file: ChangedFile, method_long_name: str, commit: Commit):
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


# def update_or_create_method(changed_file: ChangedFile, method: Method, commit: Commit):
#     update_or_create_method_using_str(changed_file, method.long_name, commit)


def get_method_content(source_code_lines):
    # trim whitespaces
    source_code_lines = [line.strip(' \t\n') for line in source_code_lines]
    cnt_start = 0
    for i in range(len(source_code_lines)):
        if '{' in source_code_lines[i]:
            cnt_start = i
            break
    return source_code_lines[cnt_start:]


def compare_methods(modification: Modification, method: Method, prev_method: Method) -> int:
    text_before = modification.source_code_before.splitlines()[prev_method.start_line: prev_method.end_line]
    text_current = modification.source_code.splitlines()[method.start_line: method.end_line]

    text_before = get_method_content(text_before)
    text_current = get_method_content(text_current)

    d = Differ()
    result = list(d.compare(text_before, text_current))

    changed_lines = 0
    for line in result:
        if line.startswith('-'):
            line = line[1:].strip(" \n")
            if not line.startswith('//') and len(line) > 1:
                changed_lines += 1

    return changed_lines


def get_number_of_changed_lines(modification: Modification, current_method: Method, prev_method: Method = None):

    if prev_method is None:
        result = [m for m in modification.methods_before if m.long_name == current_method.long_name]
        if len(result) != 1:
            raise Exception("One method with signature {} should exist in previous methods. Currently {} occurrence(s)"
                            .format(current_method.long_name, len(result)))
        prev_method = result[0]

    return compare_methods(modification, prev_method, current_method)


def update_or_create_method(modification: Modification, changed_file: ChangedFile, commit: Commit, method: Method):

    commit_copy = copy.deepcopy(commit)
    try:
        commit_copy.changed_lines = get_number_of_changed_lines(modification, current_method=method)
    except Exception as e:
        print(e, "Commit msg: '{}' , hash {}".format(commit.msg, commit.commit_hash))

    update_or_create_method_using_str(changed_file, method.long_name, commit_copy)


def replace_and_update_method(modification: Modification, c_file: ChangedFile, commit: Commit, obs_m: Method, new_m: Method):
    commit_copy = copy.deepcopy(commit)
    try:
        commit_copy.changed_lines = get_number_of_changed_lines(modification, current_method=new_m, prev_method=obs_m)
    except Exception as e:
        print(e, "Commit msg: '{}' , hash {}".format(commit.msg, commit.commit_hash))

    old_long_name = obs_m.long_name
    new_long_name = new_m.long_name

    matches = [m for m in c_file.methods if (m.class_path + m.name).replace(' ', '') == old_long_name.replace(' ', '')]
    if len(matches) == 0:
        sig, _ = split_method_long_name(old_long_name)
        # can be the case that two different commits change the method signature in different ways
        # try to search for a method with the same name (if it's overloaded then the error is raised)
        matches = [m for m in c_file.methods if m.name[:m.name.rfind('(')] == sig[:sig.rfind('(')]]

    if len(matches) == 1:
        signature, class_path = split_method_long_name(new_long_name)
        matches[0].name = signature
        matches[0].class_path = class_path
        matches[0].commits.append(commit_copy)
    else:
        raise ValueError('The method was not found (should be present) or too many matches',
                         [(m.class_path + m.name) for m in matches], old_long_name, commit.commit_hash, c_file.full_path)


def add_methods(changed_file: ChangedFile, methods: List[Method], commit: Commit):
    for m in methods:
        update_or_create_method_using_str(changed_file, m.long_name, commit)


def update_all_methods_with_new_class(c_file: ChangedFile, current_path: str, new_class_path: str):
    for m in c_file.methods:
        if m.class_path == current_path:
            m.class_path = new_class_path
            break
    c_file.classes.discard(current_path)
    c_file.classes.add(new_class_path)


def update_methods_with_new_class(c_file: ChangedFile, methods: List[str], current_path: str, new_class_path: str):
    for m in c_file.methods:
        long_name = m.class_path + m.name
        if (long_name in methods) and (m.class_path == current_path):
            m.class_path = new_class_path
    c_file.classes.discard(current_path)
    c_file.classes.add(new_class_path)


def update_method_with_new_class(c_file: ChangedFile, method_name: str, current_path: str, new_class_path: str):
    for m in c_file.methods:
        if (m.class_path == current_path) and (m.name == method_name):
            m.class_path = new_class_path
            break
    c_file.classes.add(new_class_path)


# def search_and_update_old_method_with_new_class(c_file, m, methods_before):
#     sig, class_path = split_method_long_name(m.long_name)
#     for old_m in methods_before:
#         sig2, old_class_path = split_method_long_name(old_m.long_name)
#         # check the methods in range +-10; in case the file has more classes with the same method signature
#         if (sig == sig2) and (m.start_line in range(old_m.start_line - 10, old_m.start_line + 10)):
#             update_method_with_new_class(c_file, sig, old_class_path, class_path)
#             break


def get_classes_in_current_file(mod: Modification):
    classes = set()
    for m in mod.methods:
        _, class_path = split_method_long_name(m.long_name)
        classes.add(class_path)
    return classes


def get_match(pattern, text):
    matches = pattern.search(text)
    if matches:
        return matches.groups()[0]
    return None


def possible_rename_check(mod: Modification):
    diff = mod.diff.splitlines(1)
    for i in range(len(diff)):
        line = diff[i].lower()
        if line.startswith('-') and (("namespace " in line)
                                     or ("class " in line)
                                     or ("struct " in line)):
            return True
    return False


# def check_for_replacement(removed_text, added_text):
#     match = get_match(PATTERN, removed_text)
#     if match is not None:
#         replacement_match = get_match(PATTERN, added_text)
#         if replacement_match is not None:
#             if ("namespace" in removed_text) and ("namespace" in added_text):
#                 return match + "::", replacement_match + "::"
#             else:
#                 return "::" + match + "::", "::" + replacement_match + "::"
#     return None

# def check_and_update_class_rename(c_file, mod):
#     diff = mod.diff.splitlines(1)
#     to_replace_groups = []
#     for i in range(len(diff)):
#         if diff[i].startswith('-') and diff[i + 1].startswith('+'):
#             replacement = check_for_replacement(diff[i], diff[i + 1])
#             if replacement is not None:
#                 to_replace_groups.append(replacement)
#     if len(to_replace_groups) == 0:
#         return
#
#     common_methods = [m.long_name for m in mod.methods if m in mod.methods_before]
#     for a, b in to_replace_groups:
#         if a.startswith("::"):
#             old_paths = [c for c in c_file.classes if a in c]
#             op = old_paths[0]
#             new_op = op.replace(a, b)
#             print('replace: ', op, " with: ", new_op)
#             update_methods_with_new_class(c_file, common_methods, op, new_op)
#         else:
#             old_paths = [op for op in c_file.classes if op.startsWith(a)]
#             for op in old_paths:
#                 new_op = op.replace(a, b)
#                 print('replace: ', op, " with: ", new_op)
#                 update_methods_with_new_class(c_file, common_methods, op, new_op)


# def check_class_rename(c_file, mod):
#     if len(mod.changed_methods) == 0:
#         if len(c_file.classes) == 1:
#             # it is enough to check only one method when there is only one class per file
#             _, class_path = split_method_long_name(mod.methods[0].long_name)
#             if class_path not in c_file.classes:
#                 current_class = c_file.classes.pop()
#                 update_all_methods_with_new_class(c_file, current_class, class_path)
#         else:
#             # the methods are in the order they appear in the file
#             for i in range(len(mod.methods)):
#                 sig, old_class = split_method_long_name(mod.methods_before[i].long_name)
#                 sig2, new_class = split_method_long_name(mod.methods[i].long_name)
#                 if (sig == sig2) and (old_class != new_class):
#                     c_file.classes.discard(old_class)
#                     update_method_with_new_class(c_file, sig, old_class, new_class)
#     else:
#         all_classes = get_classes_in_current_file(mod)
#         if (len(all_classes) == 1) and (len(c_file.classes) == 1):
#             cls = all_classes.pop()
#             if cls not in c_file.classes:
#                 current_class = c_file.classes.pop()
#                 for m in mod.methods:
#                     sig, new_class = split_method_long_name(m.long_name)
#                     update_method_with_new_class(c_file, sig, current_class, new_class)
#         else:
#             check_and_update_class_rename(c_file, mod)


def remove_methods(c_file: ChangedFile, obsolete_methods: List[str]):
    to_remove = [m for m in c_file.methods if (m.class_path + m.name) in obsolete_methods]
    c_file.methods = [m for m in c_file.methods if m not in to_remove]


def get_map_of_methods(methods: List[str]):
    methods_dict = {}
    for m in methods:
        sig, class_path = split_method_long_name(m)
        if class_path in methods_dict:
            methods_dict[class_path].append(sig)
        else:
            methods_dict[class_path] = [sig]
    for v in methods_dict.values():
        v.sort()
    return methods_dict


def check_for_rename(modification: Modification, c_file: ChangedFile, methods: MethodsSplit) -> dict:
    if not possible_rename_check(modification):
        return {}

    before = methods.names_before_without_obsolete
    current = methods.names_current_without_new

    before_dict = get_map_of_methods(before)
    current_dict = get_map_of_methods(current)

    renamed = {}

    for b_cls_path, b_methods in before_dict.items():
        for cls_path, methods in current_dict.items():
            if (b_methods == methods) and (b_cls_path != cls_path):
                # replace b_cls_path with cls_path
                update_methods_with_new_class(c_file, before, b_cls_path, cls_path)
                renamed[b_cls_path] = cls_path
    return renamed


def check_and_update_methods(c_file: ChangedFile, commit: Commit, modification: Modification):
    methods = MethodsSplit(modification)

    renamed = check_for_rename(modification, c_file, methods)

    if len(methods.names_obsolete) > 0:  # removed or renamed
        if len(methods.names_new) == 0:  # no new => only removed
            remove_methods(c_file, methods.names_obsolete)
        else:
            # in case methods were updated and their namespace or class renamed, they will appear as obs and new
            updated_obs = []
            for om in methods.obsolete:
                to_replace = ('', '', 0)
                for nm in methods.new:
                    sig_obs_m, cls_obs_m = split_method_long_name(om.long_name)
                    sig_new_m, cls_new_m = split_method_long_name(nm.long_name)

                    # check first if the namespace or class were renamed
                    if renamed and (renamed[cls_obs_m] == cls_new_m):
                        to_replace = (om, nm, 1)
                        break
                    else:
                        # check for method rename using similarity
                        sim = SequenceMatcher(None, sig_obs_m, sig_new_m).ratio()
                        if sim > to_replace[2]:
                            to_replace = (om, nm, sim)

                obs_m, new_m, similarity = to_replace
                if similarity >= 0.7:
                    try:
                        replace_and_update_method(modification, c_file, commit, obs_m, new_m)
                        updated_obs.append(obs_m.long_name)
                        methods.names_new.remove(new_m.long_name)
                        methods.new.remove(new_m)
                    except ValueError as e:
                        # if the replace fails, don't do anything
                        # the old method will be removed and the new method will be considered as new
                        print(e)
            # remove obsolete methods that were not updated
            if len(updated_obs) != len(methods.names_obsolete):
                to_remove = [val for val in methods.names_obsolete if val not in updated_obs]
                remove_methods(c_file, to_remove)

    for m in methods.names_new:
        update_or_create_method_using_str(c_file, m, commit)

    for m in methods.updated:
        update_or_create_method(modification, c_file, commit, m)


def print_actual_files():
    for key, v_f in files.items():
        print('ooooooooooo', key)
        print(v_f.filename, v_f.full_path)
        for mp in v_f.methods:
            print(mp.class_path + mp.name, ' nr of commits: ', len(mp.commits),
                  'nr of chg lines: ', sum([c.changed_lines for c in mp.commits]))


def write_to_csv(dict_files):
    with open('C:/Users/aprodea/work/metrics-tax-compare/commits/commits-tax.csv', 'w') as csvfile:
        fieldnames = ['Full_path', 'Filename', 'Method', 'Changes', 'ChgLines']
        file_writer = csv.DictWriter(csvfile, fieldnames, delimiter=';', lineterminator='\n')
        file_writer.writeheader()
        for key, v_f in dict_files.items():
            for mp in v_f.methods:
                method_full_name = (mp.class_path + mp.name)
                chg_lines = sum([c.changed_lines for c in mp.commits])
                file_writer.writerow({
                    'Full_path': v_f.full_path,
                    'Filename': v_f.filename,
                    'Method': method_full_name,
                    'Changes': len(mp.commits),
                    'ChgLines': chg_lines
                })


def mine(repo):
    # for c in RepositoryMining('C:/Users/aprodea/work/deloitte-tax-compare/.git').traverse_commits():
    # for c in RepositoryMining(repo, single='fea5cc2adb4838c2f005042c5ace1fbca9c43614',
    # only_modifications_with_file_types=['.cs']).traverse_commits():
    for c in RepositoryMining(repo, only_modifications_with_file_types=['.cs']).traverse_commits():
        # print('--->', c.msg)
        commit = Commit(c.committer_date, c.committer, c.msg, c.hash)

        # print(c.modifications)
        for mod in c.modifications:
            if mod.filename.endswith('.cs'):
                if mod.change_type == ModificationType.ADD:
                    # add all methods for file
                    c_file = search_modified_file_or_create(mod.filename, mod.new_path)
                    add_methods(c_file, mod.methods, commit)
                elif mod.change_type == ModificationType.DELETE:
                    # delete file (and its methods)
                    files.pop(mod.old_path)
                else:
                    if mod.change_type == ModificationType.RENAME:
                        c_file = update_modified_file(mod.filename, mod.old_path, mod.new_path)
                    else:
                        c_file = search_modified_file_or_create(mod.filename, mod.new_path)

                    check_and_update_methods(c_file, commit, mod)


mine('C:/Users/aprodea/work/deloitte-tax-compare/.git')
# mine('https://github.com/ana28p/testing-with-csharp.git')

print("--- %s seconds ---" % (time.time() - start_time))

# for k, m in changed_methods.items():
#     print(k, ' name: ', m.name, ' modifications:', len(m.modifications))
write_to_csv(files)
# print_actual_files()
