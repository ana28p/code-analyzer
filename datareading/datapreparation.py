"""Data preparation steps.

These scripts read the reports from data collection, transforms the method signatures
and save the files (depending on a flag) after the transformation, and as a merged data-set.

All the files are saved in CSV format, using ';' as separator.
"""

import pandas as pd
import numpy as np
import os

from transformscripts import change_method_name_metrics, ctor_to_class_name, change_method_name_commits, \
    get_profiler_metrics_data, collect_test_coverage_data, change_name_coverage, remove_generics

# Resource path locations

PROJECT_LOCATION = "C:/Users/Anamaria/Documents/master/final_project/experiments/tax-c/"

SOURCE_CODE_METRICS_FILE = PROJECT_LOCATION + "init_reports/ndepend_v111.csv"
REPO_MINING_FILE = PROJECT_LOCATION + "init_reports/commits-to-1.1.1_june_2017.csv"
USAGE_DATA_FOLDER = PROJECT_LOCATION + "init_reports/usage"

REPO_MINING_FILE_FOR_CHGLINES = PROJECT_LOCATION + "init_reports/commits-from-1.1.1_june_2017.csv"

TEST_COVERAGE_FILE = PROJECT_LOCATION + "init_reports/test_coverage_v111.xml"

SAVE_TO_FOLDER = PROJECT_LOCATION + "analysis/v111/merged/"


# --------- Source code metrics report --------- #


def prepare_source_code_metrics():
    """Reads the source code metrics report, applies the transformation on the method name
    and filters the out of scope methods"""

    metrics_data = pd.read_csv(SOURCE_CODE_METRICS_FILE, sep=';', decimal=',')
    metrics_data['FullName'] = metrics_data['FullName'].apply(change_method_name_metrics)

    metrics_data["NbLinesOfCode"].replace({0: np.nan}, inplace=True)

    no_getters = metrics_data['IsPropertyGetter'] == False
    no_setters = metrics_data['IsPropertySetter'] == False
    no_operators = metrics_data['IsOperator'] == False
    no_empty_method = metrics_data['NbLinesOfCode'].notna()
    annonymous = metrics_data['FullName'].str.contains("f__AnonymousType")
    migrations = metrics_data['FullName'].str.contains(".Migrations.")

    filtered_metrics_data = metrics_data.copy()
    filtered_metrics_data = filtered_metrics_data[no_setters & no_getters & no_operators & no_empty_method & ~annonymous & ~migrations].reset_index()

    sc_metrics_data = filtered_metrics_data[["FullName", "NbLinesOfCode", "CyclomaticComplexity", "NbParameters", "NbVariables",
                                             "ILNestingDepth", "NbMethodsCallingMe", "NbMethodsCalledInternal"]].copy()
    sc_metrics_data.columns = ["Method", "LOC", "CC", "NP", "NV", "NEST", "Ca", "Ce"]

    # Constructors are listed as 'ctor' or 'cctor',
    # replace these with the class name (the actual name of the constructor)
    sc_metrics_data['Method'] = sc_metrics_data['Method'].apply(ctor_to_class_name)

    # ..ctor and ..cctor might result in the same method;
    # however the source doesn't have all the constructors find by the Ndepend
    sc_metrics_data.drop_duplicates(subset=['Method'], inplace=True, ignore_index=True)

    return sc_metrics_data


# --------- Repository mining metrics report --------- #

def get_change_metrics(file):
    """Reads and modifies the repository mining report"""
    data = pd.read_csv(file, sep=';')
    data['Method_Parsed'] = data['Method'].apply(change_method_name_commits)
    return data


def prepare_change_metrics():
    """Change metrics report preparation"""
    return get_change_metrics(REPO_MINING_FILE)


