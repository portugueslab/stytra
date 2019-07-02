from stytra.hardware.motor.stageAPI import Motor
acc = int(204552/100)
velo = int (107374182/80)


mm =Motor(1)
mm.homethatthing()
mm.open()
mm.setvelocity(acc, velo)
mm.close()


mu =Motor(2)
mu.homethatthing()
mu.open()
mu.setvelocity(acc, velo)
mu.close()


