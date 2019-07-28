from __future__ import print_function

import typing
from builtins import range
# -*- coding: utf-8 -*-

import os
import sip
from qgis.PyQt import QtCore, QtWidgets, QtWidgets, QtGui
from qgis.PyQt import uic
import numpy as np

from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QAbstractItemView
from qgis.PyQt.QtWidgets import QDialog
from qgis._core import QgsCoordinateReferenceSystem
from qgis._core import QgsFeature
from qgis._core import QgsField
from qgis._core import QgsGeometry
from qgis._core import QgsProject
from qgis._core import QgsPoint
from qgis._core import QgsRectangle
from qgis._core import QgsVectorLayer


from qgis.PyQt.QtCore import * 
from qgis.PyQt.QtWidgets import *
from qgis.core import *


from ..model.utils import decdeg2dms
import subprocess

import qgis
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
sip.setapi('QString',2)
sip.setapi('QVariant',2)

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context.encode('utf8'), text.encode('utf8'), disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context.encode('utf8'), text.encode('utf8'), disambig)

FORMESTACA1_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '../view/ui/Topo_dialog_estacas1.ui'))
FORMGERATRACADO_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '../view/ui/Topo_dialog_gera_tracado_1.ui'))
APLICAR_TRANSVERSAL_DIALOG, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '../view/ui/applyTransDiag.ui'))
SETCTATI_DIALOG, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '../view/ui/setTransPtsIndexes.ui'))
VERTICE_EDIT_DIALOG, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '../view/ui/Topo_dialog-cv.ui'))
SET_ESCALA_DIALOG, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '../view/ui/setEscala.ui'))

rb = QgsRubberBand(iface.mapCanvas(), 1)
premuto = False
point0 = iface.mapCanvas().getCoordinateTransform().toMapCoordinates(0, 0)


class PointTool(QgsMapTool):
    def __init__(self, canvas, ref, method):

        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.estacasUI = ref
        self.method = method
        self.callback = eval('self.estacasUI.%s'%self.method)



    def canvasPressEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()
        self.callback(self.canvas.getCoordinateTransform().toMapCoordinates(x, y))



class Dialog(QtWidgets.QDialog):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        button = QtWidgets.QPushButton('Open Dialog', self)
        button.clicked.connect(self.handleOpenDialog)
        self.resize(300, 200)
        self._dialog = None

    def handleOpenDialog(self):
        if self._dialog is None:
            self._dialog = QtWidgets.QDialog(self)
            self._dialog.resize(200, 100)
        self._dialog.show()


class GeraTracadoUI(QtWidgets.QDialog,FORMGERATRACADO_CLASS):
    def __init__(self, iface):
        super(GeraTracadoUI, self).__init__(None)
        self.iface = iface
        self.setupUi(self)

