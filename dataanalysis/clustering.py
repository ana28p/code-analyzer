import pandas as pd
import os
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn import mixture
import seaborn as sns

import logging
import time

from abc import ABC, abstractmethod
from utils import scale_data, label_data

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class Clustering(ABC):
    def __init__(self, alg_type, data, all_metrics, use_metrics, output_location):
        self.alg_type = alg_type
        self.data = data
        self.all_metrics = all_metrics
        self.use_metrics = use_metrics
        self.output_location = output_location

        if output_location is not None:
            if not os.path.exists(output_location):
                os.makedirs(output_location)

            self.output_plots_location = output_location + "plots/"
            if not os.path.exists(self.output_plots_location):
                os.makedirs(self.output_plots_location)

        self.scaled_data = scale_data(data, all_metrics)

        self.output_data = None
        self.output_scaled_data = None
        self.clustering_column_name = None

    @abstractmethod
    def cluster(self, column_name):
        self.clustering_column_name = column_name

    def merge_test_coverage(self, file):
        if self.output_data is None:
            raise ValueError("Execute first the clustering method")

        test_data = pd.read_csv(file, sep=';')
        self.output_data = pd.merge(self.output_data, test_data, on='Method', how='left')

    def calculate_result(self):
        if self.output_data is None:
            raise ValueError("Execute first the clustering method")

        df = self.output_data
        low = df[df[self.clustering_column_name] == "low"]
        regular = df[df[self.clustering_column_name] == "regular"]
        high = df[df[self.clustering_column_name] == "high"]

        l_p, r_p, h_p = 0, 0, 0
        if 'TotalStatements' in df.columns.tolist() and 'CoveredStatements' in df.columns.tolist():
            if df['TotalStatements'].sum() > 0:
                l_p = low['CoveredStatements'].sum()/low['TotalStatements'].sum()
                r_p = regular['CoveredStatements'].sum()/regular['TotalStatements'].sum()
                h_p = high['CoveredStatements'].sum()/high['TotalStatements'].sum()

        logging.info("Clustering results for " + self.alg_type)

        coverage_percentage = 'Test coverage percentage High: {}  Regular: {}  Low: {}'.format(h_p, r_p, l_p)
        logging.info(coverage_percentage)

        methods_nr = 'Methods number High: {}  Regular: {}  Low: {}'.format(high.shape[0], regular.shape[0], low.shape[0])
        logging.info(methods_nr)

        logging.info('Clusters statistics')
        logging.info('High\n' + high.describe().to_string())
        logging.info('Regular\n' + regular.describe().to_string())
        logging.info('Low\n' + low.describe().to_string())

    def create_plots(self):
        if self.output_scaled_data is None:
            raise ValueError("Execute first the clustering method")

        df = self.output_scaled_data.copy()
        df = pd.melt(df, id_vars=self.clustering_column_name, value_vars=self.all_metrics)

        fig, ax = plt.subplots(figsize=(15, 7), dpi=80)
        sns.stripplot(data=df, x='variable', y='value', hue=self.clustering_column_name,
                      palette={'low': 'blue', 'regular': '#DCB732', 'high': 'red'},
                      hue_order=["low", "regular", "high"],
                      jitter=0.25, size=5, ax=ax, linewidth=.3, dodge=True)
        plt.xlabel('')
        plt.ylabel('')
        plt.savefig(self.output_plots_location + self.alg_type + '.pdf', bbox_inches='tight', pad_inches=0)


class ThresholdClustering(Clustering):
    def __init__(self, data, all_metrics, use_metrics, output_location=None):
        super().__init__("threshold", data, all_metrics, use_metrics, output_location)

    def __threshold_clustering(self):
        data = self.scaled_data.copy()
        data["CRank"] = self.scaled_data[self.use_metrics].sum(axis=1)

        ordered_data = data.sort_values(by='CRank', ignore_index=True)
        n = ordered_data.shape[0]
        first_cut = round(n * 0.7)
        second_cut = round(n * 0.9)

        ordered_data.loc[second_cut:, self.clustering_column_name] = "high"
        ordered_data.loc[first_cut:second_cut, self.clustering_column_name] = "regular"
        ordered_data.loc[:first_cut, self.clustering_column_name] = "low"

        return ordered_data

    def __c_rank_statistics(self, data):
        temp_df = data[["CRank", self.clustering_column_name]]
        logging.info(temp_df.describe())
        grouped_temp_df = temp_df.groupby(self.clustering_column_name, sort=False)
        logging.info(grouped_temp_df.describe())

    def cluster(self, column_name):
        super().cluster(column_name)

        logging.info("Perform threshold clustering")

        start_time = time.time()
        cl_result = self.__threshold_clustering()
        data_classified = pd.merge(self.data, cl_result[["Method", column_name]], on='Method', how='left')
        text = 'Ended threshold classification in {:.3f} seconds'.format(time.time() - start_time)
        logging.info(text)

        if self.output_location is not None:
            data_classified.to_csv(self.output_location + "threshold_result.csv", sep=';', index=False)

        self.__c_rank_statistics(cl_result)

        # Remove the extra column
        cl_result.drop(['CRank'], axis=1, inplace=True)

        self.output_data = data_classified
        self.output_scaled_data = cl_result


class KMeansClustering(Clustering):
    def __init__(self, data, all_metrics, use_metrics, output_location=None):
        super().__init__("k-means", data, all_metrics, use_metrics, output_location)

    def cluster(self, column_name):
        super().cluster(column_name)
        logging.info("K-means clustering")

        start_time = time.time()

        k_means = KMeans(init="random", n_clusters=3, random_state=42)
        k_means.fit(self.scaled_data[self.use_metrics])

        cl_result = label_data(self.scaled_data, self.use_metrics, k_means.labels_)
        text = 'Ended k-means classification in {:.3f} seconds'.format(time.time() - start_time)
        logging.info(text)

        data_classified = pd.merge(self.data, cl_result[["Method", column_name]], on='Method', how='left')
        if self.output_location is not None:
            data_classified.to_csv(self.output_location + "kmeans_result.csv", sep=';', index=False)

        self.output_data = data_classified
        self.output_scaled_data = cl_result


class EMClustering(Clustering):
    def __init__(self, data, all_metrics, use_metrics, output_location=None):
        super().__init__("em", data, all_metrics, use_metrics, output_location)

    def cluster(self, column_name):
        super().cluster(column_name)

        logging.info("EM clustering")

        start_time = time.time()

        gmm = mixture.GaussianMixture(n_components=3, covariance_type='full', random_state=42)
        gmm.fit(self.scaled_data[self.use_metrics])
        labels = gmm.predict(self.scaled_data[self.use_metrics])

        cl_result = label_data(self.scaled_data, self.use_metrics, labels)
        text = 'Ended EM classification in {:.3f} seconds'.format(time.time() - start_time)
        logging.info(text)

        data_classified = pd.merge(self.data, cl_result[["Method", column_name]], on='Method', how='left')
        if self.output_location is not None:
            data_classified.to_csv(self.output_location + "em_result.csv", sep=';', index=False)

        self.output_data = data_classified
        self.output_scaled_data = cl_result
