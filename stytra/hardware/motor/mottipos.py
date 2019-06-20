from stytra.hardware.motor.stageAPI import Motor
import datetime


# Run motorminimal before that here

mo = Motor(1)

mo.open()
#mo.movethatthing(2000)
#mo.tolerance = 50
time1 = []
time2 = []
for i in range(5):
    start1 = datetime.datetime.now()
    mo.movethatthing(int(110000 + 18000))
    time1.append((datetime.datetime.now() - start1).total_seconds())

    # mo.tolerance = 2000
    start2 = datetime.datetime.now()
    mo.movethatthing(110000)
    time2.append((datetime.datetime.now() - start2).total_seconds())

print (time1, time2)
mo.close()