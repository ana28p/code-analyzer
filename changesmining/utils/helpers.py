import csv


def split_method_long_name(long_name: str) -> (str, str):
    start_of_name = long_name.rfind('::')
    if start_of_name < 0:
        print('Invalid method name ', long_name)
        return '', long_name
    start_of_name += 2  # add length of separator
    return long_name[start_of_name:], long_name[:start_of_name]


def print_actual_files(files):
    for key, v_f in files.items():
        print('ooooooooooo', key)
        print(v_f.filename, v_f.full_path)
        for mp in v_f.methods:
            print(mp.class_path + mp.name, ' nr of commits: ', len(mp.commits),
                  'nr of chg lines: ', sum([c.changed_lines for c in mp.commits]))


def write_to_csv(files, file_path: str, include_prev_name: bool = False):
    with open(file_path, 'w') as csvfile:
        fieldnames = ['Full_path', 'Filename', 'Method', 'Changes', 'ChgLines']
        if include_prev_name:
            fieldnames.append('Previous_name')
        file_writer = csv.DictWriter(csvfile, fieldnames, delimiter=';', lineterminator='\n')
        file_writer.writeheader()
        for key, v_f in files.items():
            for mp in v_f.methods:
                method_full_name = (mp.class_path + mp.name)
                chg_lines = sum([c.changed_lines for c in mp.commits])
                if include_prev_name:
                    file_writer.writerow({
                        'Full_path': v_f.full_path,
                        'Filename': v_f.filename,
                        'Method': method_full_name,
                        'Changes': len(mp.commits),
                        'ChgLines': chg_lines,
                        'Previous_name': mp.previous_long_name
                    })
                else:
                    file_writer.writerow({
                        'Full_path': v_f.full_path,
                        'Filename': v_f.filename,
                        'Method': method_full_name,
                        'Changes': len(mp.commits),
                        'ChgLines': chg_lines
                    })


def write_to_cvs_trash(trash_methods, file_path):
    with open(file_path, 'w') as csvfile:
        fieldnames = ['Commit_hash', 'Date', 'Method', 'Changes', 'ChgLines']
        file_writer = csv.DictWriter(csvfile, fieldnames, delimiter=';', lineterminator='\n')
        file_writer.writeheader()
        for commit, methods in trash_methods.items():
            flat_list = [item for sublist in methods for item in sublist]
            for mp in flat_list:
                method_full_name = (mp.class_path + mp.name)
                chg_lines = sum([c.changed_lines for c in mp.commits])
                file_writer.writerow({
                    'Commit_hash': commit.commit_hash,
                    'Date': commit.date,
                    'Method': method_full_name,
                    'Changes': len(mp.commits),
                    'ChgLines': chg_lines
                })
