import datetime
import os
import re
import shutil
import sqlite3
import sys
import time
from sqlite3 import Error
from subprocess import PIPE, Popen

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.uic import loadUi

import schedule


def get_date():
    return str(datetime.datetime.now().ctime())

class InputForm(QDialog):
    def __init__(self):
        super(InputForm,self).__init__()
        loadUi('input_layout.ui',self)
        self.setWindowTitle('Input Form')
        self.create_field.setText(get_date())
    
    @pyqtSlot()
    def on_pushButton_clicked(self):
        command = Command(self.name.text(),"-1",self.param.text(),self.desc.toPlainText(),self.create_field.text(),self.call_field.text(),self.alias_field.text(),self.script.toPlainText(),str(self.comboBox.currentText()))
        conn = create_connection(os.getcwd() + "\\automata.db")
        with conn:
            create_command(conn,command)
        self.close()

class UpdateForm(QDialog):
    def __init__(self,command):
        super(UpdateForm,self).__init__()
        loadUi('update_layout.ui',self)
        self.setWindowTitle('Update Form')
        self.name.setText(command.name)
        self.param.setText(command.params)
        self.desc.setText(command.description)
        self.create_field.setText(command.create_date)
        self.call_field.setText(command.last_call)
        self.script.setText(command.function)
        self.alias_field.setText(command.alias)
        self.id = command.id
    
    @pyqtSlot()
    def on_pushButton_clicked(self):
        command = Command(self.name.text(),self.id,self.param.text(),self.desc.toPlainText(),self.create_field.text(),self.call_field.text(),self.alias_field.text(),self.script.toPlainText(),str(self.comboBox.currentText()))
        conn = create_connection(os.getcwd() + "\\automata.db")
        with conn:
            update_command(conn,command)
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

def update_command(conn, command):
    if isinstance(command,Command):
        command = (*command.to_tuple(),command.id)

    sql = "UPDATE COMMAND SET name = ?, parameters = ?, description = ?, created = ?, 'last call' = ?, alias = ?, function = ?, language = ? WHERE id = ?"
    cur = conn.cursor()
    cur.execute(sql, command)

def update_call_by_name(conn, name):
    sql = "UPDATE COMMAND SET 'last call' = '"+get_date()+"' WHERE name = '"+name+"' OR alias = '"+name+"';"
    cur = conn.cursor()
    cur.execute(sql)

def delete_command_by_name(conn, name):
    sql = 'Delete from command where name=?'
    cur = conn.cursor()
    cur.execute(sql,(name,))

def select_all_commands(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM Command")

    rows = cur.fetchall()

    for row in rows:
        print(row)

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
        print('\nDeleting bin contents...')
        dump_bin()

def add_command():
    app = QApplication(sys.argv)
    widget = InputForm()
    widget.show()
    sys.exit(app.exec()) 

def change_command(command):
    app = QApplication(sys.argv)
    widget = UpdateForm(command)
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


# test_CRUD()
# run_execution_test()
# run_update_GUI_test()
# add_command()

