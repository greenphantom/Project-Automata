import os
import re
import shutil
import sqlite3
import sys
from sqlite3 import Error
from subprocess import PIPE, Popen


def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return None


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
    with conn:
        function_map = select_code_for_command(conn)
        for key,value in function_map.items():
            file = open(os.getcwd()+"\\bin\\"+key+".py","w+")
            file.write(value)
            file.close()
    return function_map


if __name__ == '__main__':
    fm = main()
    for k,v in fm.items():
        name = os.getcwd()+"\\bin\\"+k+".py"
        process = Popen(['python',name],stdout=PIPE,stderr=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            print('Error from file',name+':\n\n',scrub_text(stderr,back_clip=-1))
        if stdout:
            print('Output from file',name+':\n'+scrub_text(stdout))
    prompt = input('Delete generates content? (Y|N):')
    if str(prompt).lower() == 'y':
        dump_bin()
        print("Bin's contents deleted!")
    else:
        print('Content saved')
    
    
