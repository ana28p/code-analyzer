""" Scripts to modify the method signatures from the data collection reports. """

from xml.etree import ElementTree
import pandas as pd
import numpy as np

""" Dictionary for type transformation """
type_dict = {'byte': 'Byte', 'sbyte': 'SByte', 'int': 'Int32', 'uint': 'UInt32', 'short': 'Int16', 'ushort': 'UInt16',
             'long': 'Int64', 'ulong': 'UInt64', 'float': 'Single', 'double': 'Double', 'char': 'Char',
             'bool': 'Boolean', 'object': 'Object', 'string': 'String', 'decimal': 'Decimal', 'dynamic': 'Object'}


def get_type_outbox(param_type):
    if param_type in type_dict:
        return type_dict[param_type]
    return param_type


def handle_token(token, remove_parentclass, replace_type):
    if remove_parentclass:
        token = token[token.rfind(".") + 1:]
    if replace_type:
        token = get_type_outbox(token)
    return token


def replace_by_token(param_type, remove_parentclass, replace_type):
    delims = "<>,[]()"
    token = ''
    new_param_type = ''
    for i in range(len(param_type)):
        if param_type[i] in delims:
            replace = handle_token(token, remove_parentclass, replace_type)
            token = ''
            new_param_type += replace + param_type[i]
        else:
            token = token + param_type[i]
            if i == len(param_type) - 1:
                replace = handle_token(token, remove_parentclass, replace_type)
                new_param_type += replace
    return new_param_type


def replace_types(param_type):
    for k, v in type_dict.items():
        if k in param_type:
            param_type = param_type.replace(k, v)
    return param_type


def ctor_to_class_name(value):
    """Replace ..ctor and ..cctor with the actual name of the constructor """
    if "..ctor" in value:
        idx2 = value.rfind("..ctor")
        idx1 = value[:idx2].rfind(".")
        cls_name = value[idx1:idx2]
        # in case the class has generics keep only the class name
        if '<' in cls_name:
            cls_name = cls_name[:cls_name.find('<')]
        value = value.replace("..ctor", cls_name)
    if "..cctor" in value:
        idx2 = value.rfind("..cctor")
        idx1 = value[:idx2].rfind(".")
        cls_name = value[idx1:idx2]
        # in case the class has generics keep only the class name
        if '<' in cls_name:
            cls_name = cls_name[:cls_name.find('<')]
        value = value.replace("..cctor", cls_name)
    return value


def remove_generics(params_decl):
    new_decl = ''
    count = 0

    for i in range(len(params_decl)):
        c = params_decl[i]
        if c == '<':
            count += 1
            continue
        if c == '>':
            count -= 1
            continue
        if c == '&':
            continue
        if count == 0:
            new_decl += c

    return new_decl


# --------- Source code metrics report --------- #

def change_method_name_metrics(method):
    """Modifies the method name for the source code metrics report"""
    # for inner classes
    method = method.replace('+', '.')
    # for out, ref paramaters
    method = method.replace('&', '')
    # some parameter types include also the parent; and other reports don't include it eg SqlMapper.GridReader
    start_parameters = method.rfind('(')
    method_name = method[:start_parameters]
    parameters_text = method[start_parameters:]
    if len(parameters_text) > 2:
        parameters_text = replace_by_token(parameters_text, True, False)

    new_name = method_name + parameters_text

    return new_name


# --------- Repository mining metrics report --------- #

