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


def search_matches_for_method(changed_file: ChangedFile, method_long_name: str):
    matches = [m for m in changed_file.methods
               if (m.class_path + m.name).replace(' ', '') == method_long_name.replace(' ', '')]
    if len(matches) == 0:
        sig, _ = split_method_long_name(method_long_name)
        # can be the case that two different commits change the method signature in different ways (e.g. merge)
        # try to search for a method with the same name
        matches = [m for m in changed_file.methods if m.name[:m.name.rfind('(')] == sig[:sig.rfind('(')]]
        # if there are more matches with the same name;
        # return an empty list such that the method will be added as new
        if len(matches) > 1:
            return []

    return matches


def get_matches_for_method(changed_file: ChangedFile, commit_hash: str, method_long_name: str):
    matches = search_matches_for_method(changed_file, method_long_name)

    if len(matches) > 1:
        print('The method {} has too many matches {} for file {} in commit {}'
              .format(method_long_name, [(m.class_path + m.name) for m in matches],
                      changed_file.full_path, commit_hash))

    return matches


def create_method_using_str(changed_file: ChangedFile, method_long_name: str, commit: Commit):
    method_signature, class_path = split_method_long_name(method_long_name)

    m = ChangedMethod(method_signature, class_path)
    m.commits.append(commit)
    changed_file.methods.append(m)


def update_or_create_method_using_str(changed_file: ChangedFile, method_long_name: str, commit: Commit):
    matches = get_matches_for_method(changed_file, commit.commit_hash, method_long_name)

    if len(matches) == 1:
        matches[0].commits.append(commit)
    elif len(matches) == 0:
        create_method_using_str(changed_file, method_long_name, commit)


def add_methods(changed_file: ChangedFile, methods: List[Method], commit: Commit):
    for m in methods:
        create_method_using_str(changed_file, m.long_name, commit)


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
            print("One method with signature {} should exist in previous methods. Currently {} occurrence(s)"
                  .format(current_method.long_name, len(result)))
            return 0
        prev_method = result[0]

    return compare_methods(modification, prev_method, current_method)


def update_or_create_method(modification: Modification, changed_file: ChangedFile, method: Method, commit: Commit):

    commit_copy = copy.deepcopy(commit)
    try:
        commit_copy.changed_lines = get_number_of_changed_lines(modification, current_method=method)
    except Exception as e:
        print(e, "Commit msg: '{}' , hash {}".format(commit.msg, commit.commit_hash))

    update_or_create_method_using_str(changed_file, method.long_name, commit_copy)


def update_methods(modification: Modification, c_file: ChangedFile, methods: List[Method], commit: Commit):
    for m in methods:
        update_or_create_method(modification, c_file, m, commit)


def replace_and_update_method(modification: Modification, c_file: ChangedFile, commit: Commit,
                              before_m: Method, new_m: Method):
    commit_copy = copy.deepcopy(commit)
    try:
        commit_copy.changed_lines = get_number_of_changed_lines(modification, current_method=new_m, prev_method=before_m)
    except Exception as e:
        print(e, "Commit msg: '{}' , hash {}".format(commit.msg, commit.commit_hash))

    old_long_name = before_m.long_name
    new_long_name = new_m.long_name

    matches = get_matches_for_method(c_file, commit.commit_hash, old_long_name)

    if len(matches) == 1:
        signature, class_path = split_method_long_name(new_long_name)
        matches[0].name = signature
        matches[0].class_path = class_path
        matches[0].commits.append(commit_copy)
    else:
        print('Method not found {}, or too many matches. Current matches {}'.format(old_long_name, matches))
        print("Commit msg: '{}', hash {}".format(commit.msg, commit.commit_hash))


def update_or_create_methods(modification: Modification, c_file: ChangedFile,
                             methods: List[Method], commit: Commit):
    for m in methods:
        matches = search_matches_for_method(c_file, m.long_name)

        if len(matches) == 0:
            create_method_using_str(c_file, m.long_name, commit)
        else:
            update_or_create_method(modification, c_file, m, commit)


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


def add_to_trash(methods: List[ChangedMethod], commit: Commit):
    if commit in commit_deleted_methods:
        commit_deleted_methods[commit].append(methods)
    else:
        commit_deleted_methods[commit] = [methods]


def remove_methods(c_file: ChangedFile, obsolete_methods: List[str], commit: Commit):
    to_remove = [m for m in c_file.methods if (m.class_path + m.name) in obsolete_methods]
    c_file.methods = [m for m in c_file.methods if m not in to_remove]
    add_to_trash(to_remove, commit)


