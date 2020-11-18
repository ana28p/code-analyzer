from pathlib import Path
from difflib import SequenceMatcher

from utils.change import ChangedFile, ChangedMethod, Commit, Modification, ModificationType, MethodsSplit

from pydriller import RepositoryMining


files = {}


def search_modified_file_or_create(filename, full_path) -> ChangedFile:
    if full_path in files:
        return files[full_path]
    else:
        c_file = ChangedFile(filename, full_path)
        files[full_path] = c_file
        return c_file


def add_method(file, methodname, commit):
    m = ChangedMethod(methodname)
    m.commits.append(commit)
    file.methods.append(m)


def update_method(file, methodname, commit):
    matches = [v for v in file.methods if v.name == methodname]
    if len(matches) == 1:
        matches[0].commits.append(commit)
    else:
        add_method(file, methodname, commit)


def print_files():
    for f in files.values():
        print(f.full_path)
        for m in f.methods:
            print(m.name, len(m.commits))


def update_files():
    c = Commit('2020', 'apro', 922883847482)
    file = search_modified_file_or_create('file1', '/path/to/file')
    add_method(file, 'method1', c)
    add_method(file, 'method2', c)
    # print_files()


def update_method_test():
    c = Commit('2020', 'apro', 32343424)
    file = search_modified_file_or_create('file1', '/path/to/file')
    update_method(file, 'method2', c)
    update_method(file, 'method2', c)
    update_method(file, 'method2', c)
    update_method(file, 'method3', c)
    update_method(file, 'method3', c)
    update_method(file, 'method3', c)


def split_method_long_name(long_name):
    start_of_name = long_name.rfind('::')
    if start_of_name < 0:
        raise Exception('Invalid method name ', long_name)
    start_of_name += 2
    return long_name[start_of_name:], long_name[:start_of_name]


# method_signature, class_path = split_method_long_name("test::to::see::split ( st, ft)")
# print(method_signature, '----', class_path)
# update_files()
# update_method_test()
# print_files()

# a = ['add', 'sutract', 'add2', 'subtract', 'pow']
# b = ['add', 'pow']
# a.remove(b)
# print(a)

# 468e305ac3c8bc10bde80d0b1357fa7f78b03410 - commit for method rename
# d29780c984d3a034ee2e3e4ad82aad2de5153782 - commit for the parameter types change
# for c in RepositoryMining('C:/Users/aprodea/work/deloitte-tax-compare/.git',
for c in RepositoryMining('https://github.com/ana28p/testing-with-csharp.git',
                          single='5184eea9a2078b43db04c9c8f2768ac5713506f4').traverse_commits():
    print('----------------------------------')
    print(c.committer.name, c.committer_date, '|| msg: ', c.msg, c.hash)
    for m in c.modifications:
        print(m.filename, m.change_type)
        print(m.old_path, m.new_path)
        ch_mets = [val.long_name for val in m.changed_methods]
        print('changed: ', ch_mets)
        for val in m.changed_methods:
            print(val.name, val.long_name, 'start line {} - end line {}'.format(val.start_line, val.end_line))
        curr_mets = [val.long_name for val in m.methods]
        print('current: ', curr_mets)
        nesting = [val.top_nesting_level for val in m.methods]
        print('nesting: ', nesting)
        old_mets = [val.long_name for val in m.methods_before]
        print('before: ', old_mets)
        not_ex_mets = [x for x in ch_mets if x not in curr_mets]
        if len(not_ex_mets) > 0:
            print('removed or renamed', not_ex_mets)
            # newm = [x for x in curr_mets if x not in old_mets]
            # for nm in not_ex_mets:
            #     for cm in newm:
            #         print(nm, cm, ' similarity', SequenceMatcher(None, nm, cm).ratio())

        modification = m
        obsolete_methods = [m.long_name for m in modification.changed_methods if m not in modification.methods]
        new_methods = [m.long_name for m in modification.changed_methods if m not in modification.methods_before]
        updated_methods = [m.long_name for m in modification.changed_methods
                           if (m in modification.methods_before) and (m in modification.methods)]
        print('obs: ', obsolete_methods)
        print('new: ', new_methods)
        print('updated: ', updated_methods)

        met_split = MethodsSplit(modification)

        print('obs: ', met_split.names_obsolete)
        print('new: ', met_split.names_new)
        print('updated: ', met_split.names_updated)

        print(modification.diff_parsed['added'])
        print(modification.diff_parsed['deleted'])

        print(modification.diff)

        # print(modification.source_code_before.splitlines(True))
        # print(modification.source_code_before)

        # print('>', m.change_type, m.filename, m.old_path, m.new_path)
        # for c_met in m.changed_methods:
        #     print('>>>', c_met.name, c_met.long_name, c_met.fan_in, c_met.fan_out, c_met.general_fan_out)
        # print('methods before: ', len(m.methods_before), ' current: ', len(m.methods),
        #       ' changed: ', len(m.changed_methods), m.token_count)
        # print(m.diff)
        # print('oooooo')
        # print(m.diff_parsed)

# p = Path('./utils/change.py')

# print(p)
# print(str(p))
#
# a_dict = {'color': 'blue', 'fruit': 'apple', 'pet': 'dog'}
# new_dict = {k: v for k, v in a_dict.items() if v != 'blue'}
#
# print(new_dict)
# print(new_dict['pet'])
# trebuie verificat daca metoda este deja definita
# trebuie verificat daca fisierul a fost redenumit/sau metoda redenumita
# daca nu atunci ce adauga una noua
# si verificat daca fisierul exista sau nu

        # if (len(mod.changed_methods) == 0) and (mod.filename.endswith('.cs')) and not (mod.filename.endswith('Dto.cs')):
        #     # print(mod.filename)
        #     if mod.change_type in [ModificationType.ADD, ModificationType.MODIFY]:
        #         print(commit.hash, mod.filename, mod.diff_parsed)
        #         print(mod.diff)
        # print('{} has complexity of {}, and it contains {} methods'.format(
        #       mod.filename, mod.complexity, len(mod.methods)))


# c_f1 = ChangedFile('filename', 'a_path')
# files['a_path'] = c_f1
# c_f2 = ChangedFile('filename2', 'a_path2')
# files['a_path2'] = c_f2
#
# s_c_f = search_modified_file('filename', 'a_path')
# print(s_c_f.full_path)
# print("all", files)
#
# up = update_modified_file('filename_new', 'a_path', 'a_path_new')
# print(up.filename)
# print(up.full_path)
# print(up.old_paths)
#
# print("all", files)
# print(files['a_path_new'].filename)
# print(files['a_path_new'].old_paths)
# print(files['a_path'])