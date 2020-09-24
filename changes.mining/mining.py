from pydriller import RepositoryMining, ModificationType
from .change import Commit, ModificationType, Modification, ChangedMethod, ChangedFile


changedMethods = []

for c in RepositoryMining('C:/Users/aprodea/work/deloitte-tax-compare/.git').traverse_commits():
    # print(commit.msg)
    commit = Commit(c.committer_date, c.committer, c.hash)

    for mod in c.modifications:
        modification = Modification(commit, mod.change_type)

        for cMet in mod.changed_methods:
            # check if method is in list
            changedMethod = ChangedMethod(cMet.name, mod.filename)
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
