from stytra.hardware.motor.stageAPI import Motor
acc = 204552
velo = 107374182


mm =Motor(1)

mm.homethatthing()
mm.open()
mm.setvelocity(acc, velo)
mm.close()
#
# mm2.homethatthing()
# mm2.open()
# mm2.setvelocity(acc, velo)
# mm2.close()