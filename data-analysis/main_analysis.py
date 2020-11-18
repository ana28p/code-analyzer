import csv
from xml.etree import ElementTree
import pandas as pd
from sklearn import preprocessing
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.ticker import StrMethodFormatter
import statsmodels.api as sm
import scipy.stats as stats
from pyclustertend import hopkins, vat, assess_tendency_by_mean_metric_score
from sklearn.preprocessing import scale, MinMaxScaler, minmax_scale, RobustScaler,robust_scale
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, accuracy_score, precision_score
from sklearn.metrics.cluster import adjusted_rand_score
from sklearn import mixture
import statistics
import seaborn as sns


metrics_list = ['LOC', 'CC', 'NP', 'NV', 'NEST', 'Ca', 'Ce', 'NChg', 'NCall']


def get_data():
    print('Read data')
    file = "C:/Users/aprodea/work/metrics-tax-compare/merged/merged_filledna.csv"
    data = pd.read_csv(file, sep=';')
    return data


# def get_columns_list_of_metrics(data):
#     list_columns = data.columns.tolist()
#     list_columns.remove('Method')
#     return list_columns


def scale_data(data):
    print('Scale data')
    scaled_data = data.copy()
    for col_name in data[metrics_list]:
        col = scaled_data[col_name]
        min_col, max_col = col.min(), col.max()
        # min_col = 0  # consider min as 0 to perserve the importance of values; eg LOC 25, 50 -> 0.5, 1
        #     print(col_name, min_col, max_col)
        scaled_data[col_name] = (col - min_col) / (max_col - min_col)

    return scaled_data


def hopkins_test(data):
    print('Calculate Hopkins test')
    return hopkins(data.loc[:, ~data.columns.isin(['Method'])], data.shape[0])


def merge_clevel_in_data(in_data, from_data):
    data_class = pd.merge(in_data, from_data[["Method", "CLevel"]], on='Method', how='left')
    return data_class


def threshold_clustering(data):
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


def get_total_mean_of_cluster(data, cluster):
    cluster = data[data['clust'] == cluster]
    cluster_means = cluster[metrics_list].mean(axis = 0)
    return cluster_means.mean()


def label_data(data, labels):
    data['clust'] = labels

    f_mean = get_total_mean_of_cluster(data, 0)
    s_mean = get_total_mean_of_cluster(data, 1)
    t_mean = get_total_mean_of_cluster(data, 2)

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


def k_means_clustering(data, rand_state):
    # print('K means clustering')
    k_means = KMeans(init="random", n_clusters=3, random_state=rand_state)  # , random_state=42)  # n_init=10, max_iter=300,
    # print(metrics_list)
    k_means.fit(data[metrics_list])

    return label_data(data, k_means.labels_)


def em_clustering(data, rand_state):
    # print('EM clustering')
    gmm = mixture.GaussianMixture(n_components=3, covariance_type='full', random_state=rand_state)
    gmm.fit(data[metrics_list])
    labels = gmm.predict(data[metrics_list])

    return label_data(data, labels)


def analysis(rand_state):
    print('Start')
    merged_data = get_data()
    scaled_data = scale_data(merged_data)

    print('Hopkins test result: ', hopkins_test(scaled_data))

    threshold_cluster_data = threshold_clustering(scaled_data)
    data_threshold_classified = merge_clevel_in_data(merged_data, threshold_cluster_data)
    # data_threshold_classified.to_csv(
    #     "C:/Users/aprodea/work/metrics-tax-compare/classification/threshold.csv", sep=';', index=False)

    k_means_cluster_data = k_means_clustering(scaled_data, rand_state=rand_state)
    data_k_means_classified = merge_clevel_in_data(merged_data, k_means_cluster_data)
    # data_k_means_classified.to_csv(
    #     "C:/Users/aprodea/work/metrics-tax-compare/classification/k_means.csv", sep=';', index=False)

    em_cluster_data = em_clustering(scaled_data, rand_state=rand_state)
    data_em_classified = merge_clevel_in_data(merged_data, em_cluster_data)
    # data_em_classified.to_csv(
    #     "C:/Users/aprodea/work/metrics-tax-compare/classification/em.csv", sep=';', index=False)

    # h_threshold_methods = data_threshold_classified[data_threshold_classified['CLevel'] == "high"]['Method'].to_numpy()
    # r_threshold_methods = data_threshold_classified[data_threshold_classified['CLevel'] == "regular"]['Method'].to_numpy()
    # l_threshold_methods = data_threshold_classified[data_threshold_classified['CLevel'] == "low"]['Method'].to_numpy()
    #
    # h_k_means_methods = data_k_means_classified[data_k_means_classified['CLevel'] == "high"]['Method'].to_numpy()
    # r_k_means_methods = data_k_means_classified[data_k_means_classified['CLevel'] == "regular"]['Method'].to_numpy()
    # l_k_means_methods = data_k_means_classified[data_k_means_classified['CLevel'] == "low"]['Method'].to_numpy()
    #
    # h_em_methods = data_em_classified[data_em_classified['CLevel'] == "high"]['Method'].to_numpy()
    # r_em_methods = data_em_classified[data_em_classified['CLevel'] == "regular"]['Method'].to_numpy()
    # l_em_methods = data_em_classified[data_em_classified['CLevel'] == "low"]['Method'].to_numpy()

    k_means_labels = data_k_means_classified[["Method", "CLevel"]]
    k_means_labels.columns = ["Method", "CLevel_k_means"]
    em_labels = data_em_classified[["Method", "CLevel"]]
    em_labels.columns = ["Method", "CLevel_em"]

    data_all_labels = pd.merge(data_threshold_classified, k_means_labels[["Method", "CLevel_k_means"]], on='Method', how='left')
    data_all_labels = pd.merge(data_all_labels, em_labels[["Method", "CLevel_em"]], on='Method', how='left')

    data_all_labels.to_csv(
        "C:/Users/aprodea/work/metrics-tax-compare/classification/all_labels.csv", sep=';', index=False)


