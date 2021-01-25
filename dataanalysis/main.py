"""
The main file to perform metrics analysis on the given data set.

Providing a folder location the necessarily files are:
 / "metrics.csv"  -> the file contains the metrics for each method
 / "test_coverage.csv"  -> the test coverage for each method
 / "changed_lines.csv"  -> the number of changed lines for the validation part

The analysis creates an output folder with a log file and the resulting analysis artifacts.

"""

import pandas as pd
import logging
import os
from pathlib import Path
import sklearn.metrics as compute_metrics
from sklearn.metrics.cluster import adjusted_rand_score

from clustering import ThresholdClustering, KMeansClustering, EMClustering
from analysis import Analysis
from validation import Validation
from utils import plot_first_two_pca

base_path = Path(__file__).parent

THRESHOLD_LBL = "CLevel_threshold"
KMEANS_LBL = "CLevel_k_means"
EM_LBL = "CLevel_em"


def compare_pair(data1, data2):
    """
    Creates result report for two given classification labels, where the first is considered truth.
    """
    ari = adjusted_rand_score(data1, data2)
    pr = compute_metrics.precision_score(data1, data2, labels=['high', 'regular', 'low'], average=None)
    acc = compute_metrics.accuracy_score(data1, data2)
    recall = compute_metrics.recall_score(data1, data2, labels=['high', 'regular', 'low'], average=None)
    return pr, recall, ari, acc


def compare_results(data_complete, labels):
    """
    Compares the result of a classification for each pair of levels. The first level being considered truth.
    high with regular, high with low, regular with low, etc
    """
    logging.info('Comparison result between pair of classification')
    for l1 in labels:
        for l2 in labels:
            pr, recall, ari, acc = compare_pair(data_complete[l1].tolist(), data_complete[l2].tolist())
            logging.info('{}  to  {}  precision: {}, recall: {},  ari: {}, accuracy: {}'
                         .format(l1, l2, pr, recall, ari, acc))


def process_steps(data, list_of_metric_types, use_metric_types,
                  real_labels_file, changed_lines_file,
                  test_coverage_file, save_to_location, save_plots):
    """
    Process steps for all types of clustering approaches
    """

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

    data_complete.to_csv(save_to_location / "complete_classification.csv", sep=';', index=False)

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
                       save_to_location / 'plots/')

    logging.info('==================================================')

    return data_complete


def start_process(data_location, output_location, save_plots, use_metric_types, real_labels_file=None):
    """
    Starts the process by reading the required files and initializing the process
    """
    metrics_file = data_location / "metrics.csv"
    test_coverage_file = data_location / "test_coverage.csv"
    changed_lines_file = data_location / "changed_lines.csv"
    if real_labels_file is not None:
        real_labels_file = data_location + real_labels_file
    save_to_location = output_location

    list_of_metric_types = ['LOC', 'CC', 'NP', 'NV', 'NEST', 'Ca', 'Ce', 'NChg', 'NCall']

    if save_to_location is not None:
        if not os.path.exists(save_to_location):
            os.makedirs(save_to_location)

    logging.info('Reading metrics from file ' + str(metrics_file))

    data = pd.read_csv(metrics_file, sep=';')

    data_complete = process_steps(data,
                                  list_of_metric_types,
                                  use_metric_types,
                                  real_labels_file,
                                  changed_lines_file,
                                  test_coverage_file,
                                  save_to_location,
                                  save_plots)

    return data_complete


def execute_process_for(resources_location, output_location, save_plots, real_labels_filename=None):
    """
    Executes the analysis process on multiple sets of metrics,
    then compares between the results using all metrics and the results using reduced list of metrics.
    """
    logging.info('Started')
    data_classified_all = start_process(resources_location,
                                        output_location / "classification_all/",
                                        save_plots,
                                        ['LOC', 'CC', 'NP', 'NV', 'NEST', 'Ca', 'Ce', 'NChg', 'NCall'],
                                        real_labels_filename)
    logging.info('\n\n')
    data_classified_no_call = start_process(resources_location,
                                            output_location / "classification_no_call/",
                                            save_plots,
                                            ['LOC', 'CC', 'NP', 'NV', 'NEST', 'Ca', 'Ce', 'NChg'],
                                            real_labels_filename)
    logging.info('\n\n')
    data_classified_reduced = start_process(resources_location,
                                            output_location / "classification_reduced/",
                                            save_plots,
                                            ['LOC', 'NP', 'Ca', 'Ce', 'NChg'],
                                            real_labels_filename)

    logging.info('Comparison result between pair of classification between all and reduced')
    labels = [THRESHOLD_LBL, KMEANS_LBL, EM_LBL]
    for lbl in labels:
        pr, recall, ari, acc = compare_pair(data_classified_all[lbl].tolist(), data_classified_reduced[lbl].tolist())
        logging.info('{}  to  {}  precision: {}, recall: {},  ari: {}, accuracy: {}'.format(lbl, lbl, pr, recall, ari, acc))
    logging.info('Comparison result between pair of classification between all and no call')
    for lbl in labels:
        pr, recall, ari, acc = compare_pair(data_classified_all[lbl].tolist(), data_classified_no_call[lbl].tolist())
        logging.info('{}  to  {}  precision: {}, recall: {},  ari: {}, accuracy: {}'.format(lbl, lbl, pr, recall, ari, acc))

    logging.info('Finished')


if __name__ == "__main__":
    output_dir = (base_path / "output/").resolve()
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    logging.basicConfig(filename=(base_path / "output/info.log"),
                        level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

    logging.info("\n>>>>>>>>>>>>>>>>>>>>>>>>>>>> Sharex <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
    execute_process_for(resources_location=(base_path / "sampledata/"),
                        output_location=(base_path / "output/"),
                        save_plots=True)