def change_method_name_commits(method):
    """Modifies the method name for the repository mining metrics report"""
    if method is np.nan:
        return method

    method = method.replace('::', '.')
    start_parameters = method.rfind('(')
    method_name = method[:start_parameters]
    parameters_text = method[start_parameters:]
    if len(parameters_text) > 2:
        parameters_text = parameters_text[1:-1]  # remove ()
        # remove [FromBody] from parameters text
        parameters_text = parameters_text.replace("[ FromBody ] ", "")
        parameters = parameters_text.split(', ')
        params_types = []
        for param in parameters:
            if "=" in param:
                param = param[:param.find("=")]

            # remove potential spaces from start and end
            param = param.strip(" ")

            p = param.split(' ')
            if " ? " in param:
                # if int ? _ -> Nullable<Int32>
                p_t = replace_by_token(p[0], True, True)
                param_type = "Nullable<" + p_t + ">"
                if "[]" in ''.join(p[0:-1]):
                    param_type = param_type + "[]"
            else:
                start = 0
                end = -1
                if (p[0] == "params") or (p[0] == "this") or (p[0] == "out") or (p[0] == "in") or (p[0] == "ref"):
                    # if params string [] _ -> String[] or params Func<T,object> [] _ -> Func<T,Object>[]
                    start = 1
                p_t = ''.join(p[start:end])
                param_type = replace_by_token(p_t, True, True)

            params_types.append(param_type)
        parameters_text = '(' + ','.join(params_types) + ')'

    new_name = method_name + parameters_text
    return new_name


# --------- Profiler metrics report --------- #

def change_method_name_usage(method):
    """Modifies the method name for the repository mining metrics report"""
    if '`' in method:
        idx = method.find('`')
        part = method[idx+1:]
        method = method[:idx] + part[part.find('.'):]
    params_start = method.rfind('(')
    method_name = method[:params_start]
    params_text = method[params_start:]
    if len(params_text) > 2:
        parameters_text = params_text[1:-1]  # remove ()
        parameters = parameters_text.split(',')
        params_types = []
        for param in parameters:
            param = param.strip(" ")
            if param.startswith("params "):
                param = param[len("params"):]
            elif param.startswith("out "):
                param = param[len("out"):]
            elif param.startswith("in "):
                param = param[len("in"):]
            elif param.startswith("ref "):
                param = param[len("ref"):]
            param = param.strip(" ")
            params_types.append(param)
        params_text = '(' + ','.join(params_types) + ')'

    # for inner classes
    method_name = method_name.replace('+', '.')

    new_name = method_name + params_text
    return new_name


def get_profiler_metrics_data(file):
    """Parses the XML file to collect the method signatures"""
    calls_metrics = {'Method': [], 'Calls': []}
    root = ElementTree.parse(file).getroot()
    for type_tag in root.findall('Function'):
        method = type_tag.get('FQN')
        calls = type_tag.get('Calls')

        calls_metrics['Method'].append(str(method))
        calls_metrics['Calls'].append(int(calls))
    df = pd.DataFrame(data=calls_metrics)
    df['Method'] = df['Method'].apply(change_method_name_usage)
    return df


# --------- Test coverage report --------- #

def change_name_coverage(method):
    """Modifies the method name for the test coverage report"""
    start_parameters = method.rfind('(')
    method_name = method[:start_parameters]
    parameters_text = method[start_parameters:]
    if len(parameters_text) > 2:
        parameters_text = parameters_text.replace('params ', '')
        parameters_text = parameters_text.replace('out ', '')
        parameters_text = parameters_text.replace('ref ', '')
        parameters_text = parameters_text.replace('in ', '')
        parameters_text = replace_by_token(parameters_text, True, True)

    new_name = method_name + parameters_text
    return new_name


test_coverage = {'Method': [], 'TotalStatements': [], 'CoveredStatements': []}


def get_children(all_path, element):
    """Recursive function to parse the XML file and collect the method signatures"""
    name = element.get("Name")
    if element.tag in ['Method', 'Constructor']:
        all_path += name
        method_name = str(all_path)
        idx = method_name.rfind(':')
        if idx > 0:
            method_name = method_name[:idx]
        test_coverage['Method'].append(method_name)
        test_coverage['TotalStatements'].append(int(element.get("TotalStatements")))
        test_coverage['CoveredStatements'].append(str(element.get("CoveredStatements")))
    elif name is not None:
        all_path += name + '.'

    for el in list(element):
        get_children(all_path, el)


def collect_test_coverage_data(file):
    """Reads the XML file and returns a data frame with the method signatures"""
    root = ElementTree.parse(file).getroot()
    #     for type_tag in root.findall('Project/*'):
    # in the new version we have assembly instead of project
    for type_tag in root.findall('Assembly/*'):
        get_children('', type_tag)

    return pd.DataFrame(data=test_coverage)
