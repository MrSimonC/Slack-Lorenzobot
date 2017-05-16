import pyodbc
from collections import OrderedDict
__version__ = 1.0
# 06/Feb/15 - amazing, works really well. Finalised 31/Jul/15.
# https://code.google.com/p/pyodbc/wiki/Cursor


class QueryDB:
    def __init__(self, server, database, username, password):
        self.connection = pyodbc.connect('DRIVER={SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s' %
                                         (server, database, username, password))
        self.cursor = self.connection.cursor()

    def exec_sql(self, sql, commit=False):
        """
        Execute SQL code and return array of dicts
        :param sql: SQL code to run
        :param commit: commit data to the database (true/false)
        :return List of ordered dict as rows:
                [OrderedDict([('columnA1', 'value'), ('columnA2', 'value2')]),
                OrderedDict([('columnB1', 'value'), ('columnB2', 'value2')])]
                or empty list if no results
        """
        self.cursor.execute(sql)
        if commit:
            self.cursor.commit()
        results = []
        if self.cursor.description is None:
            return results
        while True:
            cols = [c[0] for c in self.cursor.description]
            for row in self.cursor.fetchall():
                results.append(OrderedDict(list(zip(cols, [x if x is not None else '' for x in row]))))
            if not self.cursor.nextset():
                break
        return results

