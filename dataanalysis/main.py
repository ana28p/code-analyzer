import pandas as pd
import logging
import os
import sklearn.metrics as compute_metrics
from sklearn.metrics.cluster import adjusted_rand_score

from clustering import ThresholdClustering, KMeansClustering, EMClustering
from analysis import Analysis
from validation import Validation
from utils import plot_first_two_pca

THRESHOLD_LBL = "CLevel_threshold"
KMEANS_LBL = "CLevel_k_means"
EM_LBL = "CLevel_em"


def compare_pair(data1, data2):
    ari = adjusted_rand_score(data1, data2)
    pr = compute_metrics.precision_score(data1, data2, labels=['high', 'regular', 'low'], average=None)
    acc = compute_metrics.accuracy_score(data1, data2)
    recall = compute_metrics.recall_score(data1, data2, labels=['high', 'regular', 'low'], average=None)
    return pr, recall, ari, acc


def compare_results(data_complete, labels):
    logging.info('Comparison result between pair of classification')
    for l1 in labels:
        for l2 in labels:
            pr, recall, ari, acc = compare_pair(data_complete[l1].tolist(), data_complete[l2].tolist())
            logging.info('{}  to  {}  precision: {}, recall: {},  ari: {}, accuracy: {}'
                         .format(l1, l2, pr, recall, ari, acc))


def process_steps(data, list_of_metric_types, use_metric_types,
                  real_labels_file, changed_lines_file,
                  test_coverage_file, save_to_location, save_plots):

    logging.info('Analyse data based on variables ' + ', '.join(use_metric_types))

    analysis = Analysis(data,
                        list_of_metric_types,
                        use_metric_types,
                        save_to_location,
                        save_plots)

    analysis.create_qq_plots()
    analysis.hopkins_test()
    analysis.describe_variables()
    analysis.perform_correlation()
    analysis.correlation_changed_lines_and_metrics(changed_lines_file)
    analysis.principal_component_analysis()
    analysis.k_means_elbow()
    analysis.em_bic_aic()

    threshold_clustering = ThresholdClustering(data,
                                               list_of_metric_types,
                                               use_metric_types,
                                               save_to_location,
                                               save_plots)
    threshold_clustering.cluster(THRESHOLD_LBL)
    threshold_clustering.merge_test_coverage(test_coverage_file)
    threshold_clustering.calculate_result()
    threshold_clustering.create_plots()

    k_means_clustering = KMeansClustering(data,
                                          list_of_metric_types,
                                          use_metric_types,
                                          save_to_location,
                                          save_plots)
    k_means_clustering.cluster(KMEANS_LBL)
    k_means_clustering.merge_test_coverage(test_coverage_file)
    k_means_clustering.calculate_result()
    k_means_clustering.create_plots()

    em_clustering = EMClustering(data,
                                 list_of_metric_types,
                                 use_metric_types,
                                 save_to_location,
                                 save_plots)
    em_clustering.cluster(EM_LBL)
    em_clustering.merge_test_coverage(test_coverage_file)
    em_clustering.calculate_result()
    em_clustering.create_plots()

    data_complete = threshold_clustering.output_data[['Method'] + list_of_metric_types + [THRESHOLD_LBL]]
    data_complete = pd.merge(data_complete,
                             k_means_clustering.output_data[["Method", KMEANS_LBL]],
                             on='Method', how='left')
    data_complete = pd.merge(data_complete,
                             em_clustering.output_data[["Method", EM_LBL]],
                             on='Method', how='left')

    data_complete.to_csv(save_to_location + "complete_classification.csv", sep=';', index=False)

    labels = [THRESHOLD_LBL, KMEANS_LBL, EM_LBL]

    compare_results(data_complete, labels)

    logging.info('--------------- Validation ---------------')
    validation = Validation(data_complete, labels, save_to_location, save_plots)
    if real_labels_file is not None:
        validation.using_expert_knowledge(real_labels_file)
    validation.using_changed_lines(changed_lines_file)

    analysis_after = Analysis(data_complete,
                              list_of_metric_types,
                              use_metric_types,
                              save_to_location,
                              save_plots)
    analysis_after.principal_component_analysis()
    plot_first_two_pca(data_complete, analysis_after.projected_res,
                       labels, ['Threshold', 'K-means', 'EM'],
                       save_to_location + 'plots/')

    logging.info('==================================================')


def start_process(data_location, output_location, save_plots, use_metric_types, real_labels_file=None):
    metrics_file = data_location + "merged.csv"
    test_coverage_file = data_location + "test_coverage.csv"
    changed_lines_file = data_location + "changed_lines.csv"
    if real_labels_file is not None:
        real_labels_file = data_location + real_labels_file
    save_to_location = output_location

    list_of_metric_types = ['LOC', 'CC', 'NP', 'NV', 'NEST', 'Ca', 'Ce', 'NChg', 'NCall']

    if save_to_location is not None:
        if not os.path.exists(save_to_location):
            os.makedirs(save_to_location)

    logging.basicConfig(filename=save_to_location + 'info.log', level=logging.INFO,
                        format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    logging.info('Started')
    logging.info('Reading metrics from file ' + metrics_file)

    data = pd.read_csv(metrics_file, sep=';')

    process_steps(data,
                  list_of_metric_types,
                  use_metric_types,
                  real_labels_file,
                  changed_lines_file,
                  test_coverage_file,
                  save_to_location,
                  save_plots)

    logging.info('Finished')


if __name__ == "__main__":
    pj = "C:/Users/Anamaria/Documents/master/final_project/experiments/tax-c/"
    start_process(pj + "analysis/v111/merged/",
                  pj + "analysis/v111/classification_all/",
                  True,
                  ['LOC', 'CC', 'NP', 'NV', 'NEST', 'Ca', 'Ce', 'NChg', 'NCall'],
                  "methods_labelled.csv")