def test_determinism_k_means(data, times, rand_state):
    adj_rand_idx = []
    for i in range(times):
        result_1 = k_means_clustering(data, rand_state)
        result_2 = k_means_clustering(data, rand_state)
        adj_rand_idx.append(adjusted_rand_score(result_1['CLevel'].tolist(), result_2['CLevel'].tolist()))
    return min(adj_rand_idx), max(adj_rand_idx), statistics.mean(adj_rand_idx)


def test_determinism_em(data, times, rand_state):
    adj_rand_idx = []
    for i in range(times):
        result_1 = em_clustering(data, rand_state)
        result_2 = em_clustering(data, rand_state)
        adj_rand_idx.append(adjusted_rand_score(result_1['CLevel'].tolist(), result_2['CLevel'].tolist()))
    return min(adj_rand_idx), max(adj_rand_idx), statistics.mean(adj_rand_idx)


def test_clustering_result():
    pass


def calculate_determinism():
    merged_data = get_data()
    scaled_data = scale_data(merged_data)
    times = 1000
    print('Calculate adjusted rand score for ', times, ' executions')
    print('--------- random state None ---------')
    print('===== k-means:')
    print('(min  max  average) ', test_determinism_k_means(scaled_data, times, None))
    print('===== EM:')
    print('(min  max  average) ', test_determinism_em(scaled_data, times, None))
    # for i in range(43):
    #     print('--------- random state {} ---------'.format(i))
    #     print('===== k-means:')
    #     print('(min  max  average) ', test_determinism_k_means(scaled_data, times, i))
    #     print('===== EM:')
    #     print('(min  max  average) ', test_determinism_em(scaled_data, times, i))


def compare_results():
    metrics_file = "C:/Users/aprodea/work/metrics-tax-compare/classification/all_labels.csv"
    metrics_labelled_data = pd.read_csv(metrics_file, sep=';')

    # test_cov_file = "C:/Users/aprodea/work/metrics-tax-compare/merged/test_coverage_org.csv"
    # test_data = pd.read_csv(test_cov_file, sep=';')
    #
    # data_combined = pd.merge(metrics_labelled_data[['Method', 'CLevel', 'CLevel_k_means', 'CLevel_em']], test_data,
    #                          on='Method', how='left')

    labels_var = ['CLevel', 'CLevel_k_means', 'CLevel_em']
    for l1 in labels_var:
        for l2 in labels_var:
            ari = adjusted_rand_score(metrics_labelled_data[l1].tolist(), metrics_labelled_data[l2].tolist())
            pr = precision_score(metrics_labelled_data[l1].tolist(), metrics_labelled_data[l2].tolist(),
                                 labels=['high', 'regular', 'low'], average=None)
            acc = accuracy_score(metrics_labelled_data[l1].tolist(), metrics_labelled_data[l2].tolist())
            print('{}  to  {}  ari: {}  precision: {}  accuracy: {}'.format(l1, l2, ari, pr, acc))


if __name__ == '__main__':
    # analysis(42)
    compare_results()
    # calculate_determinism()