def get_methods_before(modification: Modification, methods: List[Method]) -> List[Method]:
    methods_long_names = [m.long_name for m in methods]
    result = [m for m in modification.methods_before if m.long_name in methods_long_names]

    return result


# def validate_method_content(method_signature: str, content: List[str]):
#     braces = 0
#     start = 0
#     end = -1
#     is_the_method = False
#     sig, _ = split_method_long_name(method_signature)
#     for i in range(len(content)):
#         line = content[i]
#         if sig in line:
#             start = i
#             is_the_method = True
#         if not is_the_method:
#             continue
#         for c in line:
#             if c == '{':
#                 braces += 1
#             elif c == '}':
#                 braces -= 1
#         if braces == 0:
#             # end of method
#             end = i
#             break
#     return content[start:end]


def get_dict_content_of_methods(source_code: str, methods: List[Method]):
    methods_dict = {}
    for m in methods:
        content = source_code.splitlines()[m.start_line: m.end_line]
        sig, _ = split_method_long_name(m.long_name)
        content.insert(0, sig)  # add also the signature of the method (name + parameters)
        methods_dict[m.long_name] = content
    return methods_dict


def get_pairs_of_similar_methods(dict_methods1, dict_methods2):
    pairs = []
    copy_dict_methods2 = dict_methods2.copy()
    for k1, c1 in dict_methods1.items():
        sm = SequenceMatcher(isjunk=lambda x: x in " \t")  # ignore spaces and tabs
        sm.set_seq2(''.join(c1))
        to_replace = ('', '', 0)
        for k2, c2 in copy_dict_methods2.items():
            sm.set_seq1(''.join(c2))
            sim = sm.ratio()
            if sim > to_replace[2]:
                to_replace = (k1, k2, sim)

        m1, m2, similarity = to_replace
        if similarity >= 0.6:
            pairs.append((m1, m2))
            copy_dict_methods2.pop(m2)  # remove it to don't check it again

    return pairs


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


def possible_rename_check(mod: Modification):
    diff = mod.diff.splitlines(1)
    for i in range(len(diff)):
        line = diff[i].lower()
        if line.startswith('-') and (("namespace " in line)
                                     or ("class " in line)
                                     or ("struct " in line)):
            return True
    return False


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
                break
    return renamed


def check_current_methods(modification, c_file, commit):
    added_methods = [(m.class_path + m.name) for m in c_file.methods]
    for c_m in modification.methods:
        if c_m.long_name not in added_methods:
            print('{} was not present; commit {}'.format(c_m.long_name, commit.commit_hash))
            create_method_using_str(c_file, c_m.long_name, commit)


def handle_new_updated(modification: Modification, m_new, m_updated,
                       c_file: ChangedFile, commit: Commit):
    updated_before = get_methods_before(modification, m_updated)
    d_updated_before = get_dict_content_of_methods(modification.source_code_before, updated_before)

    d_new = get_dict_content_of_methods(modification.source_code, m_new)
    d_updated = get_dict_content_of_methods(modification.source_code, m_updated)
    d_current = {**d_new, **d_updated}

    m_pairs = get_pairs_of_similar_methods(d_updated_before, d_current)

    # print('for commit ', commit.commit_hash, commit.msg, commit.date)
    # print('file ', c_file.filename)
    # print('pairs', [(r, l) for r, l in m_pairs])

    for before_m_name, current_m_name in m_pairs:
        before_m = next(m for m in updated_before if m.long_name == before_m_name)
        current_m = next(m for m in (m_new + m_updated) if m.long_name == current_m_name)
        replace_and_update_method(modification, c_file, commit, before_m, current_m)
        d_current.pop(current_m_name)

    # add or update the rest
    rest_new = [m for m in m_new if m.long_name in list(d_current.keys())]
    add_methods(c_file, rest_new, commit)
    rest_updated = [m for m in m_updated if m.long_name in list(d_current.keys())]
    update_or_create_methods(modification, c_file, rest_updated, commit)


def handle_new_obsolete(modification: Modification, m_new, m_obsolete,
                        c_file: ChangedFile, commit: Commit):
    d_obsolete = get_dict_content_of_methods(modification.source_code_before, m_obsolete)

    d_new = get_dict_content_of_methods(modification.source_code, m_new)

    m_pairs = get_pairs_of_similar_methods(d_obsolete, d_new)

    # print('for commit ', commit.commit_hash, commit.msg, commit.date)
    # print('file ', c_file.filename)
    # print('pairs', [(r, l) for r, l in m_pairs])

    for before_m_name, current_m_name in m_pairs:
        before_m = next(m for m in m_obsolete if m.long_name == before_m_name)
        current_m = next(m for m in m_new if m.long_name == current_m_name)
        replace_and_update_method(modification, c_file, commit, before_m, current_m)
        d_obsolete.pop(before_m_name)
        d_new.pop(current_m_name)

    # add or update the rest
    rest = [m for m in m_new if m.long_name in list(d_new.keys())]
    add_methods(c_file, rest, commit)

    # remove the rest of obsolete
    remove_methods(c_file, list(d_obsolete.keys()), commit)


