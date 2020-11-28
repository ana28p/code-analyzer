import pandas as pd


def scale_data(data, metrics_list):
    print('Scale data')
    scaled_data = data.copy()
    for col_name in data[metrics_list]:
        col = scaled_data[col_name]
        min_col, max_col = col.min(), col.max()
        # min_col = 0  # consider min as 0 to preserve the importance of values; eg LOC 25, 50 -> 0.5, 1
        #     print(col_name, min_col, max_col)
        scaled_data[col_name] = (col - min_col) / (max_col - min_col)

    return scaled_data


def split_at_last_point(s):
    idx = s.rfind('.')
    return s[:idx], s[idx+1:]


def split_method_name(value):
    parent, method_name = split_at_last_point(value)
    parent, class_name = split_at_last_point(parent)
    return pd.Series([parent, class_name, method_name])


def get_tree_map_data(data, name):
    data[['Parent_class', 'Class', 'Method']] = data[name].apply(split_method_name)
    return data
