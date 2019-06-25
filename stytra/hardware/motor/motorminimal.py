from stytra.hardware.motor.stageAPI import Motor
acc = 204552
velo = 107374182


mm =Motor(1)

mm.homethatthing()
mm.open()
mm.setvelocity(acc, velo)
# mm.movethatthing(0)
mm.close()


mu =Motor(2)
mu.homethatthing()
mu.open()
mu.setvelocity(acc, velo)
# mu.movethatthing(0)
mu.close()


