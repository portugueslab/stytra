from stytra.hardware.motor.stageAPI import Motor
import datetime


# Run motorminimal before that here

mo = Motor(1)

mo.open()
mo.movethatthing(2000)
mo.tolerance = 50

# for i in range(10):
#     start = datetime.datetime.now()
#     mo.movethatthing(8000)
#     print((datetime.datetime.now() - start).total_seconds())
#
#     # mo.tolerance = 2000
#     start = datetime.datetime.now()
#     mo.movethatthing(2000)
#     print((datetime.datetime.now() - start).total_seconds())
mo.close()