class EstacasUI(QtWidgets.QDialog,FORMESTACA1_CLASS):
    def __init__(self, iface):
        super(EstacasUI, self).__init__(None)
        self.iface = iface
        self.setupUi(self)
        self.setupUi2(self)
        self.points = []
        self.crs = 1
        self.edit = False
        self.dialog = QtWidgets.QDialog(None)
        self.actual_point = None

    def error(self, msg):
        msgBox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "AVISO",
                                   u"%s" % msg,
                                   QtWidgets.QMessageBox.NoButton, None)
        msgBox.addButton("OK", QtWidgets.QMessageBox.AcceptRole)
        msgBox.exec_()

    def openCSV(self):
        filename = QtWidgets.QFileDialog.getOpenFileName()
        if filename in ["", None]: return None
        fileDB, ok = QtWidgets.QInputDialog.getText(None, "Nome do arquivo", u"Nome do arquivo a ser salvo no projeto:")
        if not ok:
            return None
        return filename, fileDB

    def new(self,recalcular=False,layerName=None,filename=None):
        mapCanvas = self.iface.mapCanvas()
        itens = []
        for i in range(mapCanvas.layerCount() - 1, -1, -1):
            try:
                layer = mapCanvas.layer(i)
                layerName = layer.name()
                itens.append(layerName)
            except:
                pass
        if len(itens) == 0: return None
        if not filename:
            if not recalcular:
                filename, ok = QtWidgets.QInputDialog.getText(None, "Nome do arquivo", u"Nome do arquivo:")
                if not ok:
                    return None
            else:
                filename = ''

        if layerName is None:
            layerList = QgsProject .instance().mapLayersByName(layerName)
            layer = None
            if layerList:
                layer = layerList[-1]
        else:
            itens = []
            for i in range(mapCanvas.layerCount() - 1, -1, -1):
                try:
                    layer = mapCanvas.layer(i)
                    layerName = layer.name()
                    if type(layer) == qgis._core.QgsVectorLayer:
                        itens.append(layerName)
                except:
                    pass
            item, ok = QtWidgets.QInputDialog.getItem(None, "Camada com tracado", u"Selecione a camada com o traçado:",
                                                  itens,
                                                  0, False)
            if not(ok) or not(item):
                return None
            else:
                layerList = QgsProject .instance().mapLayersByName(item)
                layer = None
                if layerList:
                    layer = layerList[0]

        dist, ok = QtWidgets.QInputDialog.getDouble(None, "Distancia", u"Distancia entre estacas:", 20.0, -10000,
                                                10000, 2)
        if not ok or dist<=0:
            return None
        estaca, ok = QtWidgets.QInputDialog.getInt(None, "Estaca Inicial", u"Estaca Inicial:", 0, -10000, 10000, 2)

        if not ok:
            return None
        return filename, layer, dist, estaca

    def fill_table_index(self, files):
        self.tableEstacas.setRowCount(0)
        self.tableEstacas.clearContents()
        for i,f in enumerate(files):
            self.tableEstacas.insertRow(self.tableEstacas.rowCount())
            for j,f2 in enumerate(f):
                tableItem=QtWidgets.QTableWidgetItem(u"%s" % f2)
                tableItem.setFlags(tableItem.flags() ^ Qt.ItemIsEditable)
                self.tableEstacas.setItem(i,j,tableItem)

    def create_line(self,p1,p2,name):
        layer = QgsVectorLayer('LineString?crs=%s'%int(self.crs), name, "memory")
        mycrs = QgsCoordinateReferenceSystem(int(self.crs), 0)
        self.reprojectgeographic = QgsCoordinateTransform(self.iface.mapCanvas().mapSettings().destinationCrs(), mycrs, QgsCoordinateTransformContext())
        pr = layer.dataProvider()
        line = QgsFeature()
        line.setGeometry(QgsGeometry.fromPolyline([QgsPoint(self.reprojectgeographic.transform(point=QgsPointXY(p1))), QgsPoint(self.reprojectgeographic.transform(point=QgsPointXY(p2)))]))
        pr.addFeatures([line])
        #layer.setCrs(QgsCoordinateReferenceSystem(int(self.crs), 0))
        layer.updateExtents()

        QgsProject.instance().addMapLayer(layer)

        return p1, p2

    def create_point(self,p1,name):
        layer = QgsVectorLayer('Point?crs=%s'%int(self.crs), name, "memory")
        mycrs = QgsCoordinateReferenceSystem(int(self.crs), 0)
        self.reprojectgeographic = QgsCoordinateTransform(self.iface.mapCanvas().mapSettings().destinationCrs(), mycrs, QgsCoordinateTransformContext())
        pr = layer.dataProvider()
        point = QgsFeature()
        point.setGeometry(QgsGeometry.fromPoint(QgsPoint(self.reprojectgeographic.transform(point=QgsPointXY(p1)))))
        pr.addFeatures([point])
        #layer.setCrs(QgsCoordinateReferenceSystem(int(self.crs), 0))
        layer.updateExtents()

        QgsProject.instance().addMapLayer(layer)

        return p1

    def drawShapeFileAndLoad(self, crs):
        #Creates a shapefile on the given path and triggers the digitizing menu QActions
        #For editing and saving the LineString
        #This relies on the QActions order on the menu

        fields = QgsFields()
        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("value", QVariant.Double))
        fields.append(QgsField("name", QVariant.String))
        dialog = QtWidgets.QFileDialog()
        dialog.setWindowTitle("Caminho para criar arquivo shapefile")
        dialog.setDefaultSuffix("shp")
        path = QtWidgets.QFileDialog.getSaveFileName(filter="Shapefiles (*.shp)")[0]

        if not path:
            return None

        writer = QgsVectorFileWriter(path, 'UTF-8', fields, QgsWkbTypes.MultiLineString,
                                     QgsCoordinateReferenceSystem('EPSG:' + str(crs)), 'ESRI Shapefile')
        del writer
        self.iface.addVectorLayer(path,"","ogr")

        self.iface.digitizeToolBar().show()
        addLineAction = self.iface.digitizeToolBar().actions()[8]
        toggleEditAction = self.iface.digitizeToolBar().actions()[1]
        if not addLineAction.isChecked():
            toggleEditAction.trigger()
        addLineAction.setChecked(True)
        addLineAction.trigger()


    def get_click_coordenate(self,point, mouse):
        self.actual_point=QgsPoint(point)
        if self.tracado_dlg.txtNorthStart.text().strip()=='':
            self.tracado_dlg.txtNorthStart.setText("%f"%self.actual_point.y())
            self.tracado_dlg.txtEsteStart.setText("%f"%self.actual_point.x())
        elif self.tracado_dlg.txtNorthEnd.text().strip()=='':
            self.tracado_dlg.txtNorthEnd.setText("%f"%self.actual_point.y())
            self.tracado_dlg.txtEsteEnd.setText("%f"%self.actual_point.x())

    def gera_tracado_pontos(self,inicial=False,final=False,callback_inst=None,callback_method=None,crs=None):
        if (not (inicial) and not (final)):
            self.callback = eval('callback_inst.%s' % callback_method)
            self.crs = crs
            self.tracado_dlg_inicial = GeraTracadoUI(self.iface)
            self.tracado_dlg_inicial.lblName.setText("Ponto Inicial")
            self.tracado_dlg_inicial.btnCapture.clicked.connect(self.capture_point_inicial)
            self.tracado_dlg_final = GeraTracadoUI(self.iface)
            self.tracado_dlg_final.lblName.setText("Ponto Final")
            self.tracado_dlg_final.btnCapture.clicked.connect(self.capture_point_final)
        if (not (inicial) and not (final)) or not (final):
            ok = self.tracado_dlg_inicial.exec_()
            if not (ok):
                return None
            else:
                pn = float(self.tracado_dlg_inicial.txtNorth.text().strip().replace(",", "."))
                pe = float(self.tracado_dlg_inicial.txtEste.text().strip().replace(",", "."))
                self.gera_tracado_ponto_inicial(QgsPoint(pe, pn))

        if (not (inicial) and not (final)) or not (inicial):
            ok = self.tracado_dlg_final.exec_()
            if not (ok):
                return None
            else:
                pn = float(self.tracado_dlg_final.txtNorth.text().strip().replace(",", "."))
                pe = float(self.tracado_dlg_final.txtEste.text().strip().replace(",", "."))
                self.gera_tracado_ponto_final(QgsPoint(pe, pn))

        if inicial and final:
            p1n = float(self.tracado_dlg_inicial.txtNorth.text().strip().replace(",", "."))
            p1e = float(self.tracado_dlg_inicial.txtEste.text().strip().replace(",", "."))
            p2n = float(self.tracado_dlg_final.txtNorth.text().strip().replace(",", "."))
            p2e = float(self.tracado_dlg_final.txtEste.text().strip().replace(",", "."))
            self.iface.mapCanvas().setMapTool(None)
            self.callback(pontos=self.create_line(QgsPoint(p1e, p1n), QgsPoint(p2e, p2n), "Diretriz"), parte=1)



    def gera_tracado_ponto_inicial(self,point):
        self.tracado_dlg_inicial.txtNorth.setText("%f"%point.y())
        self.tracado_dlg_inicial.txtEste.setText("%f"%point.x())
        ok = self.tracado_dlg_inicial.exec_()
        if not(ok):
            return None
        else:
            pn = float(self.tracado_dlg_inicial.txtNorth.text().strip().replace(",","."))
            pe = float(self.tracado_dlg_inicial.txtEste.text().strip().replace(",","."))
            self.gera_tracado_ponto_final(QgsPoint(pe, pn))
        
        #self.gera_tracado_pontos(inicial=True)
        self.gera_tracado_pontos(final=True)

    def gera_tracado_ponto_final(self,point):
        self.tracado_dlg_final.txtNorth.setText("%f"%point.y())
        self.tracado_dlg_final.txtEste.setText("%f"%point.x())
        ok = self.tracado_dlg_final.exec_()
        if not(ok):
            return None
        else:
            pn = float(self.tracado_dlg_final.txtNorth.text().strip().replace(",","."))
            pe = float(self.tracado_dlg_final.txtEste.text().strip().replace(",","."))
            #self.gera_tracado_ponto_final(QgsPoint(pe, pn))
        
        #self.gera_tracado_pontos(final=True)
        self.gera_tracado_pontos(inicial=True,final=True)
    
    def capture_point_inicial(self):
        tool = PointTool(self.iface.mapCanvas(),self,'gera_tracado_ponto_inicial')
        self.iface.mapCanvas().setMapTool(tool)

    def capture_point_final(self):
        tool = PointTool(self.iface.mapCanvas(),self,'gera_tracado_ponto_final')
        self.iface.mapCanvas().setMapTool(tool)


    def exit_dialog(self, points, crs):
        self.dialog.close()

        layer = QgsVectorLayer('LineString', self.name_tracado, "memory")
        pr = layer.dataProvider()
        # fix_print_with_import
        print(points)
        anterior = QgsPoint(points[0])
        fets=[]
        for p in points[1:]:
            fet = QgsFeature(layer.fields())
            fet.setGeometry(QgsGeometry.fromPolyline([anterior, QgsPoint(p)]))
            fets.append(fet)
            anterior = QgsPoint(p)
        pr.addFeatures(fets)
        self.crs = crs
        layer.setCrs(QgsCoordinateReferenceSystem(int(crs), 0))
        layer.updateExtents()

        QgsProject.instance().addMapLayer(layer)

    def gera_tracado_vertices(self,pointerEmitter):
        self.iface.mapCanvas().setMapTool(pointerEmitter)
        self.name_tracado = "TracadoNovo"
        self.dialog.resize(200, 100)
        self.dialog.setWindowTitle(u"Traçado")
        self.dialog.btnClose = QtWidgets.QPushButton("Terminar",self.dialog)
        self.dialog.show()
        return self.name_tracado

    def setupUi2(self,Form):
        Form.setObjectName(_fromUtf8(u"Traçado Horizontal"))
        self.tableEstacas.setColumnCount(3)
        self.tableEstacas.setRowCount(0)
        self.tableEstacas.setColumnWidth(0, 54)
        self.tableEstacas.setColumnWidth(1, 360)
        self.tableEstacas.setColumnWidth(2, 200)
        self.tableEstacas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableEstacas.setHorizontalHeaderLabels((u"ID",u"Arquivo",u"Data criação"))



