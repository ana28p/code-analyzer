"""Helper methods"""

import statsmodels.api as sm
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics.cluster import adjusted_rand_score
import sklearn.metrics as compute_metrics


def scale_data(data, metrics_list):
    scaled_data = data.copy()
    for col_name in data[metrics_list]:
        col = scaled_data[col_name]
        min_col, max_col = col.min(), col.max()
        # min_col = 0  # consider min as 0 to preserve the importance of values; eg LOC 25, 50 -> 0.5, 1
        scaled_data[col_name] = (col - min_col) / (max_col - min_col)

    return scaled_data


def get_total_mean_of_cluster(data, variables, cluster):
    cluster = data[data['clust'] == cluster]
    cluster_means = cluster[variables].mean(axis=0)
    return cluster_means.mean()


def label_data(data, using_variables, cluster_classification):
    data['clust'] = cluster_classification

    f_mean = get_total_mean_of_cluster(data, using_variables, 0)
    s_mean = get_total_mean_of_cluster(data, using_variables, 1)
    t_mean = get_total_mean_of_cluster(data, using_variables, 2)

    means_dict = {f_mean: 0, s_mean: 1, t_mean: 2}
    means_list = [k for k in means_dict.keys()]
    means_list.sort()

    def to_string_label(value):
        if value == means_dict[means_list[0]]:
            return "low"
        elif value == means_dict[means_list[1]]:
            return "regular"
        if value == means_dict[means_list[2]]:
            return "high"

    data['CLevel'] = data['clust'].apply(to_string_label)
    return data.drop(['clust'], axis=1)


def print_cm(cm, labels):
    """pretty print for confusion matrixes"""
    res = []
    column_width = 10
    # Print header
    header = " " * column_width
    for label in labels:
        header += "%{0}s".format(column_width) % label
    res.append(header)
    print(header)
    # Print rows
    for i, label1 in enumerate(labels):
        row_text = "%{0}s".format(column_width) % label1
        for j in range(len(labels)):
            cell = "%{0}.1f".format(column_width) % cm[i, j]
            row_text += cell
        res.append(row_text)
        print(row_text)
    return res


def classification_report(real, predicted):
    res = []
    labels = ['high', 'regular', 'low']
    ari = adjusted_rand_score(labels_true=real, labels_pred=predicted)
    acc = compute_metrics.accuracy_score(y_true=real, y_pred=predicted)
    report = compute_metrics.classification_report(y_true=real, y_pred=predicted, labels=labels)
    conf_matrix = compute_metrics.confusion_matrix(y_true=real, y_pred=predicted, labels=labels)
    print('ARI ', ari)
    print('Accuracy ', acc)
    print(report)
    print('Confusion matrix')
    cm_res = print_cm(conf_matrix, labels)
    res.append('ARI ' + ari)
    res.append('Accuracy ' + acc)
    res.append(report)
    res.append('Confusion matrix')

    return '\n'.join(res + cm_res)


# ----------------- Visualisations ----------------- #

def create_qq_subplots(data, variables):
    fig, axes = plt.subplots(nrows=3, ncols=3, figsize=(20, 15))
    ax = axes.flatten()
    for i in range(len(variables)):
        for label in (ax[i].get_xticklabels() + ax[i].get_yticklabels()):
            label.set_fontsize(12)
        col_name = variables[i]
        sm.qqplot(data[col_name], marker='o', markerfacecolor='none', markeredgecolor='k', alpha=0.5, ax=ax[i])
        ax[i].set_ylabel(col_name, fontsize=18)
        ax[i].set_xlabel("Theoretical Quantiles", fontsize=14)
    return plt


def plot_first_two_pca(data, projected_data_result, list_labels, list_titles, save_location):
    fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(18, 5))
    ax = axes.flatten()
    title_append = ['(a)', '(b)', '(c)']
    for i in range(3):
        lvl = list_labels[i]
        sns.scatterplot(x=projected_data_result['PC1'], y=projected_data_result['PC2'], hue=data[lvl],
                        palette={'low': 'blue', 'regular': '#DCB732', 'high': 'red'},
                        hue_order=["high", "regular", "low"], s=20, ax=ax[i])
        ax[i].legend(loc="lower left", title=list_titles[i])
        ax[i].title.set_text(title_append[i] + ' ' + list_titles[i])
        ax[i].title.set_fontsize(16)

    plt.savefig(save_location + 'pca.pdf', bbox_inches='tight', pad_inches=0)