def handle_new_obsolete_updated(modification: Modification, m_new: List[Method], m_obsolete: List[Method],
                                m_updated: List[Method], c_file: ChangedFile, commit: Commit):

    updated_before = get_methods_before(modification, m_updated)
    d_updated_before = get_dict_content_of_methods(modification.source_code_before, updated_before)
    d_obsolete = get_dict_content_of_methods(modification.source_code_before, m_obsolete)
    d_before = {**d_updated_before, **d_obsolete}

    d_new = get_dict_content_of_methods(modification.source_code, m_new)
    d_updated = get_dict_content_of_methods(modification.source_code, m_updated)
    d_current = {**d_new, **d_updated}

    m_pairs = get_pairs_of_similar_methods(d_before, d_current)

    # print('for commit ', commit.commit_hash, commit.msg, commit.date)
    # print('file ', c_file.filename)
    # print('pairs', [(r, l) for r, l in m_pairs])

    for before_m_name, current_m_name in m_pairs:
        before_m = next(m for m in (m_obsolete + updated_before) if m.long_name == before_m_name)
        current_m = next(m for m in (m_new + m_updated) if m.long_name == current_m_name)
        replace_and_update_method(modification, c_file, commit, before_m, current_m)
        d_before.pop(before_m_name)
        d_current.pop(current_m_name)

    # add or update the rest
    rest_new = [m for m in m_new if m.long_name in list(d_current.keys())]
    add_methods(c_file, rest_new, commit)
    rest_updated = [m for m in m_updated if m.long_name in list(d_current.keys())]
    update_or_create_methods(modification, c_file, rest_updated, commit)

    # remove the rest of obsolete
    remove_methods(c_file, list(d_before.keys()), commit)


def check_and_update_methods2(modification: Modification, c_file: ChangedFile, commit: Commit):
    methods = MethodsSplit(modification)

    renamed = check_for_rename(modification, c_file, methods)

    if methods.exist_new() and not methods.exist_obsolete() and not methods.exist_updated():
        # add all
        add_methods(c_file, methods.new, commit)

    elif methods.exist_updated() and not methods.exist_new() and not methods.exist_obsolete():
        # update all
        update_methods(modification, c_file, methods.updated, commit)

    elif methods.exist_obsolete() and not methods.exist_new() and not methods.exist_updated():
        # remove all
        remove_methods(c_file, methods.names_obsolete, commit)

    elif methods.exist_obsolete() and methods.exist_updated() and not methods.exist_new():
        # remove obsolete and update the updated methods
        remove_methods(c_file, methods.names_obsolete, commit)
        update_methods(modification, c_file, methods.updated, commit)

    elif methods.exist_new() and methods.exist_updated() and not methods.exist_obsolete():
        # get updated before and do similarity check between these and new + current updated
        # maybe the content of a new method is actually an updated method
        handle_new_updated(modification, methods.new, methods.updated, c_file, commit)

    elif methods.exist_new() and methods.exist_obsolete() and not methods.exist_updated():
        # get obsolete and do similarity check between these and new
        # maybe the content of a new method is actually an obsolete method; rename
        handle_new_obsolete(modification, methods.new, methods.obsolete, c_file, commit)

    else:  # obsolete & new & updated
        # get obsolete and updated before and check between those and new + current updated
        handle_new_obsolete_updated(modification, methods.new, methods.obsolete, methods.updated, c_file, commit)

    # check if the file has all the current methods; add those missing
    check_current_methods(modification, c_file, commit)


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


