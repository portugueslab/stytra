# from time import sleep

# from lightparam import Param
# import stytra

# from stytra.stimulation import Protocol, Pause
# from stytra.experiments import VisualExperiment
# from stytra.stimulation.stimuli import FullFieldVisualStimulus
# from stytra.triggering import Trigger
# from PyQt5.QtWidgets import QApplication
# from PyQt5.QtCore import Qt
# import stytra
# from pathlib import Path
# from pkgutil import iter_modules
# from importlib import import_module


# PROTOCOL_DURATION = 4  # Duration of each simulated experiment
# N_REFRESH_EVTS = 50

# # iterate through the modules in the current package
# package_dir = Path(stytra.__file__).parent / "examples"
# print(package_dir)

# protocols = []
# for (_, module_name, _) in iter_modules([package_dir]):
#     # Heuristic to exclude examples more complicated to run:
#     if all([excl not in module_name
#                 for excl in ["custom", "trigger", "serial", "camera"]]):
#         # import the module and iterate through its attributes
#         # try:
#         module = import_module(f"stytra.examples.{module_name}")
#         for attribute_name in dir(module):
#             if "Protocol" in attribute_name and attribute_name != "Protocol":
#                 protocols.append(getattr(module, attribute_name))
#             # attribute = getattr(module, attribute_name)
#         # except ModuleNotFoundError:
#         #    print(f"Can't import {module}")
# print(protocols)


# class AProtocol(Protocol):
#     name = "test_protocol"

#     def __init__(self):
#         super().__init__()
#         self.duration = Param(PROTOCOL_DURATION / 2)

#     def get_stim_sequence(self):
#         stimuli = [Pause(duration=self.duration),
#                    FullFieldVisualStimulus(duration=self.duration)]
#         return stimuli


# class DummyTrigger(Trigger):
#     def __init__(self):
#         super().__init__()
#         self.k = False

#     def check_trigger(self):
#         if self.k:
#             sleep(PROTOCOL_DURATION / 5)
#             self.k = False
#             return True
#         else:
#             self.k = True
#             return False


# # def test_base_exp(experiment_factory, temp_dir, qtbot):
# #     exp, exp_wnd = experiment_factory(VisualExperiment,
# #                              protocol=TestProtocol0(),
# #                              dir_save=temp_dir
# #                              )
# #     qtbot.addWidget(exp_wnd)
# #     qtbot.mouseClick(exp_wnd.toolbar_control.toggleStatus,
# #                      Qt.LeftButton,
# #                      delay=1)
# #     qtbot.wait((PROTOCOL_DURATION + 1)*1000)
# #     #qtbot.mousePress(exp_wnd)
# #     #for _ in range(N_REFRESH_EVTS):
# #      #   exp.protocol_runner.timestep()
# #      #   sleep(PROTOCOL_DURATION / N_REFRESH_EVTS)
# #     #if tracking is not None:
# #     #    exp.acc_tracking.update_list()
# #     exp.end_protocol(save=True)



# # def test_base_exp(qtbot):
# #     stytra = Stytra(protocol=TestProtocol0(),
# #                     exec=False)
# #     #qtbot.addWidget(exp_wnd)
# #     exp = stytra.exp
# #     exp_wnd = exp.window_main
# #     qtbot.mouseClick(exp_wnd.toolbar_control.toggleStatus,
# #                      Qt.LeftButton,
# #                      delay=1)
# #     qtbot.wait((PROTOCOL_DURATION + 1)*1000)
# #     exp.end_protocol(save=True)

# from PyQt5.QtWidgets import QWidget

# # def test_wind(widg_factory):
# #     a = widg_factory()
# #     a.show()
