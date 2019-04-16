import schedule
import time
import scripts.gdelt as gdelt
import datetime


def job():
    current_dt = datetime.datetime.now()
    print(str(current_dt))
    gdelt.run()


schedule.every().hour.at(":03").do(job)
schedule.every().hour.at(":18").do(job)
schedule.every().hour.at(":33").do(job)
schedule.every().hour.at(":48").do(job)

while 1:
    schedule.run_pending()
    time.sleep(1)
