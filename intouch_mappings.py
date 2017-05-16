from custom_modules.mssql import QueryDB
import os


class InTouchMapping:
    def __init__(self):
        server = 'NBPRODSQL01'
        database = 'LorenzoRI'
        username = 'BackOffice'
        password = os.environ['INTOUCH_LORENZORI_DB']
        self.db = QueryDB(server, database, username, password)

    def get_all_mappings(self):
        mappings = self.db.exec_sql("exec spCheckSP ''")
        return mappings

    def show_match_for_sp(self, sp):
        return [each['InTouchLocation'] for each in self.get_all_mappings() if each['ServicePoint'] == sp]

    def show_match_for_intouchlocation(self, location):
        return [each['ServicePoint'] for each in self.get_all_mappings() if each['InTouchLocation'] == location]

if __name__ == '__main__':
    it = InTouchMapping()
    # mappings = it.get_all_mappings()
    # for each in mappings:
    #     print(each['ServicePoint'] + ' ' + each['InTouchLocation'])
    # print(it.show_match_for_sp('307_DIAB_EHC'))
    # mappings_found = it.show_match_for_sp('307_DIAB_EHC')
    # mappings = ', '.join(mappings_found)
    # print(mappings)
    print(it.show_match_for_intouchlocation('Cardiology'))