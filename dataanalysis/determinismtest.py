import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics.cluster import adjusted_rand_score
from sklearn import mixture
import statistics
from pathlib import Path

base_path = Path(__file__).parent

metrics_file = (base_path / "sampledata/metrics.csv").resolve()
metrics_list = ['LOC', 'CC', 'NP', 'NV', 'NEST', 'Ca', 'Ce', 'NChg', 'NCall']


def get_data():
    print('Read data')
    data = pd.read_csv(metrics_file, sep=';')
    return data


def scale_data(data):
    print('Scale data')
    scaled_data = data.copy()
    for col_name in data[metrics_list]:
        col = scaled_data[col_name]
        min_col, max_col = col.min(), col.max()
        # min_col = 0  # consider min as 0 to preserve the importance of values; eg LOC 25, 50 -> 0.5, 1
        #     print(col_name, min_col, max_col)
        scaled_data[col_name] = (col - min_col) / (max_col - min_col)

    return scaled_data


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
    k_means = KMeans(init="random", n_clusters=3, random_state=rand_state)  # , random_state=42)  # n_init=10, max_iter=300,
    k_means.fit(data[metrics_list])

    return label_data(data, k_means.labels_)


def em_clustering(data, rand_state):
    gmm = mixture.GaussianMixture(n_components=3, covariance_type='full', random_state=rand_state)
    gmm.fit(data[metrics_list])
    labels = gmm.predict(data[metrics_list])

    return label_data(data, labels)


def test_determinism_k_means(data, times, rand_state):
    adj_rand_idx = []
    for i in range(times):
        result_1 = k_means_clustering(data, rand_state)
        result_2 = k_means_clustering(data, rand_state)
        ars = adjusted_rand_score(result_1['CLevel'].tolist(), result_2['CLevel'].tolist())
        adj_rand_idx.append(ars)
    return min(adj_rand_idx), max(adj_rand_idx), statistics.mean(adj_rand_idx)


def test_determinism_em(data, times, rand_state):
    adj_rand_idx = []
    for i in range(times):
        result_1 = em_clustering(data, rand_state)
        result_2 = em_clustering(data, rand_state)
        adj_rand_idx.append(adjusted_rand_score(result_1['CLevel'].tolist(), result_2['CLevel'].tolist()))
    return min(adj_rand_idx), max(adj_rand_idx), statistics.mean(adj_rand_idx)


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


if __name__ == '__main__':
    calculate_determinism()
