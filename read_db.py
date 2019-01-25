import datetime
import os
import re
import shutil
import sqlite3
import sys
from sqlite3 import Error
from subprocess import PIPE, Popen

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.uic import loadUi


class InputForm(QDialog):
    def __init__(self):
        super(InputForm,self).__init__()
        loadUi('input_layout.ui',self)
        self.setWindowTitle('Input Form')
    
    @pyqtSlot()
    def on_pushButton_clicked(self):
        command = (self.name.text(),self.param.text(),self.desc.toPlainText(),str(datetime.datetime.now().date()),'',self.script.toPlainText(),str(self.comboBox.currentText()))
        conn = create_connection(os.getcwd() + "\\automata.db")
        with conn:
            create_command(conn,command)
        self.close()


def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return None

def create_command(conn, command):
    sql = ''' INSERT INTO command(name,parameters,description,created,alias,function,language)
              VALUES(?,?,?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, command)
    return cur.lastrowid

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

def main():
    database = os.getcwd() + "\\automata.db"
    # create a database connection
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
        input('Test will now be deleted...')
        delete_command_by_name(conn,'Test')
    return function_map


if __name__ == '__main__':
    fm = main()
    print()
    for k,v in fm.items():
        name = os.getcwd()+"\\bin\\"+k+".py"
        process = Popen(['python',name],stdout=PIPE,stderr=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            print('Error from file',name+':\n\n',scrub_text(stderr,back_clip=-1))
        if stdout:
            print('Output from file',name+':\n'+scrub_text(stdout))
        print()
    prompt = input('Delete generates content? (Y|N):')
    if str(prompt).lower() == 'y':
        dump_bin()
        print("Bin's contents deleted!")
    else:
        print('Content saved')

    prompt = input('\nWould you like to add a command? (Y|N):')
    if str(prompt).lower() == 'y':
        app = QApplication(sys.argv)
        widget = InputForm()
        widget.show()
        sys.exit(app.exec()) 
    else:
        print('Terminating program...')
       
