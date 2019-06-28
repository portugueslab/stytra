from stytra.hardware.motor.stageAPI import Motor
acc = 204552
velo = 107374182


m1 =Motor(1)
m1.homethatthing()
m1.open()
m1.setvelocity(acc, velo)
m1.close()


m2 =Motor(2)
m2.homethatthing()
m2.open()
m2.setvelocity(acc, velo)
m2.close()