class EstacasIntersec(QtWidgets.QDialog):

    def __init__(self,iface):
        super(EstacasIntersec, self).__init__(None)
        self.iface = iface
        self.setupUi(self)

    def clear(self):
        self.tableWidget.setRowCount(0)
        self.tableWidget.clearContents()

    def saveEstacasCSV(self):
        filename = QtWidgets.QFileDialog.getSaveFileName()
        return filename

    def fill_table(self, xxx_todo_changeme,f=False):
        (estaca,descricao,progressiva,cota) = xxx_todo_changeme
        self.tableWidget.insertRow(self.tableWidget.rowCount())
        k = self.tableWidget.rowCount() - 1
        self.tableWidget.setItem(k, 0, QtWidgets.QTableWidgetItem(u"%s" % estaca))
        self.tableWidget.setItem(k, 1, QtWidgets.QTableWidgetItem(u"%s" % descricao))
        self.tableWidget.setItem(k, 2, QtWidgets.QTableWidgetItem(u"%s" % progressiva))
        self.tableWidget.setItem(k, 3, QtWidgets.QTableWidgetItem(u"%s" % cota))
        '''if not f:
            naz = decdeg2dms(azimute)
            str_az = "%s* %s\' %s\'\'" % (int(naz[0]), int(naz[1]), naz[2])
            self.tableWidget.setItem(k, 6, QtWidgets.QTableWidgetItem(str_az))
        else:'''


    def get_estacas(self):
        estacas = []
        for i in range(self.tableWidget.rowCount()):
            estaca = []
            for j in range(self.tableWidget.columnCount()):
                estaca.append(self.tableWidget.item(i,j).text())
            estacas.append(estaca)
        return estacas

    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8(u"Traçado Horizontal"))
        Form.resize(919, 510)
        self.tableWidget = QtWidgets.QTableWidget(Form)
        self.tableWidget.setGeometry(QtCore.QRect(0, 0, 750, 511))
        self.tableWidget.setObjectName(_fromUtf8("tableWidget"))
        self.modelSource = self.tableWidget.model()


        self.tableWidget.setColumnCount(8)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setHorizontalHeaderLabels((u"Estaca",u"Descrição",u"Progressiva",u"Cota", u"Relevo", u"Norte",u"Este",u"Azimute"))



        self.btnGen = QtWidgets.QPushButton(Form)
        self.btnGen.setText("Tabela de Verticais")
        self.btnGen.setGeometry(QtCore.QRect(755, 16, 180, 45))
        self.btnGen.setObjectName(_fromUtf8("btnGen"))
        #self.btnGen.clicked.connect(self.generate)

        self.btnTrans = QtWidgets.QPushButton(Form)
        self.btnTrans.setText("Definir Sessão Tipo")
        self.btnTrans.setGeometry(QtCore.QRect(760, 50+16, 160, 30))
        self.btnTrans.setObjectName(_fromUtf8("btnTrans"))
        #self.btnEstacas.clicked.connect(self.ref_super.tracado)

        self.btnPrint = QtWidgets.QPushButton(Form)
        self.btnPrint.setText("Imprimir")
        self.btnPrint.setGeometry(QtCore.QRect(760, 16 + 34 * 6, 160, 30))
        self.btnPrint.setObjectName(_fromUtf8("btnPrint"))
        #self.btnEstacas.clicked.connect(self.ref_super.tracado)

        self.btnClean = QtWidgets.QPushButton(Form)
        self.btnClean.setText("Apagar Dados")
        self.btnClean.setGeometry(QtCore.QRect(760, 16 + 34 * 7, 160, 30))
        self.btnClean.setObjectName(_fromUtf8("btnClean"))




        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)



    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Traçado Horizontal", "Traçado Vertial", None))


