import time

import schedule

def job():
    print('Executing...')

schedule.every(30).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)