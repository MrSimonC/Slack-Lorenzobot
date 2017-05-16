import csv
import datetime
from dateutil.relativedelta import relativedelta
import json
import os
import random
import re
import sys
import time
import schedule
import slack_lorenzobot_quotes
from intouch_mappings import InTouchMapping
from sdplus_api_rest_nbt import ApiNbt
from sdplus_counts import Counts
from slackclient import SlackClient

__version__ = '1.64'
# https://it-nbt.slack.com/apps/manage/custom-integrations
# https://api.slack.com/methods
# https://api.slack.com/docs/messages/builder
# https://github.com/slackhq/python-slackclient

# Below TODOs not finished as I left NBT before they were implemented Nov2016
# TODO: Sdplus Maid: Third party queue - calls which have got closed from CSC in conversation
# TODO: Sdplus Maid: Slack the oldest Back Office with who owns it to Back Office group
# TODO: Sdplus Maid: CSC - still open after 6 days + produce report of the last month of closed + open Third party
# ...calls which weren't resolved within SLA
# TODO: Mitch: add user into eRS service ID
# TODO: Galaxy: Reset user's Galaxy password
# TODO: Do DI links for UUID and AD account


class RTM:
    def __init__(self):
        # Env vars check
        try:
            if not os.environ['SLACK_LORENZOBOT'] and not os.environ['SDPLUS_ADMIN']:
                print('Needed environment variables not found')
                sys.exit(1)  # exit as error
        except KeyError:
            print('Needed environment variables not found')
            sys.exit(1)  # exit as error
        # this_module's path
        if hasattr(sys, 'frozen'):
            self.this_module = os.path.dirname(sys.executable)
        else:
            self.this_module = os.path.dirname(os.path.realpath(__file__))
        # Slack
        self.sc = SlackClient(os.environ['SLACK_LORENZOBOT'])
        self.bo_channel = 'backoffice'
        self.event = None  # set later when event received
        self.approved_users = ['U1F4X362D', 'U1FA6DMFV', 'U1FBYK4BZ']  # Simon Crouch, Paul Stinson, Mitch
        self.use_approved_users_authentication = False  # turn on to use above list
        self.previous_responses = []
        self.counts = Counts()
        # SDPlus
        self.sdplus_api = ApiNbt(os.environ['SDPLUS_ADMIN'], 'http://sdplus/sdpapi/')
        # Files
        self.triage_rota_file = os.path.join(self.this_module, 'triage_rota.csv')
        self.queue_list_file_path = os.path.join(self.this_module, 'back office queue list.txt')
        self.queue_count_file_path = os.path.join(self.this_module, 'back office queue count.csv')
        nine_am = '07:00'
        schedule.every().monday.at(nine_am).do(self.inform_bo_of_rota_and_record_stats)
        schedule.every().tuesday.at(nine_am).do(self.inform_bo_of_rota_and_record_stats)
        schedule.every().wednesday.at(nine_am).do(self.inform_bo_of_rota_and_record_stats)
        schedule.every().thursday.at(nine_am).do(self.inform_bo_of_rota_and_record_stats)
        schedule.every().friday.at(nine_am).do(self.inform_bo_of_rota_and_record_stats)
        # Schedule
        morning_1 = '10:30'
        schedule.every().monday.at(morning_1).do(self.rota_dq_check)
        schedule.every().tuesday.at(morning_1).do(self.rota_dq_check)
        schedule.every().wednesday.at(morning_1).do(self.rota_dq_check)
        schedule.every().thursday.at(morning_1).do(self.rota_dq_check)
        schedule.every().friday.at(morning_1).do(self.rota_dq_check)
        morning_2 = '11:30'
        schedule.every().monday.at(morning_2).do(self.rota_dq_check)
        schedule.every().tuesday.at(morning_2).do(self.rota_dq_check)
        schedule.every().wednesday.at(morning_2).do(self.rota_dq_check)
        schedule.every().thursday.at(morning_2).do(self.rota_dq_check)
        schedule.every().friday.at(morning_2).do(self.rota_dq_check)
        afternoon_1 = '14:30'
        schedule.every().monday.at(afternoon_1).do(self.rota_dq_check)
        schedule.every().tuesday.at(afternoon_1).do(self.rota_dq_check)
        schedule.every().wednesday.at(afternoon_1).do(self.rota_dq_check)
        schedule.every().thursday.at(afternoon_1).do(self.rota_dq_check)
        schedule.every().friday.at(afternoon_1).do(self.rota_dq_check)
        afternoon_2 = '14:45'
        schedule.every().monday.at(afternoon_2).do(self.stats_day_get_inform_bo)
        schedule.every().tuesday.at(afternoon_2).do(self.stats_day_get_inform_bo)
        schedule.every().wednesday.at(afternoon_2).do(self.stats_day_get_inform_bo)
        schedule.every().thursday.at(afternoon_2).do(self.stats_day_get_inform_bo)
        schedule.every().friday.at(afternoon_2).do(self.stats_day_get_inform_bo)

    def start(self):
        """
        Every second, look for activity. If found, act on it.
        :return: Chats back into Slack
        """
        if self.sc.rtm_connect():
            while True:
                schedule.run_pending()
                events = self.sc.rtm_read()
                # if events:
                #     print(events)  # Can't have unicode output on windows cmd
                for event in events:
                    if self.directed_at_bot(event):
                        self.event = event
                        self.process()
                time.sleep(1)
        else:
            print('Connection Failed, invalid token?')

    @staticmethod
    def directed_at_bot(event):
        if 'type' in event \
                and event['type'] == 'message' \
                and 'bot_id' not in event \
                and 'text' in event \
                and (event['channel'][:1] == 'D' or '<@U1FCPA9QV>' in event['text']):  # U1FCPA9QV=@lorenzobot
            return True
        return False

    def process(self):
        print('Found input to process')
        user_input = self.event['text'].replace('<@U1FCPA9QV>', '').strip()
        if 'version' == user_input.lower():
            self.send(__version__)
        # SDPlus CreateTI
        elif 'sdplus createti' in user_input.lower():
            self._create_ti_call(user_input)
        # SDPlus Create
        elif 'sdplus create' in user_input.lower():
            self._create_call(user_input)
        # SDPlus Edit
        elif 'sdplus edit' in user_input.lower():
            self._edit_call(user_input)
        # InTouch Mapping
        elif 'intouch check' in user_input.lower():
            self._intouch_check(user_input)
        # Call Triage Rota - Get User
        elif 'rota get' in user_input.lower():
            if self.use_approved_users_authentication:
                if self.event['user'] in self.approved_users:
                    self.rota_get()
            else:
                self.rota_get()
        # Call Triage Rota - Set User
        elif 'rota set' in user_input.lower():
            if self.use_approved_users_authentication:
                if self.event['user'] in self.approved_users:
                    self.rota_set(user_input)
            else:
                self.rota_set(user_input)
        # Call Triage Rota - Inform back office
        elif 'rota inform' in user_input.lower():
            if self.use_approved_users_authentication:
                if self.event['user'] in self.approved_users:
                    self.rota_inform_bo_of_today_person()
            else:
                self.rota_inform_bo_of_today_person()
        # Stats get month
        elif 'stats get month' in user_input.lower():
            self.stats_get_month()
        # Stats get week
        elif 'stats get week' in user_input.lower():
            self.stats_get_week()
        # Stats get day
        elif 'stats get day' in user_input.lower() or 'stats get' in user_input.lower():
            self.stats_get_day()
        # Set Stats
        elif 'stats set -f' in user_input.lower():
            if self.use_approved_users_authentication:
                if self.event['user'] in self.approved_users:
                    self.stats_set()
            else:
                self.stats_set()
        # Quote
        elif 'quote' in user_input.lower():
            self.send(slack_lorenzobot_quotes.get_inspring_quote())
        # Help
        elif 'help' in user_input.lower():
            self._help()
        # Answer Questions
        elif '?' in user_input:
            self._answer_questions()
        else:
            self.send('Hey {0} - ask me a question, or type `help` to see my commands.'.format(random.choice(you)))

    def _create_ti_call(self, ti_params):
        ti_params = [str(x.strip()) for x in self._remove_case_insensitive('sdplus createti', ti_params).split(',')]
        if len(ti_params) < 3:
            self.send('Nothing done - try formatting your input. Type `help` to check.')
            return
        # TI number, Test Cycle number, tel extension, [title, description, requester, assignee, group]
        ti_number = 'RVJ-TI-' + ti_params[0]
        test_cycle = ti_params[1]
        tel = ti_params[2]
        title = ''
        description = ''
        requester = ''
        assignee = ''
        group = 'Lorenzo Testing'
        try:
            if ti_params[3]:
                title = ti_params[3]
            if ti_params[4]:
                description = ti_params[4]
            if ti_params[5]:
                requester = ti_params[5]
            if ti_params[6]:
                assignee = ti_params[6]
            if ti_params[7]:
                group = ti_params[7]
        except IndexError:
            pass
        if not requester:
            requester = self._slack_get_real_name(self.event['user'])
        if not assignee:
            assignee = requester
        date_now = datetime.datetime.now().strftime('%d/%m/%Y')
        body = 'Hello CSC,\n\nPlease Find The Below Test Issue Noted During {0} Test Cycle.\n\n ' \
               'Trust Local Issue Id\n{1}\n\nIssue Title\n{5}\n\nIssue Description\n{6}\n\nContact Details' \
               '\n{2}@nbt.nhs.uk\n0117 414 {3}\n\nEnvironment\n1067\n\nBuild\n{0}\n\nDate Raised\n{7}\n\n' \
               'Replication Steps\n\n\n\nAny queries or problems, please let me know.\nKind Regards \n{4}' \
            .format(test_cycle, ti_number, requester.replace(' ', '.', 1), tel, requester, title, description,
                    date_now)
        fields = {
            'reqtemplate': 'Default Request',
            'requesttype': 'Service Request',
            'status': 'Open',
            'requester': requester,
            'mode': '@Southmead Retained Estate',  # Site
            'best contact number': tel,
            'Exact Location': '-',
            'group': group,
            'subject': ti_number,
            'description': body,
            'service': '.Lorenzo/Galaxy - IT Templates',  # Service Category
            'category': 'Clinical Applications Incident',  # Self Service Incident
            'subcategory': 'Lorenzo',
            'impact': self.sdplus_api.get_impact('5'),
            'urgency': self.sdplus_api.get_urgency('5'),
            'technician': assignee
        }
        api_response = self.sdplus_api.request_add(fields)
        if api_response['response_status'] == 'Success':
            sdplus_href = '<http://sdplus/WorkOrder.do?woMode=viewWO&woID={sdplus_ref}|{sdplus_ref}>' \
                .format(sdplus_ref=api_response['workorderid'])
            self.send('TI Call {0} created successfully.'.format(sdplus_href))
        else:
            self.send('Call not created due to error.')

    def _create_call(self, call_params):
        call_params = [x.strip() for x in self._remove_case_insensitive('sdplus create', call_params).split(',')]
        # Summary [, Impact, Urgency, Requester, Description, Telephone, Assignee, Group]
        summary = ''
        impact = '3'
        urgency = '3'
        requester = ''
        description = ''
        tel = '-'
        assignee = ''
        group = 'Back Office'
        if call_params != ['']:
            try:
                summary = call_params[0]
                if call_params[1]:
                    impact = call_params[1]
                if call_params[2]:
                    urgency = call_params[2]
                if call_params[3]:
                    requester = call_params[3]
                if call_params[4]:
                    description = call_params[4]
                if call_params[5]:
                    tel = call_params[5]
                if call_params[6]:
                    assignee = call_params[6]
                if call_params[7]:
                    group = call_params[7]
            except IndexError:
                pass
            if not requester:
                requester = self._slack_get_real_name(self.event['user'])
            if not description:
                description = summary + '\n\n(This call was auto-created by Back Office from Slack)'
            if not assignee:
                assignee = requester
            fields = {
                'reqtemplate': 'Default Request',
                'requesttype': 'Service Request',
                'status': 'Pending',
                'requester': requester,
                'mode': '@Southmead Retained Estate',  # Site
                'best contact number': tel,
                'Exact Location': '-',
                'group': group,
                'subject': summary,
                'description': description,
                'service': '.Lorenzo/Galaxy - IT Templates',  # Service Category
                'category': 'Clinical Applications Incident',  # Self Service Incident
                'subcategory': 'Lorenzo',
                'impact': self.sdplus_api.get_impact(impact),
                'urgency': self.sdplus_api.get_urgency(urgency),
                'technician': assignee
            }
            api_response = self.sdplus_api.request_add(fields)
            if api_response['response_status'] == 'Success':
                sdplus_href = '<http://sdplus/WorkOrder.do?woMode=viewWO&woID={sdplus_ref}|{sdplus_ref}>' \
                    .format(sdplus_ref=api_response['workorderid'])
                self.send('Call {0} created successfully.'.format(sdplus_href))
            else:
                self.send('Call not created due to error.')

    def _edit_call(self, call_params):
        call_params = self._remove_case_insensitive('sdplus edit', call_params)
        re_sdplus_ref = r'^\d{6}'  # 6 digits at start
        if not re.search(re_sdplus_ref, call_params):
            self.send("Couldn't work out sdplus number from your request. It should be e.g. sdplus edit 123456")
        else:
            sdplus_ref = re.search(re_sdplus_ref, call_params).group(0)
            call_params = call_params.replace(sdplus_ref, '').strip()
            valid_sdplus_fields = [
                'status',
                'group',
                'impact',
                'urgency',
                'level',
                'tel',
                'requester',
                'subject',
                'description'
            ]
            key, value = self._remove_field_from_string(valid_sdplus_fields, call_params)
            if key == 'impact':
                value = self.sdplus_api.get_impact(value)
            if key == 'urgency':
                value = self.sdplus_api.get_urgency(value)
            if key == 'tel':
                key = 'best contact number'
            if key == 'level':
                if value.lower() == 'a':
                    value = 'A – High'
                elif value.lower() == 'b':
                    value = 'B – Medium'
                if value.lower() == 'c':
                    value = 'C – Low'
            if key and value:
                update = self.sdplus_api.request_edit(sdplus_ref, {key: value})
                if update['response_status'] == 'Success':
                    sdplus_href = '<http://sdplus/WorkOrder.do?woMode=viewWO&woID={sdplus_ref}|{sdplus_ref}>' \
                        .format(sdplus_ref=sdplus_ref)
                    self.send('Call {0} updated successfully.'.format(sdplus_href))
                else:
                    self.send('Call not updated due to error.')
            else:
                self.send('Nothing done - try formatting your input. Type `help` to check.')

    def _intouch_check(self, sp_or_tf):
        it = InTouchMapping()
        re_sp = r'([a-zA-Z0-9]*_){2}[a-zA-Z0-9]*'
        if re.search(re_sp, sp_or_tf):
            sp = re.search(re_sp, sp_or_tf).group()
            sp_map = it.show_match_for_sp(sp.upper())
            send_message = ', '.join(sp_map)
        else:
            tf = self._remove_case_insensitive('intouch check', sp_or_tf)
            tf_map = it.show_match_for_intouchlocation(tf)
            send_message = ', '.join(tf_map)
        if not send_message:
            send_message = 'Sorry - No Results. _(note: Treatment Function is case sensitive)_'
        self.send(send_message)

    def send(self, message, channel=None, save_response=False):
        if channel is None:
            channel = self.event['channel']
        self.sc.api_call('chat.postMessage', as_user=True, channel=channel, text=message)
        if save_response:
            self.previous_responses.append({'channel': channel, 'response': message})

    def rota_inform_bo_of_today_person(self):
        user_id = self._rota_get_today_person()
        self.send('Triage and Logging Calls to CSC today is: <@{0}>'.format(user_id), self.bo_channel)

    def rota_get(self):
        self.send('Triage rota today is: <@{0}>'.format(self._rota_get_today_person()))

    def rota_set(self, slack_user_id):
        slack_user_id = self._remove_case_insensitive('rota set', slack_user_id)
        slack_user_id = slack_user_id.replace('<@', '').replace('>', '')
        self._rota_set_today_person(slack_user_id)
        self.send('Triage rota today is set to: <@{0}>'.format(self._rota_get_today_person()))

    def _rota_get_today_person(self):
        rota = [x for x in csv.DictReader(open(self.triage_rota_file))]
        for entry in rota:
            if datetime.datetime.strptime(entry['Date'], '%d/%m/%Y').date() == datetime.datetime.now().date():
                return self._slack_get_id(entry['Person'])

    def _rota_set_today_person(self, slack_user_id):
        rota = [x for x in csv.DictReader(open(self.triage_rota_file))]
        for entry in rota:
            if datetime.datetime.strptime(entry['Date'], '%d/%m/%Y').date() == datetime.datetime.now().date():
                entry['Person'] = self._slack_get_real_name(slack_user_id)
        with open(self.triage_rota_file, 'w', newline='') as rota_file_out:
            writer = csv.DictWriter(rota_file_out, rota[0].keys())
            writer.writeheader()
            writer.writerows(rota)

    def stats_set(self, channel=None):
        keys = ['name', 'id']
        queues_list_with_id = open(self.queue_list_file_path).read().split('\n')
        queues_list_with_id = [dict(zip(keys, x.split('\t'))) for x in queues_list_with_id]
        try:
            stats_now = self.counts.read_counts_from_sdplus(queues_list_with_id)
        except TypeError:
            print('XML TypeError confirmed')
            self.send('Had major trouble talking to sdplus - I failed to set stats', channel)
            return False
        self.counts.write_counts_to_file(stats_now, self.queue_count_file_path)
        self.send('stats set.', channel)

    def stats_get_day(self, channel=''):
        try:
            self._stats_get(datetime.datetime.now().date(), channel)
        except IndexError:
            self.send('Stats not set for the day. Recording stats now.')
            self.stats_set()
            try:
                self._stats_get(datetime.datetime.now().date(), channel)
            except IndexError:
                self.send("Had major trouble getting stats from file. Tell my creator they can't code.")
                return False

    def stats_get_week(self, channel=''):
        try:
            self._stats_get(datetime.datetime.now().date()-datetime.timedelta(days=7), channel)
        except IndexError:
            self.send("Sorry, no stats found for this time last week I'm afraid. Try again tomorrow?")

    def stats_get_month(self, channel=''):
        try:
            self._stats_get(datetime.datetime.now().date()-relativedelta(months=1), channel)
        except IndexError:
            self.send("Sorry, no stats found for this time last month I'm afraid. "
                      "Try again tomorrow, he-he or next month?")

    def _stats_get(self, date_to_get_stats, channel=''):
        keys = ['name', 'id']
        queues_list_with_id = open(self.queue_list_file_path).read().split('\n')
        queues_list_with_id = [dict(zip(keys, x.split('\t'))) for x in queues_list_with_id]
        stats_now = self.counts.read_counts_from_sdplus(queues_list_with_id)
        stats_all_from_file = self.counts.read_counts_from_file(self.queue_count_file_path)
        stats_earlier_from_file = self.counts.latest_counts_on_date(stats_all_from_file, on_date=date_to_get_stats)
        try:
            earlier_time = stats_earlier_from_file[0]['datetime'].strftime('%H:%M')
        except IndexError:  # no data found for date_to_get_stats
            raise
        comparison_result = self.counts.compare(stats_earlier_from_file, stats_now)
        overall_change = Counts.int_to_string(sum(x['count open'] for x in comparison_result))
        attachments = self.counts.slack_attachments(comparison_result)
        self.sc.api_call('chat.postMessage', as_user=True, channel=channel if channel else self.event['channel'],
                         text='Statistics show {change} overall since {time} :'.format(time=earlier_time,
                                                                                       change=overall_change),
                         attachments=json.dumps(attachments))
        return True

    def stats_day_get_inform_bo(self):
        self.stats_get_day('backoffice')

    def _help(self):
        help_message = (
            '*help* _- Show This Menu_\n'
            '*intouch check* Clinic_ID or Mapped Treatment Function _- Shows Mapping_\n'
            '*sdplus create* Summary [, Impact, Urgency, Requester, Description, Telephone, Assignee, Group] _- Create SDPlus Call (with optional fields)_\n'
            '*sdplus createti* TI Number, Test Cycle Number, Tel Extension, [Title, Description, Requester, Assignee, Group] _- Create TI SDPlus Call_\n'
            '*sdplus edit* number [status/group/impact/urgency/level/tel/requester/subject/description] value _- Edit SDPlus Call_\n'
            '*stats get [day/week/month]* _- Get Statistics for Back Office queues today/this week/this month_\n'
            '_Ask a Question_ (use *?*) _- Lets chat!_\n'
            '*quote* _- Tell me a nice quote_'
        )
        try:
            higher_commands = ('\n*rota get* _- Get Triage Rota Person_\n'
                               '*rota set @username* _- Set Triage Rota Person_\n'
                               "*rota inform* _- Inform Back Office of who's on rota_\n"
                               '*stats set -f* _- Force Set of Statistics for Back Office queues_')
            if self.use_approved_users_authentication:
                if self.event['user'] in self.approved_users:
                    help_message += higher_commands
            else:
                help_message += higher_commands
        except KeyError:
            pass
        self.send(help_message)

    def _answer_questions(self):
        response = random.choice(responses)
        if not self.previous_responses \
                or {'channel': self.event['channel'], 'response': response} not in self.previous_responses:
            self.send(response, save_response=True)
        else:  # we've happened upon something we sent previously, so choose from answers left
            sent_channel_responses = [x['response'] if x['channel'] == self.event['channel']
                                      else '' for x in self.previous_responses]
            responses_left = list(set(responses) - set(sent_channel_responses))
            if responses_left:
                response = random.choice(responses_left)
                self.send(response, save_response=True)
            else:
                response = "Right, I'm off. Bye then, n'stuff."
                if {'channel': self.event['channel'], 'response': response} not in self.previous_responses:
                    self.send(response, save_response=True)

    def rota_dq_check(self):
        # Tell person on rota via backoffice channel to triage calls, and log any calls to CSC
        # Back Office - Triage
        to_triage_message = ''
        requests_to_triage = self.sdplus_api.request_get_requests('113112_MyView')  # Back Office - Triage
        number_to_triage = len(requests_to_triage)
        if number_to_triage != 0:
            if number_to_triage == 1:
                call_or_calls = 'call'
                is_or_are = 'is'
            else:
                call_or_calls = 'calls'
                is_or_are = 'are'
            to_triage_message = '{0} {1} {2} waiting in the Back Office - Triage queue. '\
                .format(number_to_triage, call_or_calls, is_or_are)
        # To Log to CSC
        to_log_message = ''
        requests_to_log = self.sdplus_api.request_get_requests('Back Office - to log to CSC_QUEUE')
        number_of_requests = len(requests_to_log)
        if number_of_requests != 0:
            if number_of_requests == 1:
                call_or_calls = 'call'
            else:
                call_or_calls = 'calls'
            to_log_message = 'Please log {0} {1} to CSC.'.format(number_of_requests, call_or_calls)
        if to_triage_message or to_log_message:
            message_to_channel = '<@{id}> - {triage}{log}'.format(id=self._rota_get_today_person(),
                                                                  triage=to_triage_message, log=to_log_message)
            self.send(message_to_channel, self.bo_channel)

    @staticmethod
    def _remove_field_from_string(field_list, input_string):
        # returns found field, and string with field removed
        for field in field_list:
            # if field in input_string:
            if field.lower() in input_string.lower():  # case insensitive check
                phrase = re.compile(re.escape(field), re.IGNORECASE)  # case insensitive replace
                return field, phrase.sub('', input_string, 1).strip()
                # return field, input_string.replace(field, '', 1).strip()
        return '', ''

    @staticmethod
    def _remove_case_insensitive(remove, from_string):
        # case insensitive replace
        phrase = re.compile(re.escape(remove), re.IGNORECASE)
        return phrase.sub('', from_string).strip()

    def _slack_get_id(self, real_name):
        # Translate full name (e.g. Simon Crouch) into id (e.g. U1FBNCGLX)
        users = self.sc.api_call('users.list')
        return self._slack_get_value(users, real_name, 'real_name', 'id', 'members')

    def _slack_get_real_name(self, id):
        # Translate id (e.g. U1FBNCGLX) into full name (e.g. Simon Crouch)
        users = self.sc.api_call('users.list')
        return self._slack_get_value(users, id, 'id', 'real_name', 'members')

    @staticmethod
    def _slack_get_value(slack_response, search_value, search_field, return_field, classifier):
        """
        Traverses a slack response to obtain a single value
        :param slack_response: json response from slackclient api_call
        :param search_value: value to search for
        :param search_field: field to search for the value in
        :param return_field: field who's value you want to return
        :param classifier: specific slack identifying string which is found in the slack_response e.g. 'groups'
        :return: string value
        """
        if not slack_response['ok']:
            return False
        for item in slack_response[classifier]:
            if search_field in item and search_value == item[search_field] and return_field in item:
                return item[return_field]

    def inform_bo_of_rota_and_record_stats(self):
        self.rota_inform_bo_of_today_person()
        self.stats_set('backoffice')

responses = [
    "Really? You're really asking me this?!",
    "I'm Lorenzo and I'm tired - TIRED OF YOU! puny human...",
    "Ugh, do i really have to sit here and chat to you?",
    "Don't you have work to do?"
]

you = [
    'you crazy-why-work-at-NBT person',
    "crazy-horse",
    'you super super special person',
    'bae'
]

if __name__ == '__main__':
    rtm = RTM()
    # -t = send test direct message to Simon Crouch
    try:
        if sys.argv[1] == '-t':
            rtm.send('Test message from slack_lorenzobot.py', 'D1FCKCS80')  # D1FCKCS80=Simon IM Channel
            sys.exit(0)
    except IndexError:
        pass

    print('LorenzoBot Version: ' + __version__)
    rtm.send('LorenzoBot is coming online', 'D1FCKCS80')  # D1FCKCS80=Simon IM Channel
    rtm.start()