class EstacasCv(QtWidgets.QDialog):

    def __init__(self,iface):
        super(EstacasCv, self).__init__(None)
        self.iface = iface
        self.setupUi(self)

    def clear(self):
        self.tableWidget.setRowCount(0)
        self.tableWidget.clearContents()

    def saveEstacasCSV(self):
        filename = QtWidgets.QFileDialog.getSaveFileName()
        return filename

    def fill_table(self, xxx_todo_changeme,f=False):
        (estaca,descricao,progressiva,cota) = xxx_todo_changeme
        self.tableWidget.insertRow(self.tableWidget.rowCount())
        k = self.tableWidget.rowCount() - 1
        self.tableWidget.setItem(k, 0, QtWidgets.QTableWidgetItem(u"%s" % estaca))
        self.tableWidget.setItem(k, 1, QtWidgets.QTableWidgetItem(u"%s" % descricao))
        self.tableWidget.setItem(k, 2, QtWidgets.QTableWidgetItem(u"%s" % progressiva))
        self.tableWidget.setItem(k, 3, QtWidgets.QTableWidgetItem(u"%s" % cota))
        '''if not f:
            naz = decdeg2dms(azimute)
            str_az = "%s* %s\' %s\'\'" % (int(naz[0]), int(naz[1]), naz[2])
            self.tableWidget.setItem(k, 6, QtWidgets.QTableWidgetItem(str_az))
        else:'''


    def get_estacas(self):
        estacas = []
        for i in range(self.tableWidget.rowCount()):
            estaca = []
            for j in range(self.tableWidget.columnCount()):
                estaca.append(self.tableWidget.item(i,j).text())
            estacas.append(estaca)
        return estacas


    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8(u"Traçado Horizontal"))
        Form.resize(919, 510)
        self.tableWidget = QtWidgets.QTableWidget(Form)
        self.tableWidget.setGeometry(QtCore.QRect(0, 0, 750, 511))
        self.tableWidget.setObjectName(_fromUtf8("tableWidget"))
        self.modelSource = self.tableWidget.model()
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setHorizontalHeaderLabels((u"Estaca",u"Descrição",u"Progressiva",u"Cota"))

        self.btnGen = QtWidgets.QPushButton(Form)
        self.btnGen.setText("Tabela de intersecção")
        self.btnGen.setGeometry(QtCore.QRect(755, 16, 180, 45))
        self.btnGen.setObjectName(_fromUtf8("btnGen"))
        #self.btnGen.clicked.connect(self.generate)

        self.btnTrans = QtWidgets.QPushButton(Form)
        self.btnTrans.setText("Definir Sessão Tipo")
        self.btnTrans.setGeometry(QtCore.QRect(760, 50+16, 160, 30))
        self.btnTrans.setObjectName(_fromUtf8("btnTrans"))
        #self.btnEstacas.clicked.connect(self.ref_super.tracado)

        self.btnPrint = QtWidgets.QPushButton(Form)
        self.btnPrint.setText("Imprimir")
        self.btnPrint.setGeometry(QtCore.QRect(760, 16 + 34 * 6, 160, 30))
        self.btnPrint.setObjectName(_fromUtf8("btnPrint"))
        #self.btnEstacas.clicked.connect(self.ref_super.tracado)

        self.btnClean = QtWidgets.QPushButton(Form)
        self.btnClean.setText("Apagar Dados")
        self.btnClean.setGeometry(QtCore.QRect(760, 16 + 34 * 7, 160, 30))
        self.btnClean.setObjectName(_fromUtf8("btnClean"))

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

        self.Form=Form

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Traçado Horizontal", "Traçado Vertial", None))



