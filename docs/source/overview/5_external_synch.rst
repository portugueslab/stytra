.. raw:: html

     <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

.. _imaging-example:

Synchronize stimulation with data acquisition
=============================================

Here, we demonstrate the communication with a custom-built two-photon microscope. We performed two-photon calcium imaging in a seven days post fertilization,  head-restrained fish larva pan-neuronally expressing the calcium indicator GCaMP6f (Tg(*elavl3*:GCaMP6f), :cite:`wolf2017sensorimotor`). For a complete description of the calcium imaging protocol see :cite:`kist2017whole`. These and following experiments were performed in accordance with approved protocols set by the Max Planck Society and the Regierung von Oberbayern.


We designed a simple protocol in Stytra consisting of either open- or closed-loop forward-moving gratings, similar to the optomotor assay described in the closed-loop section, with the gain set to either 0 or 1. At the beginning of the experiment, the microscope sends a ZeroMQ message to Stytra, as described in the previous section. This triggers the beginning of the visual stimulation protocol, as well as the online tracking of the fish tail, with a 10-20 ms delay.

The figure belows shows the trace obtained from the live tracking of the tail during the experiment together with the vigor, the gain, and the grating velocities before and after calculating the closed loop velocity. Light shades represent open-loop trials and dark shades closed loop trials, and the triggering time is maked by an arrow:

.. raw:: html
   :file: ../../figures/imaging_behav.html

To analyse the obtained imaging data, we used the behavioural data saved by Stytra to build regressors for grating speed and tail motion (for a description of regressor-based analysis of calcium signals, see :cite:`portugues2014whole`). Then, we computed pixel-wise correlation coefficients of calcium activity and the two regressors. The figure below reports the results obtained by imaging a large area of the fish brain, covering all regions from the rhombencephalon to the optic tectum. As expected, calcium signals in the region of the optic tectum are highly correlated with motion in the visual field, while events in more caudal regions of the reticular formation are highly correlated with swimming bouts:

.. raw:: html
   :file: ../../figures/imaging_cmaps.html

To look at actual fluorescence traces, we investigated the activity of the pixels around the maximum of the correlation maps, highlighted by the square on the fish anatomies. Below, the plot shows the average activity in these regions together with the regressor traces for the vigor and the grating velocities.

.. raw:: html
   :file: ../../figures/imaging_traces.html

The Stytra script used for this experiment is available in the examples, and the analysis in a separate `github repository <https://github.com/portugueslab/example_stytra_analysis>`_.