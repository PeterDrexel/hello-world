# -*- coding: utf-8 -*-
"""
/***************************************************************************
 VogisSuche
                                 A QGIS plugin
 Lucene-Suche für das VoGIS
                              -------------------
        begin                : 2016-04-27
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Peter Drexel
        email                : peter.drexel@vorarlberg.at
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction
from PyQt5 import QtSql

# Import the code for the DockWidget
from .vogis_suche_dockwidget import VogisSucheDockWidget
import os.path
import datetime
# Initialize Qt resources from file resources.py
from . import resources_rc
pluginVerson = '2018.01.08'

class VogisSuche:
	"""QGIS Plugin Implementation."""

	def __init__(self, iface):
		"""Constructor.

		:param iface: An interface instance that will be passed to this class
			which provides the hook by which you can manipulate the QGIS
			application at run time.
		:type iface: QgsInterface
		"""
		# Save reference to the QGIS interface
		self.iface = iface

		# initialize plugin directory
		self.plugin_dir = os.path.dirname(__file__)

		# initialize locale
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'VogisSuche_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)

			if qVersion() > '4.3.3':
				QCoreApplication.installTranslator(self.translator)

		# Declare instance attributes
		self.actions = []
		self.menu = self.tr('&VoGIS Suche')
		# TODO: We are going to let the user set this up in a future iteration
		self.toolbar = self.iface.addToolBar('VoGIS Suche')
		self.toolbar.setObjectName('VogisSuche')

		#print "** INITIALIZING VogisSuche"

		self.pluginIsActive = False
		self.dockwidget = None


	# noinspection PyMethodMayBeStatic
	def tr(self, message):
		"""Get the translation for a string using Qt translation API.

		We implement this ourselves since we do not inherit QObject.

		:param message: String for translation.
		:type message: str, QString

		:returns: Translated version of message.
		:rtype: QString
		"""
		# noinspection PyTypeChecker,PyArgumentList,PyCallByClass
		return QCoreApplication.translate('VogisSuche', message)


	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):
		"""Add a toolbar icon to the toolbar.

		:param icon_path: Path to the icon for this action. Can be a resource
			path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
		:type icon_path: str

		:param text: Text that should be shown in menu items for this action.
		:type text: str

		:param callback: Function to be called when the action is triggered.
		:type callback: function

		:param enabled_flag: A flag indicating if the action should be enabled
			by default. Defaults to True.
		:type enabled_flag: bool

		:param add_to_menu: Flag indicating whether the action should also
			be added to the menu. Defaults to True.
		:type add_to_menu: bool

		:param add_to_toolbar: Flag indicating whether the action should also
			be added to the toolbar. Defaults to True.
		:type add_to_toolbar: bool

		:param status_tip: Optional text to show in a popup when mouse pointer
			hovers over the action.
		:type status_tip: str

		:param parent: Parent widget for the new action. Defaults None.
		:type parent: QWidget

		:param whats_this: Optional text to show in the status bar when the
			mouse pointer hovers over the action.

		:returns: The action that was created. Note that the action is also
			added to self.actions list.
		:rtype: QAction
		"""

		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			self.toolbar.addAction(action)

		if add_to_menu:
			self.iface.addPluginToMenu(
				self.menu,
				action)

		self.actions.append(action)

		return action


	def initGui(self):
		"""Create the menu entries and toolbar icons inside the QGIS GUI."""

		icon_path = ':/plugins/VogisSuche/icon.png'
		self.add_action(icon_path,text=self.tr('VoGIS Suche'),callback=self.run,parent=self.iface.mainWindow())
		
		# Dock nach dem Laden gleich anzeigen
		# self.run()

	#--------------------------------------------------------------------------

	def onClosePlugin(self):
		"""Cleanup necessary items here when plugin dockwidget is closed"""

		#print "** CLOSING VogisSuche"

		# disconnects
		self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

		# remove this statement if dockwidget is to remain
		# for reuse if plugin is reopened
		# Commented next statement since it causes QGIS crashe
		# when closing the docked window:
		# self.dockwidget = None

		self.pluginIsActive = False


	def unload(self):
		"""Removes the plugin menu item and icon from QGIS GUI."""

		#print "** UNLOAD VogisSuche"

		for action in self.actions:
			self.iface.removePluginMenu(
				self.tr('&VoGIS Suche'),
				action)
			self.iface.removeToolBarIcon(action)
		# remove the toolbar
		del self.toolbar

	#--------------------------------------------------------------------------

	def run(self):
		"""Run method that loads and starts the plugin"""

		if not self.pluginIsActive:
			self.pluginIsActive = True

			#print "** STARTING VogisSuche"

			# dockwidget may not exist if:
			#    first run of plugin
			#    removed on close (see self.onClosePlugin method)
			if self.dockwidget == None:
				# Create the dockwidget (after translation) and keep reference
				self.dockwidget = VogisSucheDockWidget()

			# connect to provide cleanup on closing of dockwidget
			self.dockwidget.closingPlugin.connect(self.onClosePlugin)

			# show the dockwidget
			# TODO: fix to allow choice of dock location
			self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
			self.dockwidget.show()
			

			#Eintrag in die User-Logging-Tabelle
			#Referenz auf die Datenquelle
			#direkt über SQLITE
			now = datetime.datetime.now()
			datumString = now.strftime("%Y-%m-%d %H:%M:%S")
			#QMessageBox.information(self.iface.mainWindow(),"",datumString)
			self.db = QtSql.QSqlDatabase.addDatabase("QSQLITE");
			dbpfad = "//vogis.intra.vlr.gv.at/vogis/Geodaten/_Allgemein/userreg/vogis_suche_db.sqlite"
			self.db.setDatabaseName(dbpfad);

			if os.path.exists(dbpfad) == 1: #sonst erzeugt open eine leer sqllitedb, wollen wir aber nicht

				#nur wenn Öffnen OK
				if  self.db.open():
					import getpass
					username = getpass.getuser().lower()
					abfrage = QtSql.QSqlQuery(self.db)
					abfrage.exec_("SELECT starts  FROM suche_user where user = '" + username + "'")

					if abfrage.first(): #user gefunden
						abfrage.exec_("update suche_user set starts = starts + 1 where user = '" + username + "'")
						abfrage.exec_("update suche_user set version = '"+pluginVerson+"' where user = '" + username + "'")
						abfrage.exec_("update suche_user set lastrun = '"+datumString+"' where user = '" + username + "'")
						self.db.close()
					else: #user nicht gefunden, d.h. noch nicht vorhanden
						abfrage.exec_("insert into suche_user ("'user'", "'starts'", "'version'", "'lastrun'") values ('" + username + "', 1 , '"+pluginVerson+"' , '"+datumString+"' )")

						self.db.close()



