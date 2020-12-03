#!/usr/bin/env python3

from difflib import SequenceMatcher, Differ
from typing import List
import time
import copy

from pydriller import RepositoryMining
from pydriller.domain.commit import Method, Modification, ModificationType
from utils.change import ChangedFile, ChangedMethod, Commit, MethodsSplit
from utils.helpers import split_method_long_name, write_to_csv, write_to_cvs_trash


changed_methods = {}
files = {}
commit_deleted_methods = {}


def search_modified_file_or_create(filename: str, full_path: str) -> ChangedFile:
    if full_path in files:
        return files[full_path]
    else:
        c_file = ChangedFile(filename, full_path)
        files[full_path] = c_file
        return c_file


def update_modified_file(filename: str, old_full_path: str, new_full_path: str) -> ChangedFile:
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


def get_matches_for_method(changed_file: ChangedFile, commit_hash: str, method_long_name: str):
    matches = [m for m in changed_file.methods
               if (m.class_path + m.name).replace(' ', '') == method_long_name.replace(' ', '')]
    if len(matches) == 0:
        sig, _ = split_method_long_name(method_long_name)
        # can be the case that two different commits change the method signature in different ways
        # try to search for a method with the same name
        matches = [m for m in changed_file.methods if m.name[:m.name.rfind('(')] == sig[:sig.rfind('(')]]
        # if there are more matches with the same name;
        # return an empty list such that the method will be added as new
        if len(matches) > 1:
            return []

    if len(matches) > 1:
        raise ValueError('The method {} was not found (should be present) '
                         'or too many matches {} for file {} in commit {}'
                         .format(method_long_name, [(m.class_path + m.name) for m in matches],
                                 changed_file.full_path, commit_hash))
    return matches


def update_or_create_method_using_str(changed_file: ChangedFile, method_long_name: str, commit: Commit):

    matches = get_matches_for_method(changed_file, commit.commit_hash, method_long_name)

    if len(matches) == 1:
        matches[0].commits.append(commit)
    elif len(matches) == 0:
        method_signature, class_path = split_method_long_name(method_long_name)
        m = ChangedMethod(method_signature, class_path)
        m.commits.append(commit)
        changed_file.methods.append(m)


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


def update_or_create_method(modification: Modification, changed_file: ChangedFile, method: Method, commit: Commit):

    commit_copy = copy.deepcopy(commit)
    try:
        commit_copy.changed_lines = get_number_of_changed_lines(modification, current_method=method)
    except Exception as e:
        print(e, "Commit msg: '{}' , hash {}".format(commit.msg, commit.commit_hash))

    update_or_create_method_using_str(changed_file, method.long_name, commit_copy)


def replace_and_update_method(modification: Modification,
                              c_file: ChangedFile,
                              commit: Commit,
                              obs_m: Method,
                              new_m: Method):
    commit_copy = copy.deepcopy(commit)
    try:
        commit_copy.changed_lines = get_number_of_changed_lines(modification, current_method=new_m, prev_method=obs_m)
    except Exception as e:
        print(e, "Commit msg: '{}' , hash {}".format(commit.msg, commit.commit_hash))

    old_long_name = obs_m.long_name
    new_long_name = new_m.long_name

    matches = get_matches_for_method(c_file, commit.commit_hash, old_long_name)

    if len(matches) == 1:
        signature, class_path = split_method_long_name(new_long_name)
        matches[0].name = signature
        matches[0].class_path = class_path
        matches[0].commits.append(commit_copy)


def add_methods(changed_file: ChangedFile, methods: List[Method], commit: Commit):
    for m in methods:
        update_or_create_method_using_str(changed_file, m.long_name, commit)


def update_all_methods_with_new_class(c_file: ChangedFile, current_path: str, new_class_path: str):
    for m in c_file.methods:
        if m.class_path == current_path:
            m.class_path = new_class_path
            break


def update_methods_with_new_class(c_file: ChangedFile, methods: List[str], current_path: str, new_class_path: str):
    for m in c_file.methods:
        long_name = m.class_path + m.name
        if (long_name in methods) and (m.class_path == current_path):
            m.class_path = new_class_path


def update_method_with_new_class(c_file: ChangedFile, method_name: str, current_path: str, new_class_path: str):
    for m in c_file.methods:
        if (m.class_path == current_path) and (m.name == method_name):
            m.class_path = new_class_path
            break


def possible_rename_check(mod: Modification):
    diff = mod.diff.splitlines(1)
    for i in range(len(diff)):
        line = diff[i].lower()
        if line.startswith('-') and (("namespace " in line)
                                     or ("class " in line)
                                     or ("struct " in line)):
            return True
    return False


def add_to_trash(methods: List[ChangedMethod], commit: Commit):
    if commit in commit_deleted_methods:
        commit_deleted_methods[commit].append(methods)
    else:
        commit_deleted_methods[commit] = [methods]


