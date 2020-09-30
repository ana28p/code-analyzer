from difflib import SequenceMatcher


def update_met(ch, curr, old):
    obs = [val for val in ch if val not in curr]
    print('removed or renamed: ', obs)
    new_m = [val for val in ch if val not in old]
    print('new: ', new_m)
    up = [val for val in ch if (val in old) and (val in curr)]
    print('updated: ', up)

    if len(obs) > 0:  # removed or renamed
        if len(new_m) == 0:
            print('remove all obs: ', obs)
        else:
            updated_obs = []
            for e in obs:
                max_sim = ['', '', 0]
                for n in new_m:
                    sim = SequenceMatcher(None, e, n).ratio()
                    # print('similarity: ', e, n, sim)
                    # print('current max: ', max_sim, 'las val: ', max_sim[2])
                    if sim > max_sim[2]:
                        max_sim = [e, n, sim]
                if max_sim[2] >= 0.75:
                    print('update ', max_sim[0], ' with ', max_sim[1])
                    new_m.remove(max_sim[1])
                    updated_obs.append(max_sim[0])
            if len(updated_obs) != len(obs):
                to_remove = [val for val in obs if val not in updated_obs]
                print('to remove: ', to_remove)
    if len(new_m) > 0:
        print('add as new remaining elements: ', new_m)
    if len(up) > 0:
        print('increase count or add: ', up)


# add, sutract, division, pow, add2, subtract

ch1 = ['add', 'sutract', 'add2', 'subtract', 'pow']
curr1 = ['add2', 'subtract', 'division', 'pow']
old1 = ['add', 'sutract', 'division']


print('--------rename, add---------')
update_met(ch1, curr1, old1)
print('--------delete---------')
update_met(['add', 'subtract'], ['division', 'pow'], ['add', 'subtract', 'division', 'pow'])  # just delete
print('---------add---------')
update_met(['add', 'subtract'], ['add', 'subtract', 'division', 'pow'], ['division', 'pow'])  # just add
print('---------update--------')
update_met(['add', 'subtract'], ['add', 'subtract', 'division', 'pow'], ['add', 'subtract', 'division', 'pow'])  # just update
print('--------del, rename, update-------')
update_met(['add', 'subtract', 'pow', 'power', 'sutract', 'division'],
           ['subtract', 'division', 'power'],
           ['add', 'sutract', 'division', 'pow'])  # del, rename, update
