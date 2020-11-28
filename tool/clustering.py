from enum import Enum

import pandas as pd
from sklearn.cluster import KMeans
from sklearn import mixture

from helpers import scale_data


class ClusteringType(Enum):
    THRESHOLD = 1
    K_MEANS = 2
    EM = 3


def merge_clevel_in_data(in_data, from_data):
    data_class = pd.merge(in_data, from_data[["Method", "CLevel"]], on='Method', how='left')
    return data_class


def threshold_clustering(data, metrics_list):
    print('Threshold clustering')
    data["CRank"] = data.sum(axis=1)
    # min_col, max_col = data["CRank"].min(), data["CRank"].max()
    ordered_data = data.sort_values(by='CRank', ignore_index=True)
    n = ordered_data.shape[0]
    first_cut = round(n * 0.7)
    second_cut = round(n * 0.9)

    ordered_data.loc[:first_cut, "CLevel"] = "low"
    ordered_data.loc[first_cut:second_cut, "CLevel"] = "regular"
    ordered_data.loc[second_cut:, "CLevel"] = "high"

    return ordered_data


def get_total_mean_of_cluster(data, metrics_list, cluster):
    cluster = data[data['clust'] == cluster]
    cluster_means = cluster[metrics_list].mean(axis = 0)
    return cluster_means.mean()


def label_data(data, metrics_list, labels):
    data['clust'] = labels

    f_mean = get_total_mean_of_cluster(data, metrics_list, 0)
    s_mean = get_total_mean_of_cluster(data, metrics_list, 1)
    t_mean = get_total_mean_of_cluster(data, metrics_list, 2)

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
    data = data.drop(['clust'], axis=1)
    return data


def k_means_clustering(data, metrics_list, rand_state):
    # print('K means clustering')
    k_means = KMeans(init="random", n_clusters=3, random_state=rand_state)  # , random_state=42)  # n_init=10, max_iter=300,
    # print(metrics_list)
    k_means.fit(data[metrics_list])

    return label_data(data, metrics_list, k_means.labels_)


def em_clustering(data, metrics_list, rand_state):
    # print('EM clustering')
    gmm = mixture.GaussianMixture(n_components=3, covariance_type='full', random_state=rand_state)
    gmm.fit(data[metrics_list])
    labels = gmm.predict(data[metrics_list])

    return label_data(data, metrics_list, labels)


def analysis(data, selected_metrics, clustering_type):
    scaled_data = scale_data(data, selected_metrics)
    data_classified = None

    rand_state = 42

    if clustering_type == ClusteringType.THRESHOLD:
        threshold_cluster_data = threshold_clustering(scaled_data, selected_metrics)
        data_classified = merge_clevel_in_data(data, threshold_cluster_data)
    elif clustering_type == ClusteringType.K_MEANS:
        k_means_cluster_data = k_means_clustering(scaled_data, selected_metrics, rand_state=rand_state)
        data_classified = merge_clevel_in_data(data, k_means_cluster_data)
    elif clustering_type == ClusteringType.EM:
        em_cluster_data = em_clustering(scaled_data, selected_metrics, rand_state=rand_state)
        data_classified = merge_clevel_in_data(data, em_cluster_data)

    return data_classified