class Estacas(QtWidgets.QDialog):

    def __init__(self,iface):
        super(Estacas, self).__init__(None)
        self.iface = iface
        self.type="horizontal"
        self.setupUi(self)

    def clear(self):
        self.tableWidget.setRowCount(0)
        self.tableWidget.clearContents()

    def saveEstacasCSV(self):
        filename = QtWidgets.QFileDialog.getSaveFileName()
        return filename

    def fill_table(self, xxx_todo_changeme,f=False):
        (estaca,descricao,progressiva,norte,este,cota,azimute) = xxx_todo_changeme
        self.tableWidget.insertRow(self.tableWidget.rowCount())
        k = self.tableWidget.rowCount() - 1
        self.tableWidget.setItem(k, 0, QtWidgets.QTableWidgetItem(u"%s" % estaca))
        self.tableWidget.setItem(k, 1, QtWidgets.QTableWidgetItem(u"%s" % descricao))
        self.tableWidget.setItem(k, 2, QtWidgets.QTableWidgetItem(u"%s" % progressiva))
        self.tableWidget.setItem(k, 3, QtWidgets.QTableWidgetItem(u"%s" % norte))
        self.tableWidget.setItem(k, 4, QtWidgets.QTableWidgetItem(u"%s" % este))
        self.tableWidget.setItem(k, 5, QtWidgets.QTableWidgetItem(u"%s" % cota))
        '''if not f:
            naz = decdeg2dms(azimute)
            str_az = "%s* %s\' %s\'\'" % (int(naz[0]), int(naz[1]), naz[2])
            self.tableWidget.setItem(k, 6, QtWidgets.QTableWidgetItem(str_az))
        else:'''
        self.tableWidget.setItem(k, 6, QtWidgets.QTableWidgetItem(u"%s" % azimute))

        for j in range(0,7):
            cell_item = self.tableWidget.item(k, j)
            cell_item.setFlags(cell_item.flags() ^ Qt.ItemIsEditable)

    def get_estacas(self):
        estacas = []
        for i in range(self.tableWidget.rowCount()):
            estaca = []
            for j in range(self.tableWidget.columnCount()):
                estaca.append(self.tableWidget.item(i,j).text())
            estacas.append(estaca)
        return estacas

    def plotar(self):
        vl = QgsVectorLayer("Point", "temporary_points", "memory")
        pr = vl.dataProvider()

        # Enter editing mode
        vl.startEditing()

        # add fields
        pr.addAttributes([QgsField("estaca", QVariant.String), QgsField("descrição", QVariant.String),
                          QgsField("north", QVariant.String), QgsField("este", QVariant.String),
                          QgsField("cota", QVariant.String), QgsField("azimite", QVariant.String)])
        fets = []

        for r in range(self.tableWidget.rowCount()):
            ident = self.tableWidget.item(r, 0).text()
            if ident in ["", None]: break
            fet = QgsFeature(vl.pendingFields())
            n = 0.0
            e = 0.0
            try:
                es = self.tableWidget.item(r, 0).text()
                d = self.tableWidget.item(r, 1).text()
                n = float(self.tableWidget.item(r, 3).text())
                e = float(self.tableWidget.item(r, 4).text())
                c = float(self.tableWidget.item(r, 5).text())
                a = self.tableWidget.item(r, 6).text()
            except:
                break
            fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(e, n)))
            fet.setAttributes([es, d, n, e, c, a])
            fets.append(fet)
        pr.addFeatures(fets)
        vl.commitChanges()
        QgsProject .instance().addMapLayer(vl)

    def openTIFF(self):
        mapCanvas = self.iface.mapCanvas()
        itens = []
        for i in range(mapCanvas.layerCount() - 1, -1, -1):
            try:
                layer = mapCanvas.layer(i)
                layerName = layer.name()
                if type(layer)==qgis._core.QgsRasterLayer:
                    itens.append(layerName)
            except:
                pass
        item, ok = QtWidgets.QInputDialog.getItem(None, "Camada com tracado", u"Selecione o raster com as elevações:",
                                              itens,
                                              0, False)
        if not(ok) or not(item):
            return None
        else:
            layerList = QgsProject .instance().mapLayersByName(item)
            layer = None
            if layerList:
                layer = layerList[0]

        filename = layer.source()
        #filename = QtWidgets.QFileDialog.getOpenFileName(filter="Image files (*.tiff *.tif)")

        return filename
        
    def openDXF(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(filter="Autocad files (*.dxf)")
        return filename
        
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8(u"Traçado Horizontal"))
        Form.resize(919, 510)
        self.tableWidget = QtWidgets.QTableWidget(Form)
        self.tableWidget.setGeometry(QtCore.QRect(0, 0, 761, 511))
        self.tableWidget.setObjectName(_fromUtf8("tableWidget"))
        self.modelSource = self.tableWidget.model()
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setHorizontalHeaderLabels((u"Estaca",u"Descrição",u"Progressiva",u"Norte",u"Este",u"Cota",u"Azimute"))

        self.btnRead = QtWidgets.QPushButton(Form)
        self.btnRead.setText("Abrir Arquivo")
        self.btnRead.setGeometry(QtCore.QRect(769, 16, 143, 30))
        self.btnRead.setObjectName(_fromUtf8("btnRead"))
        #self.btnRead.clicked.connect(self.carrega)

        self.btnEstacas = QtWidgets.QPushButton(Form)
        self.btnEstacas.setText("Recalcular Estacas")
        self.btnEstacas.setGeometry(QtCore.QRect(769, 50, 143, 30))
        self.btnEstacas.setObjectName(_fromUtf8("btnEstacas"))
        #self.btnEstacas.clicked.connect(self.ref_super.tracado)

        self.btnLayer = QtWidgets.QPushButton(Form)
        self.btnLayer.setText("Plotar")
        self.btnLayer.setGeometry(QtCore.QRect(769, 84, 143, 30))
        self.btnLayer.setObjectName(_fromUtf8("btnLayer"))
        #self.btnLayer.clicked.connect(self.plot)

        self.btnPerfil = QtWidgets.QPushButton(Form)
        self.btnPerfil.setText("Perfil do trecho")
        self.btnPerfil.setGeometry(QtCore.QRect(769, 118, 143, 30))
        self.btnPerfil.setObjectName(_fromUtf8("btnPerfil"))
        #self.btnPerfil.clicked.connect(self.perfil)

        self.btnSaveCSV = QtWidgets.QPushButton(Form)
        self.btnSaveCSV.setText("Salvar em CSV")
        self.btnSaveCSV.setGeometry(QtCore.QRect(769, 152, 143, 30))
        self.btnSaveCSV.setObjectName(_fromUtf8("btnSave"))
        #self.btnSave.clicked.connect(self.save)
        self.btnSave = QtWidgets.QPushButton(Form)
        self.btnSave.setText("Salvar")
        self.btnSave.setGeometry(QtCore.QRect(769, 186, 143, 30))
        self.btnSave.setObjectName(_fromUtf8("btnSave"))

        self.btnCurva = QtWidgets.QPushButton(Form)
        self.btnCurva.setText("Curvas")
        self.btnCurva.setGeometry(QtCore.QRect(769, 220, 143, 30))
        self.btnCurva.setObjectName(_fromUtf8("btnCurva"))
        #self.btnCurva.clicked.connect(self.perfil)

     
        self.btnCotaTIFF = QtWidgets.QPushButton(Form)
        self.btnCotaTIFF.setText("Obter Cotas\nvia GeoTIFF")
        self.btnCotaTIFF.setGeometry(QtCore.QRect(769, 300, 143, 60))
        self.btnCotaTIFF.setObjectName(_fromUtf8("btnCotaTIFF"))

        self.btnCotaPC = QtWidgets.QPushButton(Form)
        self.btnCotaPC.setText("Obter Cotas\nvia Pontos cotados\nDXF")
        self.btnCotaPC.setGeometry(QtCore.QRect(769, 375, 143,60))
        self.btnCotaPC.setObjectName(_fromUtf8("btnCotaPC"))


        self.btnCota = QtWidgets.QPushButton(Form)
        self.btnCota.setText("Obter Cotas\nvia Google")
        self.btnCota.setGeometry(QtCore.QRect(769, 450, 143, 60))
        self.btnCota.setObjectName(_fromUtf8("btnCota"))

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Traçado Horizontal", "Traçado Horizontal", None))