def prepare_changed_lines_data():
    """Change metrics report preparation for validation"""
    if REPO_MINING_FILE_FOR_CHGLINES is not None:
        data = get_change_metrics(REPO_MINING_FILE_FOR_CHGLINES)
        data['Previous_Method_Parsed'] = data['Previous_name'].apply(change_method_name_commits)
        data = data[['Method_Parsed', 'Previous_Method_Parsed', 'ChgLines']]

        return data

    return None


# --------- Profiler metrics report --------- #

def get_all_profiler_metrics_data(folder):
    """Reads all the XML file from the provided folder and creates a single data frame with the calls number summed"""
    calls_dfs = []
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.is_file() and entry.name.endswith('.xml'):
                full_path = os.path.join(folder, entry.name)
                calls_dfs.append(get_profiler_metrics_data(full_path))
    df = pd.concat(calls_dfs)
    df = df.groupby('Method')['Calls'].sum().reset_index()
    return df


def prepare_usage_metrics():
    """Usage metrics report preparation"""
    data = get_all_profiler_metrics_data(USAGE_DATA_FOLDER)
    data['Method'] = data['Method'].apply(ctor_to_class_name)
    return data


# --------- Test coverage report --------- #

def prepare_test_coverage():
    """Test coverage report preparation"""
    if TEST_COVERAGE_FILE is not None:
        data = collect_test_coverage_data(TEST_COVERAGE_FILE)
        data['Method'] = data['Method'].apply(change_name_coverage)
        return data

    return None


# --------- Merging and saving reports --------- #

if __name__ == "__main__":
    sc_metrics_data = prepare_source_code_metrics()
    change_data = prepare_change_metrics()
    usage_data = prepare_usage_metrics()

    chg_lines_data = prepare_changed_lines_data()
    test_coverage_data = prepare_test_coverage()

    # Save the reports
    save = True

    if save:
        if not os.path.exists(SAVE_TO_FOLDER):
            os.makedirs(SAVE_TO_FOLDER)

        sc_metrics_data.to_csv(SAVE_TO_FOLDER + "source_code_metrics.csv", sep=';', index=False)
        change_data.to_csv(SAVE_TO_FOLDER + "change_metrics.csv", sep=';', index=False)
        usage_data.to_csv(SAVE_TO_FOLDER + "usage_metrics.csv", sep=';', index=False)

        if chg_lines_data is not None:
            chg_lines_data.to_csv(SAVE_TO_FOLDER + "changed_lines.csv", sep=';', index=False)

        if test_coverage_data is not None:
            test_coverage_data.to_csv(SAVE_TO_FOLDER + "test_coverage.csv", sep=';', index=False)

    # Select the required variables from change metrics report
    sub_change_data = change_data[['Method_Parsed', 'Changes']]
    sub_change_data.columns = ['Method', 'NChg']
    sub_change_data = sub_change_data.groupby('Method')['NChg'].sum().reset_index()

    # Merge change data to source code metrics data
    merged = pd.merge(left=sc_metrics_data, right=sub_change_data, how='left', on='Method')

    # Remove the generic types of the parameters
    merged['Method_Parsed'] = merged['Method'].apply(remove_generics)

    # Select the required variables from usage metrics report
    sub_usage_data = usage_data[['Method', 'Calls']]
    sub_usage_data.columns = ['Method_calls', 'NCall']
    sub_usage_data = sub_usage_data.groupby('Method_calls')['NCall'].sum().reset_index()

    # Merge usage data
    merged = pd.merge(left=merged, right=sub_usage_data,
                      how='left', left_on='Method_Parsed', right_on='Method_calls')

    # Remove the extra columns
    merged.drop(['Method_Parsed', 'Method_calls'], axis=1, inplace=True)

    if save:
        merged.to_csv(SAVE_TO_FOLDER + "merged_init.csv", sep=';', index=False)

    merged['NChg'].fillna(1, inplace=True)
    merged['NCall'].fillna(0, inplace=True)

    if save:
        merged.to_csv(SAVE_TO_FOLDER + "merged.csv", sep=';', index=False)
