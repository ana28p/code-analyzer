import csv
from xml.etree import ElementTree
import pandas as pd
from sklearn import preprocessing
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter


def get_profiler_metrics_data():
    file = "C:/Users/aprodea/work/metrics-tax-compare/profiler/report_tax.xml"
    calls_metrics = {'Methods': [], 'Calls': []}
    root = ElementTree.parse(file).getroot()
    for type_tag in root.findall('Function'):
        method = type_tag.get('FQN')
        calls = type_tag.get('Calls')
        method = method.replace(' ', '')

        calls_metrics['Methods'].append(method)
        calls_metrics['Calls'].append(calls)

    return pd.DataFrame(data=calls_metrics)


def change_method_name_commits(method):
    method = method.replace('::', '.')
    start_parameters = method.rfind('(')
    method_name = method[:start_parameters]
    parameters_text = method[start_parameters:]
    if len(parameters_text) > 2:
        # print('the text ', parameters_text)
        parameters_text = parameters_text[2:]
        parameters = parameters_text.split(', ')
        params_types = []
        for param in parameters:
            p = param.split(' ')
            check_type = p[0].rfind('<')
            if check_type > 0:
                params_types.append(p[0][0:check_type])
            else:
                params_types.append(p[0])
        # print(params_types)
        parameters_text = '(' + ','.join(params_types) + ')'

    new_name = method_name + parameters_text
    return new_name


def get_change_metrics_data():
    file = "C:/Users/aprodea/work/metrics-tax-compare/commits/commits_tax_compare.csv"
    data = pd.read_csv(file, sep=';')
    data['Method_Parsed'] = data['Method'].apply(change_method_name_commits)
    return data


def change_method_name_metrics(method):
    start_parameters = method.rfind('(')
    method_name = method[:start_parameters]
    parameters_text = method[start_parameters:]
    if len(parameters_text) > 2:
        parameters_text = parameters_text[1:-1]
        # nu merge atat de simplu pt ca pot fi: (IRepository<ChatMessage,Int64>,IChatFeatureChecker)
        # poate ar trebui sa imi creez fisierele cu nr de params, si sa ma bazez pe aia
        # doar la profiler v-a trebui sa calculez eu
        parameters = parameters_text.split(',')
        params_types = []
        for param in parameters:
            check_type = param.rfind('<')
            if check_type > 0:
                params_types.append(param[0:check_type])
            else:
                params_types.append(param)
        # print(params_types)
        parameters_text = '(' + ','.join(params_types) + ')'

    new_name = method_name + parameters_text
    return new_name


def get_code_metrics_data():
    file = "C:/Users/aprodea/work/metrics-tax-compare/ndepend/export_query.csv"
    data = pd.read_csv(file, sep=';', decimal=',')
    # data['Method_Parsed'] = data['FullName'].apply(change_method_name_metrics)
    return data


metrics_data = get_code_metrics_data()
change_data = get_change_metrics_data()
usage_data = get_profiler_metrics_data()

new_data = metrics_data[['NbLinesOfCode', 'CyclomaticComplexity', 'ILCyclomaticComplexity', 'ILNestingDepth', 'Level',
                         'PercentageComment', 'NbVariables', 'NbMethodsCalledInternal', 'NbMethodsCallingMe', 'Rank']]

# x = new_data.values #returns a numpy array
# min_max_scaler = preprocessing.MinMaxScaler()
# x_scaled = min_max_scaler.fit_transform(x)
# new_data = pd.DataFrame(x_scaled)

plt = new_data.hist()
plt.interactive(False)
plt.show()

# new_data['Changes'] = change_data['Changes']
# new_data['Calls'] = usage_data['Calls']