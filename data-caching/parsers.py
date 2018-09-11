import re
import statistics
import math


def parse_data_caching(log_file_names):
    graph_data = {
        'graphs': [],
        'figure_size': (24, 20),
        'dimensions': (3, len(log_file_names)),
        'sup_title': 'Data Caching (memcached) with 1 Core and 2048 MB'
    }

    memory_size = 2

    for log_file_name in log_file_names:
        log_file = open(log_file_name)

        profiles = {}
        current_rps = None
        cpu_set = []
        suffix = ''

        for line in log_file:
            line = line.replace('\n', '')

            if line.startswith('rps: '):
                current_rps = int(line.split()[1])
                profiles[current_rps] = {
                    'cpu_util': {},
                    '95th': [],
                    '99th': [],
                    'rps': [],
                }

            if line.startswith('cpu_set: '):
                cpu_set = [int(cpu_index_string) for cpu_index_string in line.split()[1].split(',')]

            if line.startswith('suffix: '):
                suffix = line.split()[1]

            if line.startswith('memory_size: '):
                memory_size = int(line.split()[1])

            if current_rps is not None:
                match = re.match(
                    r"^\d\d:\d\d:\d\d[ \t]+[PMA]*[ \t]+([\d\.]+)[ \t]+([\d\.]+)[ \t]+([\d\.]+)[ \t]+([\d\.]+)[ \t]+"
                    r"([\d\.]+)[ \t]+([\d\.])+[ \t]+([\d\.]+)[ \t]+([\d\.]+)[ \t]+([\d\.]+)[ \t]+([\d\.]+)[ \t]+"
                    r"([\d\.]+)$",
                    line
                )
                if match is not None:
                    cpu_stats = match.groups()
                    if int(cpu_stats[0]) not in profiles[current_rps]['cpu_util']:
                        profiles[current_rps]['cpu_util'][int(cpu_stats[0])] = []
                    profiles[current_rps]['cpu_util'][int(cpu_stats[0])].append(100 - float(cpu_stats[10]))

                match = re.match(
                    r"^[ \t]+([\d\.]+),[ \t]+([\d\.]+),[ \t]+([\d\.]+),[ \t]+([\d\.]+),[ \t]+([\d\.]+),[ \t]+([\d\.]+),"
                    r"[ \t]+([\d\.]+),[ \t]+([\d\.]+),[ \t]+([\d\.]+),[ \t]+([\d\.]+),[ \t]+([\d\.]+),[ \t]+([\d\.]+),"
                    r"[ \t]+([\d\.]+),[ \t]+([\d\.]+),[ \t]+([\d\.]+)$",
                    line
                )
                if match is not None:
                    load_stat = match.groups()
                    profiles[current_rps]['95th'].append(float(load_stat[9]))
                    profiles[current_rps]['99th'].append(float(load_stat[10]))
                    profiles[current_rps]['rps'].append(float(load_stat[1]))

        if current_rps is not None:
            if len(profiles[current_rps]['cpu_util'].keys()) == 0:
                del profiles[current_rps]

        # form the graph data to plot
        def mean_and_error_last_numbers(numbers, count=20, offset=0, normalize_by_mean_as_real_count=True):
            selected_numbers = []
            for index in range(count):
                number = numbers[len(numbers) - 1 - index - offset]
                selected_numbers.append(number)
            mean = statistics.mean(selected_numbers)
            return (
                mean,
                statistics.stdev(selected_numbers) * (math.sqrt(count / mean) if normalize_by_mean_as_real_count else 1)
            )

        def merge_cpu_set_stat(all_utilizations, cpu_set):
            result_utilizations = []
            for sample_index in range(len(all_utilizations[cpu_set[0]])):
                cpu_set_utilizations = []
                for cpu_index in cpu_set:
                    cpu_set_utilizations.append(all_utilizations[cpu_index][sample_index])
                result_utilizations.append(statistics.mean(cpu_set_utilizations))
            return result_utilizations

        x_data = list(profiles.keys())
        throughput = [mean_and_error_last_numbers(profiles[key]['rps'])[0] for key in profiles.keys()]

        utilizations = []
        utilization_errors = []

        tail_latencies_95th = []
        tail_latency_95th_errors = []

        tail_latencies_99th = []
        tail_latency_99th_errors = []

        for rps in profiles.keys():
            utilization, utilization_error = mean_and_error_last_numbers(
                merge_cpu_set_stat(profiles[rps]['cpu_util'], cpu_set),
                2,
                normalize_by_mean_as_real_count=False
            )

            utilizations.append(utilization)
            utilization_errors.append(utilization_error)

            tail_latency_95th, tail_latency_95th_error = mean_and_error_last_numbers(profiles[rps]['95th'])
            tail_latencies_95th.append(tail_latency_95th)
            tail_latency_95th_errors.append(tail_latency_95th_error)

            tail_latency_99th, tail_latency_99th_error = mean_and_error_last_numbers(profiles[rps]['99th'])
            tail_latencies_99th.append(tail_latency_99th)
            tail_latency_99th_errors.append(tail_latency_99th_error)

        # noinspection PyTypeChecker
        graph_data['graphs'].append(
            {
                'x': x_data,
                'x_label': 'Target RPS',
                'title': '',
                'y': {
                    'left': [
                        {
                            # 'type': 'errorbar',
                            'type': 'plot',
                            'format': 'r.',
                            'data': tail_latencies_95th,
                            'error': tail_latency_95th_errors,
                            'label': '95th Latency (ms)',
                            'trend_line': True,
                            'trend_line_format': 'r--',
                        },
                    ],
                    'left_label': 'Latency (ms)',
                    'left_limit': 100,
                    'right': [

                        # {
                        #     'type': 'errorbar',
                        #     'data': tail_latencies_99th,
                        #     'error': tail_latency_99th_errors,
                        #     'label': '99th Latency (ms)',
                        # },
                    ],
                    'right_limit': 100,
                    'right_label': ''
                }
            }
        )
        # noinspection PyTypeChecker
        graph_data['graphs'].append(
            {
                'x': x_data,
                'x_label': 'Target RPS',
                'title': '{}'.format(
                    suffix
                ),
                'y': {
                    'left': [
                        {
                            'type': 'plot',
                            'format': 'b.',
                            'data': utilizations,
                            'error': utilization_errors,
                            'label': 'Server CPU Utilization (%)',
                            'trend_line': False,
                        }
                    ],
                    'left_label': 'Server CPU Utilization (%)',
                    'left_limit': 100,
                    'right': [
                    ],
                    'right_limit': 100,
                    'right_label': ''
                }
            }
        )
        
        # noinspection PyTypeChecker
        graph_data['graphs'].append(
            {
                'x': x_data,
                'x_label': 'Target RPS',
                'title': '',
                'y': {
                    'left': [
                        {
                            'type': 'plot',
                            'format': 'b.',
                            'data': throughput,
                            'error': None,
                            'label': 'Actual RPS',
                            'trend_line': False,
                        }
                    ],
                    'left_label': 'Throughput (RPS)',
                    'left_limit': 90000,
                    'right': [
                    ],
                    'right_limit': 100,
                    'right_label': ''
                }
            }
        )

    graph_data['graphs'] = [
        graph_data['graphs'][1],
        graph_data['graphs'][4],
        graph_data['graphs'][0],
        graph_data['graphs'][3],
        graph_data['graphs'][2],
        graph_data['graphs'][5]
    ]
    
    return graph_data
