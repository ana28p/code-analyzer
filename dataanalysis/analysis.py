
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import seaborn as sns
from kneed import KneeLocator
from sklearn import mixture
from pyclustertend import hopkins

import logging

from utils import scale_data, create_qq_subplots

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class Analysis:
    def __init__(self, data, all_metrics, use_metrics, output_location):
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
        self.projected_res = None

    def create_qq_plots(self):
        if self.output_plots_location is not None:
            plt_data = create_qq_subplots(self.data, self.all_metrics)
            plt_data.savefig(self.output_plots_location + 'qqplots_unscaled.pdf', bbox_inches='tight', pad_inches=0)

            plt_scaled_data = create_qq_subplots(self.scaled_data, self.all_metrics)
            plt_scaled_data.savefig(self.output_plots_location + 'qqplots_scaled.pdf', bbox_inches='tight', pad_inches=0)

    def describe_variables(self):
        logging.info("\n" + self.data[self.all_metrics].describe().to_string())
        logging.info("Sum of LOC: " + self.data['LOC'].sum().to_string())

    def perform_correlation(self):
        p_corr = self.scaled_data[self.all_metrics].corr(method='kendall')
        logging.info("Correlation result \n" + p_corr.to_string())
        if self.output_plots_location is not None:
            fig, ax = plt.subplots(figsize=(10, 5))
            sns.heatmap(p_corr, xticklabels=p_corr.columns, yticklabels=p_corr.columns, annot=True, cmap='coolwarm', ax=ax)
            plt.savefig(self.output_plots_location + 'correlation.pdf', bbox_inches='tight', pad_inches=0)

    def principal_component_analysis(self):
        logging.info('Principal component analysis')
        X = self.data[self.all_metrics]
        X_scaled = StandardScaler().fit_transform(X)

        features = X_scaled.T
        cov_matrix = np.cov(features)

        values, vectors = np.linalg.eig(cov_matrix)

        importance = {}
        explained_variances = []
        for i in range(len(values)):
            val = values[i] / np.sum(values)
            explained_variances.append(val)
            importance[val] = self.all_metrics[i]

        logging.info('Explained variances sum {} and list {},'.format(np.sum(explained_variances), explained_variances))
        dict_keys = list(importance.keys())
        dict_keys.sort(reverse=True)
        all_in_order = ""
        for k in dict_keys:
            all_in_order += importance[k] + "  "
        logging.info('Variables in order of importance {} \n their variances {}'.format(all_in_order, dict_keys))

        projected_1 = X_scaled.dot(vectors.T[0])
        projected_2 = X_scaled.dot(vectors.T[1])
        res = pd.DataFrame(projected_1, columns=['PC1'])
        res['PC2'] = projected_2

        self.projected_res = res

    def hopkins_test(self):
        hopkins_res = hopkins(self.data[self.use_metrics], self.data.shape[0])
        logging.info('Hopkins test result ' + str(hopkins_res))

    def k_means_elbow(self):
        kmeans_kwargs = {"init": "random", "n_init": 10, "max_iter": 300, "random_state": 42}
        sse = []
        X = self.scaled_data[self.use_metrics]
        for k in range(1, 11):
            ekmeans = KMeans(n_clusters=k, **kmeans_kwargs)
            ekmeans.fit(X)
            sse.append(ekmeans.inertia_)
        kl = KneeLocator(range(1, 11), sse, curve="convex", direction="decreasing")
        logging.info('Recommended cluster number for K-means: ' + kl.elbow)

        if self.output_plots_location is not None:
            plt.plot(range(1, 11), sse, 'bx-')
            plt.xticks(range(1, 11))
            plt.xlabel("Number of Clusters")
            plt.ylabel("SSE")
            plt.savefig(self.output_plots_location + 'k_means-sse.pdf', bbox_inches='tight', pad_inches=0)

    def em_bic_aic(self):
        n_components = np.arange(1, 11)
        X = self.scaled_data[self.use_metrics].to_numpy()
        models = [mixture.GaussianMixture(n, covariance_type='full', random_state=0).fit(X)
                  for n in n_components]
        logging.info('For EM clustering, please check the plot image. The smallest values are considered the best.')

        if self.output_plots_location is not None:
            plt.plot(n_components, [m.bic(X) for m in models], 'x-', label='BIC')
            plt.plot(n_components, [m.aic(X) for m in models], 'x-', label='AIC')
            plt.xticks(range(1, 11))
            plt.legend(loc='best')
            plt.xlabel('Number of Clusters')

            plt.savefig(self.output_plots_location + 'em_bic-aic.pdf', bbox_inches='tight', pad_inches=0)