def mine(repository: str, from_tag: str = None, to_tag: str = None,
         from_com: str = None, to_com: str = None):
    c_count = 0
    for c in RepositoryMining(repository,
                              # only_modifications_with_file_types=['.cs'],
                              # only_no_merge=True,
                              from_tag=from_tag,
                              to_tag=to_tag,
                              from_commit=from_com,
                              to_commit=to_com
                              ).traverse_commits():

        commit = Commit(c.committer_date, c.committer, c.msg, c.hash)
        count_commit = False

        for mod in c.modifications:
            if not mod.filename.endswith('.cs'):
                continue
            count_commit = True
            # try:
            if mod.change_type == ModificationType.ADD:
                # add all methods for file
                c_file = search_modified_file_or_create(mod.filename, mod.new_path)
                add_methods(c_file, mod.methods, commit)
            elif mod.change_type == ModificationType.DELETE:
                # delete file (and its methods)
                if mod.old_path in files:
                    removed = files.pop(mod.old_path)
                    add_to_trash(removed.methods, commit)
            else:
                if mod.change_type == ModificationType.RENAME:
                    c_file = update_modified_file(mod.filename, mod.old_path, mod.new_path)
                else:
                    c_file = search_modified_file_or_create(mod.filename, mod.new_path)

                # check_and_update_methods(c_file, commit, mod)
                check_and_update_methods2(mod, c_file, commit)
            # except Exception as e:
            #     print(e)
            #     print('Commit {} {} {}'.format(c.hash, c.msg, c.committer_date))
            #     print('Modification {}'.format(mod.filename))
            #     print(mod.diff_parsed)
        if count_commit:
            c_count += 1

    print("commits parsed: ", c_count)


def mine_and_save_output(repo: str, save_location: str):
    print('========================== mine ==========================')
    start_time = time.time()

    mine(repo)
    write_to_csv(files, save_location + '/commits.csv')

    print("--- %s seconds ---" % (time.time() - start_time))


def mine_before_and_after_tag(repo: str, save_location: str, tag: str = None, commit_hash: str = None):
    print('========================== mine to tag/commit ==========================')
    start_time = time.time()

    file_ext = tag if tag is not None else commit_hash[:5]

    if tag is not None:
        mine(repo, to_tag=tag)
    elif commit_hash is not None:
        mine(repo, to_com=commit_hash)
    write_to_csv(files, save_location + '/commits-to-' + file_ext + '.csv')

    print("--- %s seconds ---" % (time.time() - start_time))

    # remove the commits from the methods and save their current long name in the previous_name field
    reset_changed_methods_and_save_name()

    write_to_cvs_trash(commit_deleted_methods, save_location + '/removed-to-' + file_ext + '.csv')
    # clear the list of removed
    commit_deleted_methods.clear()

    print('========================== mine from tag/commit ==========================')
    start_time = time.time()

    if tag is not None:
        mine(repo, from_tag=tag)
    elif commit_hash is not None:
        mine(repo, from_com=commit_hash)
    write_to_csv(files, save_location + '/commits-from-' + file_ext + '.csv', include_prev_name=True)

    print("--- %s seconds ---" % (time.time() - start_time))

    write_to_cvs_trash(commit_deleted_methods, save_location + '/removed-from-' + file_ext + '.csv')


if __name__ == '__main__':

    # use_repo = 'C:/Users/aprodea/work/deloitte-tax-compare/.git'
    # use_tag = '1.1.1_june_2017'
    # save_to_location = 'C:/Users/aprodea/work/metrics-tax-compare/commits/last'
    # save_to_location = 'C:/Users/aprodea/work/metrics-tax-compare/commits/tag-1.1.1'

    use_repo = 'C:/Users/aprodea/work/deloitte-tax-i/Web/.git'
    # save_to_location = 'C:/Users/aprodea/work/deloitte-tax-i/metrics/commits/last'
    save_to_location = 'C:/Users/aprodea/work/deloitte-tax-i/metrics/commits/commit_23-01-20'
    com = '92ad42d11f3688006d573ce9fb0f763ef3a2398f'

    # save_location = 'C:/Users/aprodea/work/metrics-tax-compare/commits/new'

    # use_repo = 'https://github.com/ShareX/ShareX.git'
    # use_repo = 'C:/Users/aprodea/work/experiment-projects/sharex/ShareX/.git'
    # use_tag = 'v12.0.0'
    # save_to_location = 'C:/Users/aprodea/work/experiment-projects/sharex/commits/v12.0.0'

    # repo = 'https://github.com/OptiKey/OptiKey.git'
    # repo = 'C:/Users/aprodea/work/experiment-projects/optikey/OptiKey/.git'
    # tag = 'v3.0.0'
    # save_location = 'C:/Users/aprodea/work/experiment-projects/optikey/commits/v3.0.0'

    # use_repo = 'https://github.com/ana28p/testing-with-csharp.git'
    # use_repo = 'C:/Users/aprodea/work/testing/DummySolution/.git'
    # save_to_location = 'C:/Users/aprodea/work/testing/last'

    mine_before_and_after_tag(repo=use_repo,
                              save_location=save_to_location,
                              # tag=use_tag,
                              commit_hash=com
                              )

    # mine_and_save_output(repo=use_repo, save_location=save_to_location)

    # print_actual_files(files)
