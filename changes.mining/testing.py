from pathlib import Path
from difflib import SequenceMatcher

from pydriller import RepositoryMining

# d29780c984d3a034ee2e3e4ad82aad2de5153782 - commit for the parameter types change
for c in RepositoryMining('https://github.com/ana28p/testing-with-csharp.git',
                          single='468e305ac3c8bc10bde80d0b1357fa7f78b03410').traverse_commits():
    print('----------------------------------')
    print(c.committer.name, c.committer_date, '|| msg: ', c.msg, c.hash)
    for m in c.modifications:
        ch_mets = [val.long_name for val in m.changed_methods]
        curr_mets = [val.long_name for val in m.methods]
        not_ex_mets = [x for x in ch_mets not in curr_mets]
        if len(not_ex_mets) > 0:
            print('removed or renamed', not_ex_mets)
            newm = [x for x in ch_mets not in not_ex_mets]
            for nm in not_ex_mets:
                for cm in newm:
                    print(nm, cm, ' similarity', SequenceMatcher(None, nm, cm).ratio())

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