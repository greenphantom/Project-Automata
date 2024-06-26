import datetime
import os
import re
import shutil
import sqlite3
import sys
import threading
import time
from sqlite3 import Error
from subprocess import PIPE, Popen

from PyQt5 import QtGui
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.uic import *

import schedule


def get_date(dt_obj=datetime.datetime.now()):
    return str(dt_obj.ctime())

def get_date_from_str(date):
    try: 
        x = datetime.datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
        return x
    except ValueError:
        x = datetime.datetime.strptime(date, '%Y-%m-%d')
        return x

def schedule_onetime_job(d_time, job_func, msg=False, *args, **kwargs):
    d_sec = (d_time-(datetime.datetime.now())).total_seconds()
    if d_sec < 0: d_sec = 0
    time.sleep(d_sec)
    job_func(*args,**kwargs)
    if msg: print('Finished execution...')

def run_onetime_then_delete(d_time, command, msg=False, *args, **kwargs):
    d_sec = (d_time-(datetime.datetime.now())).total_seconds()
    if d_sec < 0: d_sec = 0
    time.sleep(d_sec)
    command.run()
    if msg: print('Finished execution...')

    conn = create_connection()
    with conn:
        delete_schedule_by_id(conn,command.id)

class MainMenu(QDialog):
    def __init__(self):
        super(MainMenu,self).__init__()
        loadUi('main_layout.ui',self)
        self.setWindowTitle('Automata Script Manager')
        self.setWindowIcon(QtGui.QIcon('Automata.jpg'))
        self.inputDialog = InputForm(self)
        self.viewDialog = ViewMenu(self)
    
    @pyqtSlot()
    def on_create_button_clicked(self):
        self.inputDialog.show()
        self.close()

    @pyqtSlot()
    def on_view_button_clicked(self):
        self.viewDialog.refresh()
        self.viewDialog.show()
        self.close()

    @pyqtSlot()
    def on_close_button_clicked(self):
        sys.exit()
        self.close()

class InputForm(QDialog):
    def __init__(self,parent=None):
        super(InputForm,self).__init__()
        loadUi('input_layout.ui',self)
        self.setWindowTitle('Create New Script')
        self.setWindowIcon(QtGui.QIcon('Automata.jpg'))
        self.create_field.setText(get_date())
        self.dialog=parent
    
    @pyqtSlot()
    def on_create_button_clicked(self):
        command = Command(self.name.text(),"-1",self.param.text(),self.desc.toPlainText(),self.create_field.text(),self.call_field.text(),self.alias_field.text(),self.script.toPlainText(),str(self.comboBox.currentText()))
        conn = create_connection(os.getcwd() + "\\automata.db")
        with conn:
            create_command(conn,command)
        QMessageBox.information(self, "Script Created!", self.name.text()+" was successfully created." )
        self.dialog.show()
        self.close()
    
    @pyqtSlot()
    def on_back_button_clicked(self):
        self.dialog.show()
        self.close()

class ViewMenu(QDialog):
    def __init__(self,parent=None):
        super(ViewMenu,self).__init__()
        loadUi('view_layout.ui',self)
        self.dialog=parent
        self.setWindowTitle('View Scripts')
        self.setWindowIcon(QtGui.QIcon('Automata.jpg'))
        self.commands = select_all_commands(create_connection())
        for i,c in enumerate(self.commands):
            self.listWidget.addItem(str(i+1)+".   "+c.name)
            
        self.listWidget.setWindowTitle('Scripts')
        self.listWidget.itemClicked.connect(self.click_item)

    def click_item(self,item):
        com = list(filter((lambda c: c.name in (str(item.text()))),self.commands))
        self.updateForm = UpdateForm(com[0],self)
        self.updateForm.show()
        self.close()

    def refresh(self):
        self.listWidget.clear()
        self.commands = select_all_commands(create_connection())
        for i,c in enumerate(self.commands):
            self.listWidget.addItem(str(i+1)+".   "+c.name)
            
        self.listWidget.setWindowTitle('Scripts')
        self.listWidget.itemClicked.connect(self.click_item)
       
    @pyqtSlot()
    def on_back_button_clicked(self):
        self.dialog.show()
        self.close()

    @pyqtSlot()
    def on_query_button_clicked(self):
        query_jobs()

