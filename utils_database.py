import os

from PyQt5.QtSql import QSqlDatabase, QSqlQuery


class utils_database:

	def __init__(self, plugin_dir, db_config):

		self.plugin_dir = plugin_dir
		self.param = {}
		self.db_config = db_config
		self.db = None
		self.bd_open = False
		self.last_error = None
		self.last_msg = None
		self.num_fields = None
		self.num_records = None


	def open_database(self):
		""" Open database on server """

		if self.bd_open:
			return self.db

		if self.db_config == "":
			self.last_error = "No database connection parameters defined"
			return None

		# has to be available in /usr/lib/x86_64-linux-gnu/qt5/plugins/sqldrivers
		# install libqt5sql5-mysql
		self.db = QSqlDatabase.addDatabase("QMYSQL")
		self.db.setHostName(self.db_config['host'])
		self.db.setPort(self.db_config['port'])
		self.db.setDatabaseName(self.db_config['db'])
		self.db.setUserName(self.db_config['user'])
		self.db.setPassword(self.db_config['passwd'])
		ok = self.db.open()
		if not self.db.isOpen():
			print(self.db.lastError().text())
			self.last_error = f"Not able to make database connection to host {self.db_config['host']}\n\n{self.db.lastError().text()}"
			return None

		self.bd_open = True
		#print("connected to database")
		return self.db


	def close_database(self):
		"""Close database on server """

		if not self.bd_open:
			return True
		self.db.close()
		self.bd_open = False
		return True


	def reset_info(self):
		""" Reset query information values """

		self.last_error = None
		self.last_msg = None
		self.num_fields = None
		self.num_records = None


	def exec_sql(self, sql):
		""" Execute SQL (Insert or Update) """

		print("execute", sql)

		self.reset_info()
		query = QSqlQuery(self.db)
		status = query.exec(sql)
		if not status:
			self.last_error = query.lastError().text()
		return status


	def get_field(self, sql, field):
		""" Execute SQL (Select) and return column of first result """

		self.reset_info()
		query = QSqlQuery(self.db)
		status = query.exec(sql)
		if not status:
			self.last_error = query.lastError().text()
			return None

		record = query.record()
		print(record.count())
		print(record.value(1))
		print(record.value(field))
		return record.value(field)


	def get_rows(self, sql):
		""" Execute SQL (Select) and return rows """

		self.reset_info()
		query = QSqlQuery(self.db)
		status = query.exec(sql)
		if not status:
			self.last_error = query.lastError().text()
			return None

		# Get number of records
		self.num_records = query.size()
		if self.num_records == 0:
			self.last_msg = "No register with selected query"
			return None

		# Get number of fields
		record = query.record()
		self.num_fields = record.count()
		if self.num_fields == 0:
			self.last_msg = "No s'han especificat camps a retornar"
			return None

		rows = []
		while query.next():
			row = []
			for i in range(self.num_fields):
				row.append(query.value(i))
			rows.append(row)

		return rows