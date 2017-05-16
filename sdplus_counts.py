import csv
import datetime
import os
from sdplus_api_rest_nbt import ApiNbt
from typing import Dict, List

from slackclient import SlackClient
slack_api = SlackClient(os.environ['SLACK_LORENZOBOT'])
# attachments: https://api.slack.com/docs/message-attachments
# try: https://api.slack.com/docs/messages/builder


class Counts:
    def __init__(self):
        self.sdplus_api = ApiNbt(os.environ['SDPLUS_ADMIN'], 'http://sdplus/sdpapi/')
        self.datetime_format = '%d/%m/%Y %H:%M'

    def read_counts_from_sdplus(self, queues_name_id_list):
        """
        Get counts and call details from sdplus for queue names in queues_list
        :param queues_name_id_list: [{'name': 'displayed queue name', 'id': 'queue id in sdplus'}, ...]
        :return:    [{'name': 'Back Office',
                    'id': 'Back Office_QUEUE',
                    'count all': 79,
                    'count open': 45,
                    'all calls': [{'isoverdue': 'false', 'TECHNICIAN': None, 'duebytime': '-1', ... }] }]
        """
        queues_name_id_list_count = queues_name_id_list.copy()
        for queue in queues_name_id_list_count:
            queue['all calls'] = self.sdplus_api.request_get_requests(queue['id'])
            queue['count all'] = len(queue['all calls'])
            queue['count open'] = len([x for x in queue['all calls'] if x['status'] == 'Open'])
        return queues_name_id_list_count

    def write_counts_to_file(self, queue_counts: List[Dict], counts_file):
        """
        Writes stats to a file
        :param queue_counts: output of self.read_counts_from_sdplus
        :param counts_file: csv file to write to
        :return: True
        """
        with open(counts_file, 'a', newline='') as record:
            csv_record = csv.writer(record)
            now_string = datetime.datetime.now().strftime(self.datetime_format)
            for entry in queue_counts:
                csv_record.writerow([entry['name'], entry['count open'], now_string])
        return True

    def read_counts_from_file(self, counts_file, date_field='datetime', count_field='count open'):
        stats = [x for x in csv.DictReader(open(counts_file))]
        for stat in stats:
            stat[date_field] = datetime.datetime.strptime(stat[date_field], self.datetime_format)
            stat[count_field] = int(stat[count_field])
        return stats

    @staticmethod
    def latest_counts_on_date(counts_from_file, on_date, date_field='datetime', name_field='name'):
        # restrict to date obj, sort by most recent, then add unique
        all_entries_for_on_date = [x for x in counts_from_file if x[date_field].date() == on_date]
        all_entries_for_on_date = sorted(all_entries_for_on_date, key=lambda item: item[date_field], reverse=True)
        final_recent_list = []
        for x in all_entries_for_on_date:
            if x[name_field] not in [y[name_field] for y in final_recent_list]:
                final_recent_list.append(x)
        return final_recent_list

    @staticmethod
    def compare(old, new, name='name', compare='count open'):
        """
        Compares older stats to newer stats
        :param old: output from read_counts_from_file, or today_counts
        :param new: output from read_counts_from_sdplus
        :param name: key which identifies the same items in old and new
        :param compare: key to compare, e.g. 'count open', note: len(value) MUST be a valid int
        :return: [{'name': 'some queue name', 'count open': -1}, {...}]
        """
        comparison_result = []
        for new_queue in new:
            for old_queue in old:
                queue_comparison_result = {}
                if old_queue[name] == new_queue[name]:
                    queue_comparison_result[name] = new_queue[name]
                    queue_comparison_result[compare] = new_queue[compare] - old_queue[compare]  # ints
                    comparison_result.append(queue_comparison_result)
        return comparison_result

    @staticmethod
    def slack_attachments(comparison_result):
        attachments = []
        for result in comparison_result:
            value_text = Counts.int_to_string(result['count open'])
            attachments.append({
                'color': 'good' if result['count open'] < 0 else 'warning' if result['count open'] == 0 else 'danger',
                'fields': [
                    {
                        'title': result['name'],
                        'short': True
                    },
                    {
                        'value': value_text,
                        'short': True
                    }]
            })
        return attachments

    @staticmethod
    def int_to_string(number: int):
        if number > 0:
            return '+' + str(number)
        else:
            return str(number)

