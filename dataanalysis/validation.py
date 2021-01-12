
import pandas as pd
import os
import seaborn as sns
import matplotlib.pyplot as plt

import logging

from utils import classification_report, scale_data

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class Validation:
    def __init__(self, data, list_labels, output_location):
        self.data = data
        self.list_labels = list_labels
        self.output_location = output_location

        if output_location is not None:
            if not os.path.exists(output_location):
                os.makedirs(output_location)

            self.output_plots_location = output_location + "plots/"
            if not os.path.exists(self.output_plots_location):
                os.makedirs(self.output_plots_location)

    def using_expert_knowledge(self, real_labels_file):
        real_labels_data = pd.read_csv(real_labels_file, sep=';')
        data_combined = pd.merge(left=real_labels_data[['Method', 'CLevel']],
                                 right=self.data[['Method'] + self.list_labels],
                                 on='Method', how='inner')

        for y_pred in self.list_labels:
            report = classification_report(data_combined['CLevel'], data_combined[y_pred])
            logging.info('------- {} ------ \n {}'.format(y_pred, report))

    def __changed_lines_validation(self, data_combined, label, title):
        custom_dict = {'low': 0, 'regular': 1, 'high': 2}
        data_section = data_combined[['Method', label, 'ChgLines']]
        sub_df1 = data_section.sort_values(by=[label], key=lambda x: x.map(custom_dict), ignore_index=True)
        sub_df1['method_idx'] = sub_df1.index

        grouped_section = data_section.groupby(label, sort=False)
        logging.info('Total sum of changed lines: ' + str(grouped_section[['ChgLines']].sum()))
        logging.info('Chg lines description per class \n' + grouped_section[['ChgLines']].describe().to_string())

        if self.output_plots_location is not None:
            fig, ax = plt.subplots(figsize=(15, 4), dpi=80)
            for label in (ax.get_xticklabels() + ax.get_yticklabels()):
                label.set_fontsize(12)
            sns.scatterplot(data=data_section, x="method_idx", y="ChgLines", hue=label,
                            palette={'low': 'blue', 'regular': '#DCB732', 'high': 'red'}, ax=ax)
            plt.legend(loc='upper left')
            plt.title(title, fontsize=14)
            plt.ylabel('Number of lines changed')
            plt.xlabel('Methods')
            plt.savefig(self.output_plots_location + 'chg-lines_' + label + '.pdf', bbox_inches='tight', pad_inches=0)

    def using_changed_lines(self, changed_lines_file):
        chg_lines_data = pd.read_csv(changed_lines_file, sep=';')
        data_combined = pd.merge(self.data, chg_lines_data[['Previous_Method_Parsed', 'ChgLines']],
                                 how='inner', left_on='Method', right_on='Previous_Method_Parsed')
        for label in self.list_labels:
            if 'thresh' in label:
                title = "Number of changed lines after performing threshold-based clustering"
            elif 'means' in label:
                title = "Number of changed lines after performing K-means clustering"
            else:
                title = "Number of changed lines after performing EM clustering"
            self.__changed_lines_validation(data_combined, label, title)

    def chglines_correlation_with_metrics(self, list_metrics):
        list_columns = list_metrics.append('ChgLines')
        scaled_df = scale_data(self.data, list_columns)

        p_corr = scaled_df[list_columns].corr(method='kendall')
        logging.info("Correlation of metrics including chg lines \n" + p_corr.to_string())