class closeDialog(QtWidgets.QDialog):
    save = QtCore.pyqtSignal()
    dischart = QtCore.pyqtSignal()
    cancel = QtCore.pyqtSignal()

    def __init__(self, *args, **kwds):
        super(closeDialog, self).__init__(*args, **kwds)
        self.wasCanceled=False
        self.setupUI()

    def setupUI(self):

        self.setWindowTitle("Fechar")
        label = QtWidgets.QLabel(u"Deseja salvar suas alterações?")
        btnSave=QtWidgets.QPushButton(self)       
        btnSave.setText("Sim")
        btnSave.setToolTip("Salvar o perfil vertical desenhado")
        btnSave.clicked.connect(self.__exitSave)


        btnNot=QtWidgets.QPushButton(self)       
        btnNot.setText(u"Não")
        btnNot.setToolTip(u"Descartar alterações")
        btnNot.clicked.connect(self.__exitNotSave)


        btnCancel=QtWidgets.QPushButton(self)       
        btnCancel.setText("Cancelar")
        btnCancel.setToolTip("Voltar para Janela de desenho")
        btnCancel.clicked.connect(self.__exitCancel)


        Vlayout=QtWidgets.QVBoxLayout()
        HLayout=QtWidgets.QHBoxLayout()

        Vlayout.addWidget(label)
        HLayout.addWidget(btnSave)
        HLayout.addWidget(btnNot)
        HLayout.addWidget(btnCancel)
        Vlayout.addLayout(HLayout)

        self.setLayout(Vlayout)



    def __exitSave(self):
        self.save.emit()
        self.close()
    def __exitNotSave(self):
        self.dischart.emit()
        self.close()
    def __exitCancel(self):
        self.cancel.emit()
        self.close()

 


