# -*- coding: utf-8 -*-
"""
/***************************************************************************
 VogisSucheDockWidget
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

import os
import sys
import urllib.request, urllib.error, urllib.parse
import qgis.utils  # brauche ich fürs zoomen auf die Auswahl
import datetime
import json

from PyQt5 import QtGui, uic, QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal, QVariant
from PyQt5.QtWidgets import QDockWidget, QApplication, QMessageBox, QTableWidgetItem

from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle, QgsPointXY

# einige wichtige Variablen
nord = 300000
sued = 100000
west = -100000
ost = 0
suchtiefe = 10

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'vogis_suche_dockwidget_base.ui'))


class VogisSucheDockWidget(QDockWidget, FORM_CLASS):

	closingPlugin = pyqtSignal()

	def __init__(self, parent=None):
		"""Constructor."""
		super(VogisSucheDockWidget, self).__init__(parent)
		# Set up the user interface from Designer.
		# After setupUI you can access any designer object by doing
		# self.<objectname>, and you can use autoconnect slots - see
		# http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
		# #widgets-and-dialogs-with-auto-connect
		self.setupUi(self)

		# Slots einrichten
		
		self.ergebnisTw.clicked.connect(self.ergebnisTwitemSelectionChanged) # in die Tabelle geklickt
		# self.connect(self.ergebnisTw, QtCore.SIGNAL("itemClicked(QTableWidgetItem*)"), self.ergebnisTwitemSelectionChanged) # in die Tabelle geklickt __________Python 2 
		
		self.sucheLe.textChanged.connect(self.sucheLeChanged)
		#self.connect(self.sucheLe, QtCore.SIGNAL("textChanged(QString)"), self.sucheLeChanged)	        #Suchbegriff geändert __________Python 2 
		
		self.sucheLe.returnPressed.connect(self.sucheLeReturnPressed)	        #Suchbegriff Enter gedrückt
		#self.connect(self.sucheLe, QtCore.SIGNAL("returnPressed()"), self.sucheLeReturnPressed)	        #Suchbegriff Enter gedrückt __________Python 2 
		
		
	def ergebnisTwitemSelectionChanged(self):
		selectedRows = len(self.ergebnisTw.selectedIndexes ())/ self.ergebnisTw.columnCount()
		if selectedRows > 0:
			self.createMarks()
		
			# da das Canvas-CRS auch nicht-EPSG:31254 sein kann müssen die Punkte ev noch transformiert werden.
			canvas = qgis.utils.iface.mapCanvas()
			cancrs = canvas.mapSettings().destinationCrs()
			srccrs = QgsCoordinateReferenceSystem(31254)
			xform = QgsCoordinateTransform(srccrs, cancrs, QgsProject.instance())
			links = xform.transform(QgsPointXY(west-50,nord+50)).x()
			oben = xform.transform(QgsPointXY(west-50,nord+50)).y()
			rechts  = xform.transform(QgsPointXY(ost+50,sued-50)).x()
			unten  = xform.transform(QgsPointXY(ost+50,sued-50)).y()
			canvas.setExtent (QgsRectangle(links,unten,rechts,oben)) # auf Koordinatenfenster zoomen		
			canvas.refresh()     
	
	def sucheLeReturnPressed(self):
		global suchtiefe
		suchtiefe = 1000000
		self.sucheLeChanged()
		

	def sucheLeChanged(self):
		QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
		global suchtiefe
		Suchtext = self.sucheLe.text().encode('utf-8')
		LuceneSolrUrl = 'http://vogis.cnv.at/solr/geoland/select?q='+urllib.parse.quote(Suchtext)+'&qf=phonetic%5E10.0%20textsuggest%5E30.0%20textng%5E50.0%20extrasearch&wt=json&qt=ac&sort=score%20desc%2Cpopularity%20desc&defType=edismax&q.op=AND&v.template=suggest'
		# LuceneSolrUrl = 'http://vogis.cnv.at/solr/geoland/select?q='+urllib.parse.quote(Suchtext)+'&qf=phonetic%5E10.0%20extrasearch&wt=json&qt=ac&sort=score%20desc%2Cpopularity%20desc&defType=edismax&q.op=AND&v.template=suggest'
		# LuceneSolrUrl = 'http://srv.doris.at/solr/doris/select?q='+urllib.parse.quote(Suchtext)+'&qf=phonetic%5E10.0%20textsuggest%5E30.0%20textng%5E50.0%20extrasearch&wt=json&qt=ac&sort=score%20desc%2Cpopularity%20desc&defType=edismax&q.op=AND&v.template=suggest'
		# LuceneSolrUrl = 'http://gis.ktn.gv.at/solr/mywebgis/select?q='+urllib.parse.quote(Suchtext)+'&qf=phonetic%5E10.0%20textsuggest%5E30.0%20textng%5E50.0%20extrasearch&wt=json&qt=ac&sort=score%20desc%2Cpopularity%20desc&defType=edismax&q.op=AND&v.template=suggest'	
		# QMessageBox.information(self,"",LuceneSolrUrl)
		if len(Suchtext)==0:
			self.ergebnisTw.setColumnCount(0)
			self.ergebnisTw.setRowCount(0)
			self.ergebnisTw.clearSpans()
		else:
			# Da der Lucene-Server - warum auch immer - nicht immer antwortet versuchen wir es einfqach 20 mal...
			for Serveraufrufe in range(20):
				try:
					# Die Tabelle formatieren
					self.ergebnisTw.clearSpans()
					self.ergebnisTw.setColumnCount(8)
					self.ergebnisTw.setRowCount(0)
					self.ergebnisTw.setColumnWidth(0, 0)
					self.ergebnisTw.setColumnWidth(1, 0)
					self.ergebnisTw.setColumnWidth(2, 0)
					self.ergebnisTw.setColumnWidth(3, 0)
					self.ergebnisTw.setColumnWidth(4, 0)
					self.ergebnisTw.setColumnWidth(5, 0)
					self.ergebnisTw.setColumnWidth(6, 0)
					# self.ergebnisTw.setShowGrid(False)
					# die Koordinatenspalten nicht sichtbar machen:
					# self.ergebnisTw.setColumnHidden(1, True)
					self.ergebnisTw.setHorizontalHeaderLabels(['Rechtswert','Hochwert','MinRe','MaxRe','MinHo','MaxHo','Label','Suche läuft...'])
					stylesheet = "QHeaderView::section{Background-color:rgb(190,190,120);border-radius:20px;}"
					self.ergebnisTw.setStyleSheet(stylesheet)
					self.ergebnisTw.repaint()  # wichtig, sonst wird nichts angezeigt bis zum Schluss!

					if suchtiefe == 1000000:

						response = urllib.request.urlopen(LuceneSolrUrl+'&rows='+str(suchtiefe), timeout=30).read()
					else:
						if len(Suchtext)>2:
							suchtiefe = 100
							response = urllib.request.urlopen(LuceneSolrUrl+'&rows='+str(suchtiefe), timeout=30).read()
						else:
							suchtiefe = 20
							response = urllib.request.urlopen(LuceneSolrUrl+'&rows='+str(suchtiefe), timeout=30).read()
						

					#QMessageBox.information(self,"",str(LuceneSolrUrl+'&rows='+str(suchtiefe)))
						
					data  = json.loads(response)	# in response steht das Solr-Json, dieses wird nun zerlegt
					RespBlock = data['response']	# alle Trefferzeilen (ohne Header) als Dict
					RespList = RespBlock['docs']	# Liste aller Trefferzeilen (jede Zeile ist wieder ein Dict)
					
					# die Anzahl gefundener Begriffe aus dem Dict auslesen
					numFound = int(RespBlock['numFound'])
					#QMessageBox.information(self,"",str(numFound))
					#QMessageBox.information(self,"",str(RespList))
					# Tabelle formatieren
					self.ergebnisTw.clearSpans()
					self.ergebnisTw.setRowCount(len(RespList))
					self.ergebnisTw.setHorizontalHeaderLabels(['Rechtswert','Hochwert','MinRe','MaxRe','MinHo','MaxHo','Label','Treffer'])

					Zeile = 0
					for Treffer in RespList:
						MinRe = float(Treffer['minx'])
						MaxRe = float(Treffer['maxx'])
						MinHo = float(Treffer['miny'])
						MaxHo = float(Treffer['maxy'])
						
						try:
							langtext = Treffer['subtext']		#Langtext, kann auch leer sein, daher try
						except:
							langtext = ''
						try:
							labeltext = Treffer['title'][0]		#Label, kann auch leer sein, daher try
						except:
							labeltext = ''
						geo = Treffer['geo']   					#Liste mit Koordinatenpaaren "POINT(-44461.26 251175.92)", es gibt nur ein Koordinatenpaar daher
						geostr = geo[0]		   					#String mit dem Koordinatenpaar, wird nur zerlegt
						geostr = geostr.replace('POINT(','')	#unnötiges wird entfernt
						geostr = geostr.replace(')','')
						geostrlist = geostr.split(' ')			#String wird zerlegt in Liste, Element 0 ist der Rechtswert, Element 1 ist der Hochwert
						rechtswert = float (geostrlist[0])
						hochwert = float (geostrlist[1])
						#QMessageBox.information(self,"",str(rechtswert)+' '+str(hochwert)+ ' '+ langtext + ' '+ labeltext)
						self.ergebnisTw.setItem(Zeile,0,QTableWidgetItem(str(rechtswert)))
						self.ergebnisTw.setItem(Zeile,1,QTableWidgetItem(str(hochwert)))
						self.ergebnisTw.setItem(Zeile,2,QTableWidgetItem(str(MinRe)))
						self.ergebnisTw.setItem(Zeile,3,QTableWidgetItem(str(MaxRe)))
						self.ergebnisTw.setItem(Zeile,4,QTableWidgetItem(str(MinHo)))
						self.ergebnisTw.setItem(Zeile,5,QTableWidgetItem(str(MaxHo)))
						self.ergebnisTw.setItem(Zeile,6,QTableWidgetItem(labeltext))
						
						# Es wird nur noch der Langtext in der Liste dargestellt, wenn dieser leer ist dann wird dort der Labeltext eingefügt
						if len(langtext)>0:
							self.ergebnisTw.setItem(Zeile,7,QTableWidgetItem(langtext))
						else:
							self.ergebnisTw.setItem(Zeile,7,QTableWidgetItem(labeltext))
						Zeile = Zeile + 1
						
					# Tabellenkopf noch einfärben, formatieren unt entsprechend beschriften
					if Zeile < suchtiefe: 	# es wurden nicht alle Treffer gesucht (Suchtiefe nur die ersten 20 oder 100)
						stylesheet = "QHeaderView::section{Background-color:rgb(150,190,150);border-radius:20px;}"
						self.ergebnisTw.setHorizontalHeaderLabels(['Rechtswert','Hochwert','MinRe','MaxRe','MinHo','MaxHo','Label','Treffer (' + str(Zeile) + ')'])

					else: 					# es wurden alle Treffer gesucht und gefunden
						stylesheet = "QHeaderView::section{Background-color:rgb(190,150,150);border-radius:20px;}"
						self.ergebnisTw.setHorizontalHeaderLabels(['Rechtswert','Hochwert','MinRe','MaxRe','MinHo','MaxHo','Label','Treffer (' + str(Zeile) + '/'+str(numFound)+')'])
					self.ergebnisTw.setStyleSheet(stylesheet)

					# Suchtiefe wird wieder zurückgesetzt (wichtig, falls der Aufuf über returnPressed erfolgt - sonst schleift es...)
					suchtiefe = 0
					#QMessageBox.information(self,'',str(L))		
					break	# Juhu, Serverzugriff erfolgreich, also raus aus der For-Schleife
				
				except:
					if Serveraufrufe == 19:			# wenn alle 20 Serverzugriffe scheitern:
						response = ""
						self.ergebnisTw.setHorizontalHeaderLabels(['Rechtswert','Hochwert','MinRe','MaxRe','MinHo','MaxHo','Label','Suchserver antwortet nicht'])
						stylesheet = "QHeaderView::section{Background-color:rgb(240,150,150);border-radius:20px;}"
						self.ergebnisTw.setStyleSheet(stylesheet)
						self.ergebnisTw.repaint()  # wichtig, sonst wird nichts angezeigt bis zum Schluss!
						# Suchtiefe wird wieder zurückgesetzt (wichtig, falls der Aufuf über returnPressed erfolgt - sonst schleift es...)
						suchtiefe = 0
		
		QtWidgets.QApplication.restoreOverrideCursor()
		
	def closeEvent(self, event):
		self.closingPlugin.emit()
		event.accept()


	def createMarks(self):
		global nord,sued,ost,west
	
		layers = list(QgsProject.instance().mapLayers().values())
		# eventuell noch vorhandene alte _Marks-Layer entfernen
		for layer in layers:
			if layer.name() == "_Suchtreffer_":
				QgsProject.instance().removeMapLayer( layer.id() )
		
		# Memory-Layer für die Punkte-Darstellung machen
		vlMrkPunkt = QgsVectorLayer("point?crs=EPSG:31254", "_Suchtreffer_", "memory")
		prMrkPunkt = vlMrkPunkt.dataProvider()
		
		# add fields
		prMrkPunkt.addAttributes( [ 
		QgsField("Label", QVariant.String)])
				
		SelFeatures = self.ergebnisTw.selectedIndexes ()
		ColRe = 0 # Index der Rechtswertspalte
		ColHo = 1 # Index der Hochwertspalte
		ColMinRe = 2 # Index der Spalte mit MinRe
		ColMaxRe = 3 # Index der Spalte mit MinRe
		ColMinHo = 4 # Index der Spalte mit MinHo
		ColMaxHo = 5 # Index der Spalte mit MaxHo
		ColLabel = 6 # Index der Labelspalte
		ColText = 7 # Index der (Lang-)Textspalte
		nord = 0
		sued = 500000
		ost = -100000
		west = 500000
		ListLangText = []
		ListLabel = []
		ListRe = []
		ListHo = []
		for feature in SelFeatures:
			fr = feature.row()
			fc = feature.column()
			# QMessageBox.information(self,u"", 'Zeile: str(fr)+'  Spalte: '+str(fc))
			ft = feature.data()
			if fc==ColRe:
				Rechtswert = float(ft)
				ListRe.append(Rechtswert)
			if fc==ColHo:
				Hochwert = float (ft)
				ListHo.append (Hochwert)
			if fc==ColMinRe:
				MinRe = float (ft)
				if MinRe < west:
					west = MinRe 
			if fc==ColMaxRe:
				MaxRe = float (ft)
				if MaxRe > ost:
					ost = MaxRe 
			if fc==ColMinHo:
				MinHo = float (ft)
				if MinHo < sued:
					sued = MinHo 
			if fc==ColMaxHo:
				MaxHo = float (ft)
				if MaxHo > nord:
					nord = MaxHo
			if fc==ColLabel:
				Label = ft
				ListLabel.append(Label)
			if fc==ColText:
				LangText = ft
				ListLangText.append(LangText)

		
		cc = 0
		for pt in ListRe:
			fet = QgsFeature()
			fet.setGeometry( QgsGeometry.fromPointXY(QgsPointXY(ListRe[cc],ListHo[cc])))
			if len (ListLangText[cc])> len (ListLabel[cc]):
				fet.setAttributes([ListLangText[cc]])
			else:
				fet.setAttributes([ListLabel[cc]])
			prMrkPunkt.addFeatures([fet])
			cc = cc + 1
		if cc > 0:
			vlMrkPunkt.updateFields()
			QgsProject.instance().addMapLayer(vlMrkPunkt)
			vlMrkPunkt.loadNamedStyle(os.path.dirname(os.path.realpath(__file__)) + '/pointmarker.qml')
		vlMrkPunkt.updateExtents()
		vlMrkPunkt.updateFields()