class UpdateForm(QDialog):
    def __init__(self,command,parent=None):
        super(UpdateForm,self).__init__()
        loadUi('update_layout.ui',self)
        self.setWindowTitle('Manage Script - '+command.name)
        self.setWindowIcon(QtGui.QIcon('Automata.jpg'))
        self.name.setText(command.name)
        self.param.setText(command.params)
        self.desc.setText(command.description)
        self.create_field.setText(command.create_date)
        self.call_field.setText(command.last_call)
        self.script.setText(command.function)
        self.alias_field.setText(command.alias)
        self.id = command.id
        self.dialog=parent

        conn = create_connection()
        with conn:
            self.sched = select_schedule_by_id(conn,command.id)
        dt = get_date_from_str(self.sched[0][1])
        qD = QDate(dt.year,dt.month,dt.day)
        qT = QTime(dt.hour,dt.minute,dt.second)

        self.datetime_field.setDateTime(QDateTime(qD,qT))
        self.calltype_field.setCurrentIndex(int(self.sched[0][2])+1)
        self.command=command

    def refresh(self):
        self.update()

    def update(self):
        command = Command(self.name.text(),self.id,self.param.text(),self.desc.toPlainText(),self.create_field.text(),self.call_field.text(),self.alias_field.text(),self.script.toPlainText(),str(self.comboBox.currentText()))
        date = self.datetime_field.date()
        time = self.datetime_field.time()
        dt = datetime.datetime(date.year(),date.month(),date.day(),time.hour(),time.minute(),time.second())
        self.sched = (self.id,get_date(dt),int(self.calltype_field.currentIndex())-1)
        conn = create_connection(os.getcwd() + "\\automata.db")
        with conn:
            update_command(conn,command)
            update_schedule(conn,self.sched)
        self.command = command
        restart()
    
    @pyqtSlot()
    def on_update_button_clicked(self):
        self.update()
        QMessageBox.information(self, "Update to script", self.name.text()+" is now updated!" )
        self.refresh()

    @pyqtSlot()
    def on_run_button_clicked(self):
        # Updates the script when the user trys to run it
        self.update()
        self.call_field.setText(get_date())
        run_script(self.command.name,create_connection())
        QMessageBox.information(self, "Run script", self.name.text()+" ran in the terminal." )
        self.command = select_command_by_name(create_connection(),self.command.name)[0]
        self.refresh()

    @pyqtSlot()
    def on_delete_button_clicked(self):
        reply = QMessageBox.question(self, 'Delete Confirmation', "Are you sure you'd like to remove this script?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = create_connection(os.getcwd() + "\\automata.db")
            with conn:
                delete_command_by_id(conn,self.id)

            self.dialog.refresh()
            self.close()
            self.dialog.show()
            
    @pyqtSlot()
    def on_back_button_clicked(self):
        self.dialog.refresh()
        self.dialog.show()
        self.close()

class Command():
    def __init__(self, name='lambda', id='-1', params="", description='', create_date=get_date(), last_call=get_date(), alias='', function="print('This shouldn't print...')", language='Python3'):
        self.name = name
        self.id=int(id)
        if isinstance(params,list):
            temp = ''
            for p in params:
                temp += p+','
            temp= temp[:-1]
            print(temp)
            self.params = temp
        else:
            self.params = params # Params will read in a list of strings
        self.description = description
        self.create_date = create_date
        self.last_call = last_call
        self.alias = alias
        self.function = function
        self.language = language
        # Add more fields with schema change
    
    def __str__(self):
        return "\nCommand: "+self.name+"\nID: "+str(self.id)+"\nParameters: "+str(self.params)+"\nDescription: "+self.description+"\nDate Created: "+str(self.create_date)+"\nLast Call: "+str(self.last_call)+"\nAlias: "+self.alias+"\nFunction: \n"+self.function+"\nLangauge: "+self.language+'\n'
    
    def __repr__(self):
        return "\nCommand: "+self.name+"\nID: "+str(self.id)+"\nParameters: "+str(self.params)+"\nDescription: "+self.description+"\nDate Created: "+str(self.create_date)+"\nLast Call: "+str(self.last_call)+"\nAlias: "+self.alias+"\nFunction: \n"+self.function+"\nLangauge: "+self.language+'\n'
    
    def to_tuple(self,last=True,alias=True):
        if last and alias:
            return (self.name,str(self.params),self.description,self.create_date,self.last_call,self.alias,self.function,self.language)
        elif last:
            return (self.name,str(self.params),self.description,self.create_date,self.last_call,self.function,self.language)
        else:
            return (self.name,str(self.params),self.description,self.create_date,self.alias,self.function,self.language)

    def run(self):
        run_script(self.name,create_connection())
        print("Command '"+self.name+"' ran successfully at",datetime.datetime.now())

def create_connection(db_file= os.getcwd() + "\\automata.db"):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return None

def get_next_id(conn=create_connection(os.getcwd() + "\\automata.db")):
    sql = 'SELECT ID FROM COMMAND GROUP BY ID HAVING MAX(ID) ORDER BY ID DESC ;'
    cur = conn.cursor()
    cur.execute(sql)

    rows = cur.fetchall()
    return int(rows[0][0])+1

def create_command(conn, command):
    if isinstance(command,Command):
        command = command.to_tuple(last=False)

    sql = ''' INSERT INTO command(name,parameters,description,created,alias,function,language)
              VALUES(?,?,?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, command)
    return cur.lastrowid

def create_schedule(conn, id, dt_obj, call_type):
    sql = ''' INSERT INTO SCHEDULE(Com_id,Datetime,'Call Type')
              VALUES(?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, (id,get_date(dt_obj),call_type))
    return cur.lastrowid

def update_command(conn, command):
    if isinstance(command,Command):
        command = (*command.to_tuple(),command.id)

    sql = "UPDATE COMMAND SET name = ?, parameters = ?, description = ?, created = ?, 'last call' = ?, alias = ?, function = ?, language = ? WHERE id = ?"
    cur = conn.cursor()
    cur.execute(sql, command)

def update_schedule(conn, sched):
    sched = sched + (sched[0],)
    sql = "UPDATE SCHEDULE SET Com_id = ?, Datetime = ?, 'Call Type' = ? WHERE Com_id = ?"
    cur = conn.cursor()
    cur.execute(sql, sched)

def update_call_by_name(conn, name):
    sql = "UPDATE COMMAND SET 'last call' = '"+get_date()+"' WHERE name = '"+name+"' OR alias = '"+name+"';"
    cur = conn.cursor()
    cur.execute(sql)

def delete_command_by_name(conn, name):
    sql = 'DELETE FROM COMMAND WHERE name=?;'
    cur = conn.cursor()
    cur.execute(sql,(name,))

def delete_command_by_id(conn, id):
    sql = 'DELETE FROM COMMAND WHERE id=?;'
    cur = conn.cursor()
    cur.execute(sql,(id,))

def delete_schedule_by_id(conn, id):
    sql = 'DELETE FROM SCHEDULE WHERE Com_id=?;'
    cur = conn.cursor()
    cur.execute(sql,(id,))

def select_all_commands(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM Command")

    results = []
    rows = cur.fetchall()

    for i,row in enumerate(rows):
        com = Command(rows[i][0],rows[i][1],rows[i][2],rows[i][3],rows[i][4],rows[i][5],rows[i][6],rows[i][7],rows[i][8])
        results.append(com)

    return results

def select_command_by_name(conn,name,pnt=False):
    cur = conn.cursor()
    cur.execute("SELECT * FROM command where Name = '"+name+"' OR Alias = '"+name+"';")

    results = []
    rows = cur.fetchall()
    for i,row in enumerate(rows):
        com = Command(rows[i][0],rows[i][1],rows[i][2],rows[i][3],rows[i][4],rows[i][5],rows[i][6],rows[i][7],rows[i][8])
        results.append(com)
        if pnt:
            print(com)

    return results

def select_schedule_by_id(conn,id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM SCHEDULE where Com_id = '"+str(id)+"';")

    results = []
    rows = cur.fetchall()
    for i,row in enumerate(rows):
        s = (rows[i][0],rows[i][1],rows[i][2],)
        results.append(s)

    return results

def select_code_for_command(conn):
    cur = conn.cursor()
    cur.execute("SELECT name,function FROM command")

    rows = cur.fetchall()
    function_map = {}
    for i,row in enumerate(rows):
        function_name = rows[i][0] # Maps name of the command with its function
        function = rows[i][1]
        function_map[function_name] = function
    return function_map

def scrub_text(row,front_clip = 2,back_clip=-3):
    p = str(row)[front_clip:back_clip] # removes the "('" part from the beginning and the ")'" from the end
    s = p.replace('\\n','\n')
    s = s.replace('\\t','\t')
    s = s.replace('\\r','\r')
    return s

def dump_bin():
    folder = os.getcwd()+"\\bin"
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)

def update_script(cmd,conn=create_connection(os.getcwd() + "\\automata.db")):
    with conn:
        tup = (cmd.name, str(cmd.params),cmd.description, cmd.create_date, cmd.last_call, cmd.alias,cmd.function,cmd.language,cmd.id)
        print(tup)
        input()
        update_command(conn,tup)

def run_script(script_name,conn=create_connection(os.getcwd() + "\\automata.db")):
    with conn:
        query = select_command_by_name(conn,script_name)
        for q in query:
            q.last_call = str(datetime.datetime.now().date())
            if (q.language == 'Python3'): # Dependency on different langauges
                file = open(os.getcwd()+"\\bin\\"+q.name+".py","w+")
                file.write(q.function)
                file.close()
        execute_bin_contents(conn)

def execute_bin_contents(conn,rm=True):
    print()
    print('=='*30)
    print('Executing content within bin: ')
    for item in os.listdir(os.getcwd()+"\\bin\\"):
        full_item = os.getcwd()+"\\bin\\"+item
        if (item.endswith('.py')):
            process = Popen(['python',full_item],stdout=PIPE,stderr=PIPE)
            stdout, stderr = process.communicate()
            if stderr:
                print('Error from file',full_item+':\n\n',scrub_text(stderr,back_clip=-1)+'\n')
            elif stdout:
                print('Output from file',full_item+':\n'+scrub_text(stdout)+'\n')

            update_call_by_name(conn,item.replace('.py',''))

    if (rm):
        print('Deleting bin contents...')
        dump_bin()
    print('=='*30,'\n')

def add_command():
    app = QApplication(sys.argv)
    widget = InputForm()
    widget.show()
    sys.exit(app.exec()) 
    
def view_GUI():
    app = QApplication(sys.argv)
    widget = ViewMenu(MainMenu())
    widget.show()
    sys.exit(app.exec()) 

def change_command(command):
    app = QApplication(sys.argv)
    widget = UpdateForm(command,MainMenu())
    widget.show()
    sys.exit(app.exec()) 

def test_CRUD():
    conn = create_connection()
    with conn:
        command = Command('Test','-1','','Tests adding command to database',get_date(),'','','print("Hello World!")','Python3')
        create_command(conn,command)
        res = select_command_by_name(conn,'Test',True)
        res[0].name = 'funny'
        res[0].alias = 'test'
        update_command(conn,res[0])
        res = select_command_by_name(conn,'Test',True) # Sees if it was updated
        assert(len(res) == 0), "Failed to update correctly..."
        delete_command_by_name(conn,'funny')

def run_execution_test():
    database = os.getcwd() + "\\automata.db"
    conn = create_connection(database)
    com = ('Test','','Tests adding command to database',str(datetime.datetime.now().date()),'','print("Hello World!")','Python3')
    input('Test will now be added to automata.db...')
    create_command(conn,com)
    with conn:
        function_map = select_code_for_command(conn)
        for key,value in function_map.items():
            file = open(os.getcwd()+"\\bin\\"+key+".py","w+")
            file.write(value)
            file.close()
        execute_bin_contents(conn)
        input('Test will now be deleted...')
        delete_command_by_name(conn,'Test')
    return function_map

def run_update_GUI_test():
    res = select_command_by_name(create_connection(os.getcwd() + "\\automata.db"),'sum',True)
    change_command(res[0])


def init_MainMenu():
    app = QApplication(sys.argv)
    widget = MainMenu()
    widget.show()
    sys.exit(app.exec())

def run_schedules():
    while 1:
        schedule.run_pending()
        # print(schedule.jobs)
        time.sleep(1)

def restart():
    schedule.clear()
    start_up(True)

def query_jobs():
    print()
    print('=='*30)
    print('Here are all currently recurring jobs: ')
    for j in schedule.jobs:
        print(j)
    print('=='*30,'\n')

def start_up(restart=False):
    conn = create_connection()
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM COMMAND,SCHEDULE WHERE ID = COM_ID")

        results = []
        rows = cur.fetchall()

        for i,row in enumerate(rows):
            com = Command(rows[i][0],rows[i][1],rows[i][2],rows[i][3],rows[i][4],rows[i][5],rows[i][6],rows[i][7],rows[i][8])
            date = rows[i][10]
            dt_obj = get_date_from_str(date)
            call_type = int(rows[i][11])
            if (datetime.datetime.now() > dt_obj and call_type < 1 and not restart) : # Scehduled in the past
                if call_type == 0:
                    th = threading.Thread(target=schedule_onetime_job,args=(dt_obj,com.run,))
                    th.start()
                elif call_type != -1:
                    print('Warning: Outdated Script detected. Please check scheduling of script',com.name)
            else:
                if call_type == -1: continue # undefined schedule
                elif call_type == 0 and not restart: # Run on start up
                    th = threading.Thread(target=schedule_onetime_job,args=(dt_obj,com.run,))
                    th.start()
                elif call_type == 1: # Run once then never again
                    th = threading.Thread(target=run_onetime_then_delete,args=(dt_obj,com,))
                    th.start()
                elif call_type == 2: # Run Hourly
                    schedule.every().hour.do(com.run)
                elif call_type == 3: # Run Daily
                    schedule.every().day.at(str(dt_obj.time().hour)+':'+str(dt_obj.time().minute)).do(com.run)
                else:
                    #print('Call_type not defined...')
                    continue
        
        schedule_thread = threading.Thread(target=run_schedules)
        schedule_thread.start()


daemon_thread = threading.Thread(target=start_up,name="daemon")
GUI_thread = threading.Thread(target=init_MainMenu,name="GUI")

GUI_thread.daemon = True
daemon_thread.daemon = True

GUI_thread.start()

daemon_thread.start()
daemon_thread.join()

GUI_thread.join()
