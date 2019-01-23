import os
import re
import sqlite3
import sys
from sqlite3 import Error
from subprocess import PIPE, Popen


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return None


def select_all_commands(conn):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM Command")

    rows = cur.fetchall()

    for row in rows:
        print(row)

def select_code_for_command(conn):
    cur = conn.cursor()
    cur.execute("SELECT function FROM command")

    rows = cur.fetchall()
    return scrub_text(rows)

def scrub_text(rows):
    scrubbed_text = []
    for row in rows:
        p = str(row)[2:-3] # removes the "('" part from the beginning and the ")'" from the end
        s = p.replace('\\n','\n')
        s = s.replace('\\t','\t')
        scrubbed_text.append(s) 
    return scrubbed_text  

def main():
    database = os.getcwd() + "\\automata.db"

    # create a database connection
    conn = create_connection(database)
    with conn:
        # print("1. Query task by priority:")
        # select_command_by_name(conn, )

        test = select_code_for_command(conn)
        file = open(os.getcwd()+"\\bin\\test.py","w+")
        for result in test:
            file.write(result)
        file.close()


if __name__ == '__main__':
    main()
    name = os.getcwd()+"\\bin\\test.py"
    process = Popen(['python',name],stdout=PIPE,stderr=PIPE)
    stdout, stderr = process.communicate()
    if stderr:
        print('Error from file ',name+':\n',stderr)
    if stdout:
        print('Output from file ',name+':\n',stdout)
    #os.execlp(os.getcwd()+"\\bin\\test.py",'test.py')