def remove_methods(c_file: ChangedFile, obsolete_methods: List[str], commit: Commit):
    to_remove = [m for m in c_file.methods if (m.class_path + m.name) in obsolete_methods]
    c_file.methods = [m for m in c_file.methods if m not in to_remove]
    add_to_trash(to_remove, commit)


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
            remove_methods(c_file, methods.names_obsolete, commit)
        else:
            # in case methods were updated and their namespace or class renamed, they will appear as obs and new
            updated_obs = []
            for om in methods.obsolete:
                to_replace = ('', '', 0)
                for nm in methods.new:
                    sig_obs_m, cls_obs_m = split_method_long_name(om.long_name)
                    sig_new_m, cls_new_m = split_method_long_name(nm.long_name)

                    # check first if the namespace or class were renamed, but they have the same signature
                    if (cls_obs_m in renamed) and (renamed[cls_obs_m] == cls_new_m) and (sig_obs_m == sig_new_m):
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
                remove_methods(c_file, to_remove, commit)

    for m in methods.names_new:
        update_or_create_method_using_str(c_file, m, commit)

    for m in methods.updated:
        update_or_create_method(modification, c_file, m, commit)


def reset_changed_methods_and_save_name():
    for _, changed_file in files.items():
        for m in changed_file.methods:
            m.previous_long_name = m.class_path + m.name
            m.commits.clear()


def mine(repository: str, from_tag: str = None, to_tag: str = None):
    c_count = 0
    for c in RepositoryMining(repository,
                              # only_modifications_with_file_types=['.cs'],
                              from_tag=from_tag,
                              to_tag=to_tag,
                              ).traverse_commits():

        commit = Commit(c.committer_date, c.committer, c.msg, c.hash)
        count_commit = False

        for mod in c.modifications:
            if not mod.filename.endswith('.cs'):
                continue
            count_commit = True
            try:
                if mod.change_type == ModificationType.ADD:
                    # add all methods for file
                    c_file = search_modified_file_or_create(mod.filename, mod.new_path)
                    add_methods(c_file, mod.methods, commit)
                elif mod.change_type == ModificationType.DELETE:
                    # delete file (and its methods)
                    removed = files.pop(mod.old_path)
                    add_to_trash(removed.methods, commit)
                else:
                    if mod.change_type == ModificationType.RENAME:
                        c_file = update_modified_file(mod.filename, mod.old_path, mod.new_path)
                    else:
                        c_file = search_modified_file_or_create(mod.filename, mod.new_path)

                    check_and_update_methods(c_file, commit, mod)
            except Exception as e:
                print(e)
                print('Commit {} {} {}'.format(c.hash, c.msg, c.committer_date))
                print('Modification {}'.format(mod.filename))
                print(mod.diff_parsed)
        if count_commit:
            c_count += 1

    print("commits parsed: ", c_count)


def mine_and_save_output(repo: str, save_location: str):
    print('========================== mine ==========================')
    start_time = time.time()

    mine(repo)
    write_to_csv(files, save_location + '/commits.csv')

    print("--- %s seconds ---" % (time.time() - start_time))


def mine_before_and_after_tag(repo: str, tag: str, save_location: str):
    print('========================== mine to tag ==========================')
    start_time = time.time()

    mine(repo, to_tag=tag)
    write_to_csv(files, save_location + '/commits-to-' + tag + '.csv')

    print("--- %s seconds ---" % (time.time() - start_time))

    # remove the commits from the methods and save their current long name in the previous_name field
    reset_changed_methods_and_save_name()

    write_to_cvs_trash(commit_deleted_methods, save_location + '/removed-to-' + tag + '.csv')
    # clear the list of removed
    commit_deleted_methods.clear()

    print('========================== mine from tag ==========================')
    start_time = time.time()

    mine(repo, from_tag=tag)
    write_to_csv(files, save_location + '/commits-from-' + tag + '.csv', include_prev_name=True)

    print("--- %s seconds ---" % (time.time() - start_time))

    write_to_cvs_trash(commit_deleted_methods, save_location + '/removed-from-' + tag + '.csv')


if __name__ == '__main__':

    # repo = 'C:/Users/aprodea/work/deloitte-tax-compare/.git'

    # repo = 'C:/Users/aprodea/work/experiment-projects/sharex/ShareX/.git'
    # tag = '1.1.1_june_2017'
    # save_location = 'C:/Users/aprodea/work/metrics-tax-compare/commits/new'

    use_repo = 'https://github.com/ShareX/ShareX.git'
    use_tag = 'v12.0.0'
    save_to_location = 'C:/Users/aprodea/work/experiment-projects/sharex/commits/v12.0.0'

    # repo = 'https://github.com/OptiKey/OptiKey.git'
    # repo = 'C:/Users/aprodea/work/experiment-projects/optikey/OptiKey/.git'
    # tag = 'v3.0.0'
    # save_location = 'C:/Users/aprodea/work/experiment-projects/optikey/commits/v3.0.0'

    # mine('https://github.com/ana28p/testing-with-csharp.git')

    mine_before_and_after_tag(repo=use_repo,
                              tag=use_tag,
                              save_location=save_to_location)

    # mine_and_save_output(repo=repo, save_location=save_location)

    # print_actual_files(files)
