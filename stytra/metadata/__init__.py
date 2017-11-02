import param
from paramqt import ParameterGui
from pyqtgraph.parametertree import Parameter, ParameterTree
from stytra.collectors import HasPyQtGraphParams


#

# class MetadataCamera(Metadata):
#     category = 'camera'
#
#     exposure = param.Number(default=1, bounds=[0.1, 50], doc='Exposure (ms)')
#     framerate = param.Number(default=100, bounds=[0.5, 1000], doc='Frame rate (Hz)')
#     gain = param.Number(default=1.0, bounds=[0.1, 3], doc='Camera amplification gain')

#
# class MetadataGeneral(Metadata):
#     """General experiment properties metadata class
#     """
#     category = 'general'
#
#     experiment_name = param.String()
#     experimenter_name = param.ObjectSelector(default='Vilim Stih',
#                                              objects=['Elena Dragomir',
#                                                       'Andreas Kist',
#                                                       'Laura Knogler',
#                                                       'Daniil Markov',
#                                                       'Pablo Oteiza',
#                                                       'Virginia Palieri',
#                                                       'Luigi Petrucco',
#                                                       'Ruben Portugues',
#                                                       'Vilim Stih',
#                                                       'Tugce Yildizoglu'
#                                                       ])
#
#     setup_name = param.ObjectSelector(default='Saskin', objects=['2p',
#                                                'Lightsheet',
#                                                '42',
#                                                'Saskin',
#                                                'Archimedes',
#                                                'Helmut',
#                                                'Katysha'])