class rampaDialog(QtWidgets.QDialog):
    def __init__(self, roi, segment, pos):
        super(rampaDialog, self).__init__(None)
        self.setWindowTitle(u"Modificar Rampa")
        self.roi=roi
        self.segment=segment
        self.pos=pos
        self.setupUI()



    def setupUI(self):
        r=[]
        for handle in self.roi.getHandles():
            r.append(handle)
        
        self.firstHandle=r[0]
        self.lastHandle=r[len(r)-1]
 
        H1layout=QtWidgets.QHBoxLayout()
        H2layout=QtWidgets.QHBoxLayout()
        H3layout=QtWidgets.QHBoxLayout()
        Vlayout=QtWidgets.QVBoxLayout(self)

        label=QtWidgets.QLabel("Modificar Rampa")

        Incl=QtWidgets.QLineEdit()
        compr=QtWidgets.QLineEdit()
        cota=QtWidgets.QLineEdit()
        abscissa=QtWidgets.QLineEdit()
        InclLbl=QtWidgets.QLabel(u"Inclinação: ")
        posInclLbl=QtWidgets.QLabel(u"%")
        comprLbl=QtWidgets.QLabel(u"Comprimento: ")
        poscomprLbl=QtWidgets.QLabel(u"m")
        cotaLbl=QtWidgets.QLabel(u"Cota:      ")
        poscotaLbl=QtWidgets.QLabel(u"m")
        abscissalbl=QtWidgets.QLabel(u"Distância Horizontal: ")
        posabscissaLbl=QtWidgets.QLabel(u"m")

        
        h1 = self.segment.handles[0]['item']
        h2 = self.segment.handles[1]['item']

        self.h1=h1
        self.h2=h2

        self.initialPos=[h1.pos(),h2.pos()]

        b1 = QtWidgets.QPushButton("ok",self)
        b1.clicked.connect(self.finishDialog)
        b2 = QtWidgets.QPushButton("cancelar", self)
        b2.clicked.connect(lambda: self.cleanClose())

        H1layout.addWidget(InclLbl)
        H1layout.addWidget(Incl)
        H1layout.addWidget(posInclLbl)
        H1layout.addItem(QtWidgets.QSpacerItem(80,20,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        H1layout.addWidget(comprLbl)
        H1layout.addWidget(compr)
        H1layout.addWidget(poscomprLbl)
        H1layout.addItem(QtWidgets.QSpacerItem(80,20,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        H2layout.addWidget(cotaLbl)
        H2layout.addWidget(cota)
        H2layout.addWidget(poscotaLbl)
        H2layout.addItem(QtWidgets.QSpacerItem(80,20,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        H2layout.addWidget(abscissalbl)
        H2layout.addWidget(abscissa)
        H2layout.addWidget(posabscissaLbl)
        H2layout.addItem(QtWidgets.QSpacerItem(80,20,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        Vlayout.addWidget(label)
        Vlayout.addLayout(H1layout)
        Vlayout.addLayout(H2layout)
        H3layout.addItem(QtWidgets.QSpacerItem(80,20,QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))
        H3layout.addWidget(b1)
        H3layout.addWidget(b2)
        Vlayout.addLayout(H3layout)

        self.InclText=Incl       
        self.Incl=100*(h2.pos().y()-h1.pos().y())/(h2.pos().x()-h1.pos().x())
        self.comprText=compr
        self.compr=np.sqrt((h2.pos().y()-h1.pos().y())**2+(h2.pos().x()-h1.pos().x())**2)
        self.cotaText=cota
        self.cota=h2.pos().y()
        self.abscissaText=abscissa
        self.abscissa=h2.pos().x()

        Incl.setValidator(QtGui.QDoubleValidator())
        compr.setValidator(QtGui.QDoubleValidator())
        cota.setValidator(QtGui.QDoubleValidator())
        abscissa.setValidator(QtGui.QDoubleValidator())

        Incl.setText(str(round(self.Incl,2)))
        compr.setText(str(round(self.compr,2)))
        cota.setText(str(round(self.cota,2)))
        abscissa.setText(str(round(self.abscissa,2)))

        compr.textChanged.connect(self.updateCompr)
        cota.textChanged.connect(self.updateCota)
        abscissa.textChanged.connect(self.updateAbscissa)
        Incl.textChanged.connect(self.updateIncl)

        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.isBeingModified=False 


    def updateCompr(self):
        try:
            if not self.isBeingModified:
                c=self.compr
                self.compr=round(float(self.comprText.text()), 2)
                dc=self.compr-c
                self.cota=round(self.cota+np.sin(np.deg2rad(self.Incl))*dc, 2)
                self.abscissa=round(self.abscissa+np.cos(np.deg2rad(self.Incl))*dc, 2)
                self.update()
                self.redefineUI(1)

        except ValueError:
            pass

     
        
    def updateCota(self):
        try:
            if not self.isBeingModified:  
                self.cota=round(float(self.cotaText.text()), 2)
                self.update()
                self.compr=round(np.sqrt((self.h2.pos().y()-self.h1.pos().y())**2+(self.h2.pos().x()-self.h1.pos().x())**2), 2)
                self.Incl=round(100*(self.h2.pos().y()-self.h1.pos().y())/(self.h2.pos().x()-self.h1.pos().x()), 2)
                self.redefineUI(2)
        except ValueError:
            pass


    def updateAbscissa(self):
        try:
            if not self.isBeingModified:
                self.abscissa=round(float(self.abscissaText.text()), 2)
                self.update()
                self.compr=round(np.sqrt((self.h2.pos().y()-self.h1.pos().y())**2+(self.h2.pos().x()-self.h1.pos().x())**2), 2)
                self.Incl=round(100*(self.h2.pos().y()-self.h1.pos().y())/(self.h2.pos().x()-self.h1.pos().x()), 2)
                self.redefineUI(3)
        except ValueError:
            pass


    def updateIncl(self):
        try:
            if not self.isBeingModified:
               self.Incl=round(float(self.InclText.text()), 2)
               self.cota=round(np.sin(np.deg2rad(self.Incl))*self.compr+self.h1.pos().y(), 2)
               self.abscissa=round(np.cos(np.deg2rad(self.Incl))*self.compr+self.h1.pos().x(), 2)
               self.update()
               self.redefineUI(4)
        except ValueError:
            pass

       
    def update(self): 

        self.h2.setPos(self.abscissa, self.cota)


        if self.firstHandle == self.h2:
            self.firstHandle.setPos(self.initialPos[1].x(),self.cota)   
            self.Incl=round(100*(self.h2.pos().y()-self.h1.pos().y())/(self.h2.pos().x()-self.h1.pos().x())   , 2)
            self.compr=round(np.sqrt((self.h2.pos().y()-self.h1.pos().y())**2+(self.h2.pos().x()-self.h1.pos().x())**2)   , 2)
            self.cota=round(self.h2.pos().y(), 2)
            self.abscissa=round(self.h2.pos().x(), 2)
            self.cotaText.setText(str(self.cota))
            self.abscissaText.setText(str(self.abscissa))

        if self.lastHandle == self.h2:
            self.lastHandle.setPos(self.initialPos[1].x(),self.cota)
            self.Incl=round(100*(self.h2.pos().y()-self.h1.pos().y())/(self.h2.pos().x()-self.h1.pos().x())   , 2)
            self.compr=round(np.sqrt((self.h2.pos().y()-self.h1.pos().y())**2+(self.h2.pos().x()-self.h1.pos().x())**2)   , 2)
            self.cota=round(self.h2.pos().y(), 2)
            self.abscissa=round(self.h2.pos().x(), 2)
            self.cotaText.setText(str(self.cota))
            self.abscissaText.setText(str(self.abscissa))

    
    def redefineUI(self, elm):
        self.isBeingModified=True

        if elm==1:       
            self.cotaText.setText(str(round(self.cota,2)))
            self.abscissaText.setText(str(round(self.abscissa,2)))
            self.InclText.setText(str(round(self.Incl,2)))
        elif elm==2:
            self.comprText.setText(str(round(self.compr,2)))
            self.abscissaText.setText(str(round(self.abscissa,2)))
            self.InclText.setText(str(round(self.Incl,2)))
        elif elm==3:           
            self.comprText.setText(str(round(self.compr,2)))
            self.cotaText.setText(str(round(self.cota))   ,2  )
            self.InclText.setText(str(round(self.Incl,2)))
        elif elm==4:           
            self.comprText.setText(str(round(self.compr,2)))
            self.cotaText.setText(str(round(self.cota,2)))
            self.abscissaText.setText(str(round(self.abscissa,2)))
           

        self.isBeingModified=False


    def finishDialog(self):
        self.close()
    
    def cleanClose(self):
        self.h2.setPos(self.initialPos[1].x(),self.initialPos[1].y())
        self.close()



class ssRampaDialog(rampaDialog):
    def __init__(self, roi, segment, pos):
        super(ssRampaDialog, self).__init__(roi, segment, pos)
        self.setWindowTitle("Modificar Elemento")

    def setupUI(self):
        r = []
        for handle in self.roi.getHandles():
            r.append(handle)

        self.firstHandle = r[0]
        self.lastHandle = r[len(r) - 1]

        H1layout = QtWidgets.QHBoxLayout()
        H2layout = QtWidgets.QHBoxLayout()
        H3layout = QtWidgets.QHBoxLayout()
        Vlayout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("Modificar Rampa")

        Incl = QtWidgets.QLineEdit()
        compr = QtWidgets.QLineEdit()
        cota = QtWidgets.QLineEdit()
        abscissa = QtWidgets.QLineEdit()
        InclLbl = QtWidgets.QLabel(u"Inclinação: ")
        posInclLbl = QtWidgets.QLabel(u"%")
        comprLbl = QtWidgets.QLabel(u"Comprimento: ")
        poscomprLbl = QtWidgets.QLabel(u"m")
        cotaLbl = QtWidgets.QLabel(u"Cota:      ")
        poscotaLbl = QtWidgets.QLabel(u"m")
        abscissalbl = QtWidgets.QLabel(u"Distância até o eixo")
        posabscissaLbl = QtWidgets.QLabel(u"m")

        h1 = self.segment.handles[0]['item']
        h2 = self.segment.handles[1]['item']

        self.h1 = h1
        self.h2 = h2

        self.initialPos = [h1.pos(), h2.pos()]

        b1 = QtWidgets.QPushButton("ok", self)
        b1.clicked.connect(self.finishDialog)
        b2 = QtWidgets.QPushButton("cancelar", self)
        b2.clicked.connect(lambda: self.cleanClose())

        H1layout.addWidget(InclLbl)
        H1layout.addWidget(Incl)
        H1layout.addWidget(posInclLbl)
        H1layout.addItem(QtWidgets.QSpacerItem(80, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        H1layout.addWidget(comprLbl)
        H1layout.addWidget(compr)
        H1layout.addWidget(poscomprLbl)
        H1layout.addItem(QtWidgets.QSpacerItem(80, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        H2layout.addWidget(cotaLbl)
        H2layout.addWidget(cota)
        H2layout.addWidget(poscotaLbl)
        H2layout.addItem(QtWidgets.QSpacerItem(80, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        H2layout.addWidget(abscissalbl)
        H2layout.addWidget(abscissa)
        H2layout.addWidget(posabscissaLbl)
        H2layout.addItem(QtWidgets.QSpacerItem(80, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        Vlayout.addWidget(label)
        Vlayout.addLayout(H1layout)
        Vlayout.addLayout(H2layout)
        H3layout.addItem(QtWidgets.QSpacerItem(80, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))
        H3layout.addWidget(b1)
        H3layout.addWidget(b2)
        Vlayout.addLayout(H3layout)

        self.InclText = Incl
        self.Incl = 100 * (h2.pos().y() - h1.pos().y()) / (h2.pos().x() - h1.pos().x())
        self.comprText = compr
        self.compr = np.sqrt((h2.pos().y() - h1.pos().y()) ** 2 + (h2.pos().x() - h1.pos().x()) ** 2)
        self.cotaText = cota
        self.cota = h2.pos().y()
        self.abscissaText = abscissa
        self.abscissa = h2.pos().x()

        Incl.setValidator(QtGui.QDoubleValidator())
        compr.setValidator(QtGui.QDoubleValidator())
        cota.setValidator(QtGui.QDoubleValidator())
        abscissa.setValidator(QtGui.QDoubleValidator())

        Incl.setText(str(round(self.Incl, 2)))
        compr.setText(str(round(self.compr, 2)))
        cota.setText(str(round(self.cota, 2)))
        abscissa.setText(str(round(self.abscissa, 2)))

        compr.textChanged.connect(self.updateCompr)
        cota.textChanged.connect(self.updateCota)
        abscissa.textChanged.connect(self.updateAbscissa)
        Incl.textChanged.connect(self.updateIncl)

        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.isBeingModified = False


class cvEdit(QtWidgets.QDialog, VERTICE_EDIT_DIALOG):
    def __init__(self, iface):
        super(cvEdit, self).__init__(None)
        self.iface = iface
        self.setupUi(self)


    def removeCv(self, iface):
        self.groupBox_2.setFlat(True)
        self.groupBox_2.setStyleSheet("border:1;")

        self.pushButton.hide()
        self.widget1.hide()
        self.widget2.hide()
        self.widget3.hide()
        self.widget4.hide()
        self.groupBox_2.setTitle('')


class ApplyTransDialog(QtWidgets.QDialog, APLICAR_TRANSVERSAL_DIALOG):
    firstCb: QtWidgets.QComboBox
    secondCb: QtWidgets.QComboBox

    def __init__(self, iface, prog):
        super(ApplyTransDialog, self).__init__(None)
        self.iface=iface
        self.setupUi(self)
        self.progressiva=prog
        self.progressivas=None
        self.setupUi2()

    def setupUi2(self):
        self.firstCb.addItems(list(map(str, self.progressiva)))
        self.firstCb.currentIndexChanged.connect(self.setSecondCb)
        self.setSecondCb()

    def setSecondCb(self):
        self.secondCb.addItems(list(map(str, self.progressiva[self.firstCb.currentIndex()+1:])))
        self.secondCb.currentIndexChanged.connect(self.setIndexes)
        self.setIndexes()

    def setIndexes(self):
        self.progressivas=[self.firstCb.currentIndex(),self.secondCb.currentIndex()+self.firstCb.currentIndex()+1]


class SetCtAtiDialog(QtWidgets.QDialog, SETCTATI_DIALOG):
    firstCb: QtWidgets.QComboBox
    secondCb: QtWidgets.QComboBox

    def __init__(self, iface, prog):
        super(SetCtAtiDialog, self).__init__(None)
        self.iface=iface
        self.setupUi(self)
        self.roiIndexes=[]
        self.firstOptions=[]
        self.secondOptions=[]
        for i, _ in enumerate(prog):
            self.roiIndexes.append(i)
            self.firstOptions.append(i+1)

        self.indices=None
        self.setupUi2()

    def setupUi2(self):
        self.firstCb.addItems(list(map(str, self.firstOptions)))
        self.firstCb.currentIndexChanged.connect(self.setIndexes)
        self.secondCb.addItems(list(map(str, self.firstOptions)))
        self.secondCb.currentIndexChanged.connect(self.setIndexes)

    def setIndexes(self):
        try:
            self.cti=int(self.firstCb.currentText())
            self.ati=int(self.secondCb.currentText())
        except:
            pass


#TODO convert to relative scale
class setEscalaDialog(QtWidgets.QDialog, SET_ESCALA_DIALOG):
    def __init__(self, iface):
        super(setEscalaDialog, self).__init__(None)
        self.iface=iface
        self.setupUi(self)
        self.vb=self.iface.vb
        self.x.setValidator(QtGui.QDoubleValidator())
        self.y.setValidator(QtGui.QDoubleValidator())
        self.x.setText('1.0')
        self.y.setText('1.0')
        self.x.returnPressed.connect(self.changed)
        self.y.returnPressed.connect(self.changed)
        self.zoomBtn.clicked.connect(self.zoom)

    def getX(self):
        return float(self.x.text())

    def getY(self):
        return float(self.y.text())


    def zoom(self):
        self.vb.autoRange()

    def changed(self):
        self.vb.scaleBy((self.getX(),self.getY()))



