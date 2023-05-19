import sqlite3

# Create a ChatGPT database object
class ChatGPTDatabase:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        # This cursor allows you to run different SQL quereis on this database object
        self.cursor = self.conn.cursor()

    def create_table(self, table_name, columns):
        """
        Creates a new table in the database with the given name
        The columns parameter should be a comma-separated string of coukm
        """
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
        self.cursor.execute(create_table_sql)
        self.conn.commit()

    def insert_record(self, table_name, columns, record):
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({record})"
        self.cursor.execute(sql)
        self.conn.commit()

    def retrieve_records(self, table_name, conditions=None):
        select_sql = f"SELECT * FROM {table_name}"
        if conditions:
            select_sql += f" WHERE {conditions}"
        self.cursor.execute(select_sql)
        return self.cursor.fetchall()
    
    def close(self):
        self.cursor.close() 
        self.conn.close()

   
