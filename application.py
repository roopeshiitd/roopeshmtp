import sys
from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt
import pyqtgraph as pg
import numpy as np
from scipy.signal import butter,lfilter,freqz,argrelextrema
from scipy.interpolate import interp1d
import time
import serial
from collections import deque
from PyQt4.QtCore import QTime,QTimer
import serial.tools.list_ports

class TimeAxisItem(pg.AxisItem):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

    def tickStrings(self,values,scale,spacing):
        return [QTime().addMSecs(value).toString('mm:ss') for value in values]
    
def _translate(context,text,disambig):
    return QtGui.QApplication.translate(context,text,disambig)
class Window(QtGui.QMainWindow):
    def __init__(self):
        super(Window,self).__init__()
        self.setGeometry(50,50,500,300)
        self.setWindowTitle("Respiratory analysis")
        self.ser=serial.Serial('COM35',4800)
        self.menu()
        self.home()
    def menu(self):
        #--------------------Complete Menus------------------
        mainMenu=self.menuBar()
        mainMenu.setStatusTip('Select Options from main menu')
        fileMenu=mainMenu.addMenu('&File')
        fileMenu.setStatusTip('Select Options from File Menu')
        windowMenu=mainMenu.addMenu('&Plot')
        windowMenu.setStatusTip('Select Options from Window Menu')
        connectionMenu=mainMenu.addMenu('&Connection')
        connectionMenu.setStatusTip('Select Options from Connection Menu')
        helpMenu=mainMenu.addMenu('&Help')
        helpMenu.setStatusTip('Select for help')
        #----------------File Menus--------------------------------------
        #--------------Exit Action---------------------------------------
        exitAction=QtGui.QAction("&Exit",self)
        exitAction.setShortcut("Ctrl + Q")
        exitAction.setStatusTip("Leave the Application")
        exitAction.triggered.connect(self.close_application)
        fileMenu.addAction(exitAction)
        #---------------------------------------------------
        #----------------------------------------------------------------
        #-----------------Plot Menus-----------------------------------
        #----------------------------------------------------------------
        zoomin=QtGui.QAction('&Zoom In',self)
        zoomin.setStatusTip("Click to Zoom In")
        zoomin.setShortcut("Ctrl + =")
        zoomin.triggered.connect(self.zoom_in)
        windowMenu.addAction(zoomin)
        zoomout=QtGui.QAction('&Zoom Out',self)
        zoomout.setStatusTip("Click to Zoom Out")
        zoomout.setShortcut("Ctrl + -")
        zoomout.triggered.connect(self.zoom_out)
        windowMenu.addAction(zoomout)
        #----------------------------------------------------------------
        #----------------------------------------------------------------
        #----------------Connection Menus--------------------------------
        #----------------COM Ports---------------------------------------
        comMenu=connectionMenu.addMenu('&COM Ports')
        com=list(serial.tools.list_ports.comports())
        for i in range(len(com)):
            comAction=QtGui.QAction('&'+com[i][0],self)
            comAction.setStatusTip("Click to connect to "+com[i][0]+" Port")
            comAction.triggered.connect(self.establish_conn)
            comMenu.addAction(comAction)
        self.statusBar()
    def establish_conn(self,name):
        print(name)
    def zoom_in(self):
        self.ylow=self.ylow+100
        self.yhigh=self.yhigh-100
        self.p1.setYRange(self.ylow,self.yhigh)
    def zoom_out(self):
        self.ylow=self.ylow-100
        self.yhigh=self.yhigh+100
        self.p1.setYRange(self.ylow,self.yhigh)
    def home(self):
        self.splitter1=QtGui.QSplitter(Qt.Vertical,self)
        self.splitter2=QtGui.QSplitter(Qt.Vertical,self)
        self.wid=QtGui.QWidget()
        self.setCentralWidget(self.wid)
        self.hbox=QtGui.QHBoxLayout()
        self.vbox=QtGui.QVBoxLayout()
        self.wid.setLayout(self.hbox)
        self.hbox.addLayout(self.vbox)
        self.resize(1000,800)
        self.data1=deque(maxlen=1000)
        self.data=[]
        self.t=QTime()
        self.t.start()
        self.timer1=QtCore.QTimer()
        self.timer1.timeout.connect(self.update)
        self.timer2=QtCore.QTimer()
        self.timer2.timeout.connect(self.read_data)
        self.timer3=QtCore.QTimer()
        self.timer3.timeout.connect(self.stats)
        for i in range(2000):
            self.data1.append({'x':self.t.elapsed(),'y': 0})
        #----------------Left pane--------------------------
        #----------------Adding Plot------------------------
        self.p1=pg.PlotWidget(name="Raw",title="Respiration Plot",labels={'left':("Thoracic Circumference in (cm)"),'bottom':("Time Elapsed (mm:ss)")},enableMenu=True,axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.p1.addLegend(offset=(450,30))
        self.p1.showGrid(x=True,y=True,alpha=0.5)
        self.p1.setMouseEnabled(x=True,y=True)
        self.curve=self.p1.plot(pen='y',name="Raw Respiration Data")
        self.curve1=self.p1.plot(pen='r',name="Filtered Respiration DAta")
        self.ylow=600
        self.yhigh=800
        self.p1.setYRange(self.ylow,self.yhigh)
        #----------------------------------------------------
        self.statistics=QtGui.QGroupBox()
        self.statistics.setTitle("Statistics")
        self.stlabel1=QtGui.QLabel("Mean Value\t\t\t:",self.statistics)
        self.stlabel1.move(5,40)
        self.stlabel2=QtGui.QLabel("Variance\t\t\t\t:",self.statistics)
        self.stlabel2.move(280,40)
        self.stlabel3=QtGui.QLabel("Respiration Rate (per min)\t\t:",self.statistics)
        self.stlabel3.move(5,70)
        self.stlabel4=QtGui.QLabel("Average Breath Duration (mins)\t:",self.statistics)
        self.stlabel4.move(280,70)
        self.stlabel5=QtGui.QLabel("Variance in Breath Duration (mins)\t:",self.statistics)
        self.stlabel5.move(5,100)
        self.stlabel6=QtGui.QLabel("Statistical Dispersion\t\t:",self.statistics)
        self.stlabel6.move(280,100)
        self.stlabel7=QtGui.QLabel("Average Normalized Tidal Volume\t:",self.statistics)
        self.stlabel7.move(5,130)
        self.stlabel8=QtGui.QLabel("Variance in Normalized Tidal Volume\t:",self.statistics)
        self.stlabel8.move(280,130)
        self.stlabel9=QtGui.QLabel("Average Respiration Width\t\t:",self.statistics)
        self.stlabel9.move(5,160)
        self.stlabel10=QtGui.QLabel("Variance in Respiration Width\t\t:",self.statistics)
        self.stlabel10.move(280,160)
        self.stlabelmean=QtGui.QLabel("0",self.statistics)
        self.stlabelmean.move(205,40)
        self.stlabelmean.resize(200,20)
        self.stlabelvariance=QtGui.QLabel("0",self.statistics)
        self.stlabelvariance.move(485,40)
        self.stlabelvariance.resize(200,20)
        self.stlabelrrate=QtGui.QLabel("0",self.statistics)
        self.stlabelrrate.move(205,70)
        self.stlabelrrate.resize(200,20)
        self.stlabelabd=QtGui.QLabel("0",self.statistics)
        self.stlabelabd.move(485,70)
        self.stlabelabd.resize(200,20)
        self.stlabelvbd=QtGui.QLabel("0",self.statistics)
        self.stlabelvbd.move(205,100)
        self.stlabelvbd.resize(200,20)
        self.stlabelsd=QtGui.QLabel("0",self.statistics)
        self.stlabelsd.move(485,100)
        self.stlabelsd.resize(200,20)
        self.stlabelatv=QtGui.QLabel("0",self.statistics)
        self.stlabelatv.move(205,130)
        self.stlabelatv.resize(200,20)
        self.stlabelvtv=QtGui.QLabel("0",self.statistics)
        self.stlabelvtv.move(485,130)
        self.stlabelvtv.resize(200,20)
        self.stlabelarw=QtGui.QLabel("0",self.statistics)
        self.stlabelarw.move(205,160)
        self.stlabelarw.resize(200,20)
        self.stlabelvrw=QtGui.QLabel("0",self.statistics)
        self.stlabelvrw.move(485,160)
        self.stlabelvrw.resize(200,20)
        #----------------------------------------------------
        self.apneagb=QtGui.QGroupBox()
        self.apneagb.setTitle("Apnea")
        self.apnealabel1=QtGui.QLabel("Apnea Event Detected",self.apneagb)
        self.apnealabel1.resize(150,20)
        self.apnealabel1.move(30,30)
        self.apnealabel2=QtGui.QLabel("No",self.apneagb)
        self.apnealabel2.resize(150,20)
        self.apnealabel2.move(80,50)
        self.apnealabel3=QtGui.QLabel("Total Apnea Events",self.apneagb)
        self.apnealabel3.resize(150,20)
        self.apnealabel3.move(30,70)
        self.apnealabel4=QtGui.QLabel("0",self.apneagb)
        self.apnealabel4.resize(150,20)
        self.apnealabel4.move(80,90)
        #----------------Plot GroupBox---------------------------
        self.groupBox=QtGui.QGroupBox()
        self.groupBox.setTitle("Plot")
        self.label3=QtGui.QLabel("Y-Low  :",self.groupBox)
        self.label3.move(5,20)
        self.label4=QtGui.QLabel("Y-High :",self.groupBox)
        self.label4.move(150,20)
        self.slider3=QtGui.QSlider(self.groupBox)
        self.slider3.setOrientation(QtCore.Qt.Horizontal)
        self.slider3.move(50,20)
        self.slider3.valueChanged[int].connect(self.setylow)
        self.slider4=QtGui.QSlider(self.groupBox)
        self.slider4.setOrientation(QtCore.Qt.Horizontal)
        self.slider4.move(195,20)
        self.slider4.valueChanged[int].connect(self.setyhigh)
        self.pb1=QtGui.QPushButton("Resume",self.groupBox)
        self.pb1.move(60,50)
        self.pb1.clicked.connect(self.plot_resume)
        self.pb2=QtGui.QPushButton("Pause",self.groupBox)
        self.pb2.move(150,50)
        self.pb2.clicked.connect(self.plot_pause)
        #--------------------------------------------------------------
        #---------------Signal-Processing-GroupBox---------------------
        self.sp=QtGui.QGroupBox()
        self.sptab=QtGui.QTabWidget(self.sp)
        self.sptab.setGeometry(QtCore.QRect(10,20,270,120))
        self.tab1=QtGui.QWidget()
        self.sp.setTitle("Signal Processing")
        self.splabel2=QtGui.QLabel("Normalized Cutoff Frequency\t:\tHz",self.tab1)
        self.splabel2.move(5,10)
        self.l1=QtGui.QLineEdit(self.tab1)
        self.l1.setGeometry(QtCore.QRect(160,10,31,20))
        self.splabel3=QtGui.QLabel("Order of Filter\t\t:\tHz",self.tab1)
        self.splabel3.move(5,35)
        self.l2=QtGui.QLineEdit(self.tab1)
        self.l2.setGeometry(QtCore.QRect(160,35,31,20))
        self.sb1=QtGui.QPushButton("Apply",self.tab1)
        self.sb1.move(40,60)
        self.sb1.clicked.connect(self.low_pass)
        self.sptab.addTab(self.tab1,"Low Pass Filter")
        self.tab2=QtGui.QWidget()
        self.splabel7=QtGui.QLabel("Window Size:	    samples",self.tab2)
        self.splabel7.move(5,10)
        self.l5=QtGui.QLineEdit(self.tab2)
        self.l5.setGeometry(QtCore.QRect(75,10,31,20))
        self.sb2=QtGui.QPushButton("Apply",self.tab2)
        self.sb2.move(30,40)
        self.sb2.clicked.connect(self.moving_average)
        self.sb3=QtGui.QPushButton("Remove",self.tab1)
        self.sb3.move(120,60)
        self.sb3.clicked.connect(self.remove_lowpass)
        self.sb4=QtGui.QPushButton("Remove",self.tab2)
        self.sb4.move(130,40)
        self.sptab.addTab(self.tab2,"Moving Average")
        #--------------------------------------------------------------
        #--------------Pneumonia Detection-----------------------------
        self.pneumonia=QtGui.QGroupBox()
        self.pneumonia.setTitle("Pneumonia Detection")
        self.plabel1=QtGui.QLabel("Enter the Age :	        yrs",self.pneumonia)
        self.plabel1.move(70,25)
        self.pl1=QtGui.QLineEdit(self.pneumonia)
        self.pl1.setGeometry(QtCore.QRect(150,25,35,20))
        self.pb1=QtGui.QPushButton("Detect",self.pneumonia)
        self.pb1.move(115,50)
        self.pb1.clicked.connect(self.detect_pneumonia)
        self.plabel2=QtGui.QLabel("Symptoms of Pneumonia :",self.pneumonia)
        self.plabel2.move(70,85)
        self.plabelpneumonia=QtGui.QLabel("No",self.pneumonia)
        self.plabelpneumonia.move(200,85)
        #--------------------------------------------------------------
        #--------------Database Connection-----------------------------
        self.databaseg=QtGui.QGroupBox()
        self.databaseg.setTitle("Dashboard")
        self.dlabel1=QtGui.QLabel("Name\t\t:",self.databaseg)
        self.dlabel1.move(5,15)
        self.dText1=QtGui.QLineEdit(self.databaseg)
        self.dText1.move(120,15)
        self.dlabel2=QtGui.QLabel("Date of Birth\t:",self.databaseg)
        self.dlabel2.move(5,45)
        self.dateEdit=QtGui.QDateEdit(self.databaseg)
        self.dateEdit.setGeometry(QtCore.QRect(120,40,133,22))
        self.dlabel3=QtGui.QLabel("Start Saving to\t:",self.databaseg)
        self.dlabel3.move(5,152)
        self.dlabel4=QtGui.QLabel("Respiration plot\t:",self.databaseg)
        self.dlabel4.move(5,80)
        self.dpb1=QtGui.QCheckBox("Local",self.databaseg)
        self.dpb1.move(120,152)
        self.dpb2=QtGui.QCheckBox("Cloud",self.databaseg)
        self.dpb2.move(200,152)
        self.dpb6=QtGui.QPushButton("Start",self.databaseg)
        self.dpb6.move(120,180)
        self.dpb6.clicked.connect(self.database_startsaving)
        self.dpb3=QtGui.QPushButton("Stop",self.databaseg)
        self.dpb3.move(200,180)
        self.dpb3.clicked.connect(self.database_stopsaving)
        self.dpb4=QtGui.QPushButton("Start",self.databaseg)
        self.dpb4.move(120,75)
        self.dpb4.clicked.connect(self.database_startplot)
        self.dpb5=QtGui.QPushButton("Stop",self.databaseg)
        self.dpb5.move(200,75)
        self.dpb5.clicked.connect(self.database_stopplot)
        self.dlabel5=QtGui.QLabel("Tools\t\t:",self.databaseg)
        self.dlabel5.move(5,115)
        self.dpb7=QtGui.QPushButton("Calibrate",self.databaseg)
        self.dpb7.move(120,112)
        self.dpb7.clicked.connect(self.database_calibrate)
        self.dpb8=QtGui.QPushButton("Analyze",self.databaseg)
        self.dpb8.move(200,112)
        self.dpb8.clicked.connect(self.database_analyze)
        #------------------------------------------------------
        #---------------------Arranging Splitters---------------
        self.vbox2=QtGui.QVBoxLayout()
        self.splitter3=QtGui.QSplitter(self)
        self.splitter4=QtGui.QSplitter(self)
        self.splitter1.addWidget(self.p1)
        self.splitter4.addWidget(self.statistics)
        self.splitter4.addWidget(self.apneagb)
        self.splitter1.addWidget(self.splitter4)
        self.vbox.addWidget(self.splitter3)
        self.splitter2.addWidget(self.groupBox)
        self.splitter2.addWidget(self.databaseg)
        self.splitter2.addWidget(self.sp)
        self.splitter2.addWidget(self.pneumonia)
        self.splitter3.addWidget(self.splitter1)
        self.splitter3.addWidget(self.splitter2)
        self.splitter2.setSizes([80,200,200,160])
        self.splitter3.setSizes([1000,420])
        self.splitter1.setSizes([500,260])
        self.splitter4.setSizes([100,10])
        self.lowpass_flag=0
        #-------------------------------------------------------
        self.show()

    def setylow(self,value):
        self.ylow=value*1024/100
        self.p1.setYRange(self.ylow,self.yhigh)
    def setyhigh(self,value):
        self.yhigh=value*1024/100
        self.p1.setYRange(self.ylow,self.yhigh)
    def update(self):
            x=[item['x'] for item in self.data1]
            y=[item['y'] for item in self.data1]
            if(self.lowpass_flag==1):
                y1=self.butter_lowpass_filter(y,self.cutoff,10,self.order)
                self.curve1.setData(x=x,y=y1)
            self.curve.setData(x=x,y=y)
            
    def plot_resume(self):
        self.timer1.start(100)
    def plot_pause(self):
        self.timer1.stop()
    def low_pass(self):
        self.lowpass_flag=1
        self.cutoff=float(self.l1.text())
        self.order=float(self.l2.text())
    def remove_lowpass(self):
        self.lowpass_flag=0
        self.curve1.clear()
    def moving_average(self):
        print("Clicked Moving Average")
    def detect_pneumonia(self):
        print("Detect Pneumonia Clicked")
    def database_local(self):
        print("Database Local")
    def database_cloud(self):
        print("Database Cloud")
    def database_startplot(self):
        self.t.restart()
        self.timer1.start(50)
        self.timer2.start(4)
        self.timer3.start(30000)
    def database_stopplot(self):
        self.timer1.stop()
        self.timer2.stop()
        self.timer3.stop()
    def database_startsaving(self):
        print("Database start saving")
    def database_stopsaving(self):
        print("Database stop saving")
    def database_calibrate(self):
        print("Database calibrate")
    def database_analyze(self):
        print("Database Analyze")
    def read_data(self):
        #data=np.random.randint(600,700)
        data=int(self.ser.readline()[0:4])
        self.data.append(data)
        self.data1.append({'x':self.t.elapsed(),'y':data})
    def stats(self):
        resp_rate=[]
        total_tidal_volume=[]
        self.data2=self.butter_lowpass_filter(self.data,0.7,len(self.data)/30,6)
        self.data2=np.array(self.data2)
        self.mean=np.mean(self.data2)
        self.stlabelmean.setText(str(round(self.mean,2)))
        self.variance=np.var(self.data2)
        self.stlabelvariance.setText(str(round(self.variance,2)))
        new_data=self.data2-self.mean
        zero_crossings=np.where(np.diff(np.sign(new_data)))[0]
        self.respirationrate=(zero_crossings.size)
        self.stlabelrrate.setText(str(round(self.respirationrate,2)))
        local_maxima=argrelextrema(self.data2,np.greater)[0]
        local_minima=argrelextrema(self.data2,np.less)[0]
        tenp=np.percentile(self.data2,10)
        nintyp=np.percentile(self.data2,90)
        diff_local_maxima=np.diff(local_maxima)
        self.average_breath_duration=np.mean(diff_local_maxima)
        self.stlabelabd.setText(str(round(self.average_breath_duration*0.5/len(self.data2),2)))
        self.var_breath_duration=np.var(diff_local_maxima)
        self.stlabelvbd.setText(str(round(self.var_breath_duration*0.5/len(self.data2),2)))
        self.dispersion=nintyp-tenp
        self.stlabelsd.setText(str(round(self.dispersion,2)))
        tidal_volume=[]
        for i in range(local_minima.size-1):
            maxima=np.where(np.logical_and(local_maxima>=local_minima[i],local_maxima<=local_minima[i+1]))[0]
            if(maxima.size>0):
                volume=self.data2[local_maxima[maxima[0]]]-((self.data2[local_minima[i]]+self.data2[local_minima[i+1]])/2)
                tidal_volume.append(volume)
        self.average_tidal_volume=np.mean(tidal_volume)
        self.variant_tidal_volume=np.var(tidal_volume)
        self.stlabelatv.setText(str(round(self.average_tidal_volume,2)))
        self.stlabelvtv.setText(str(round(self.variant_tidal_volume,2)))
        intdata1=[self.data2[x] for x in local_maxima]
        intdata2=[self.data2[x] for x in local_minima]
        f1=interp1d(local_maxima,intdata1,kind='cubic')
        f2=interp1d(local_minima,intdata2,kind='cubic')
        xmin=max(local_maxima[0],local_minima[0])
        xmax=min(local_maxima[len(local_maxima)-1],local_minima[len(local_minima)-1])
        xnew=np.linspace(xmin,xmax)
        width=f1(xnew)-f2(xnew)
        self.average_width=np.mean(width)
        self.var_width=np.var(width)
        self.stlabelarw.setText(str(round(self.average_width,2)))
        self.stlabelvrw.setText(str(round(self.var_width,2)))
        print(self.mean)
        self.data.clear()
    def butter_lowpass(self,cutoff,fs,order=5):
        nyq=0.5*fs
        normal_cutoff=cutoff/nyq
        b,a=butter(order,normal_cutoff,btype='low',analog=False)
        return b,a
    def butter_lowpass_filter(self,data,cutoff,fs,order=5):
        b,a=self.butter_lowpass(cutoff,fs,order=order)
        y=lfilter(b,a,data)
        return y
    def close_application(self):
         sys.exit()

if __name__=="__main__":
    app=QtGui.QApplication(sys.argv)
    GUI=Window()
    sys.exit(app.exec_())
