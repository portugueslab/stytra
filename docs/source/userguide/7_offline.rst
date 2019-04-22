Offline use of Stytra
=====================

With Stytra installed, start the offline tracking script by running:

    python -m stytra.offline.track_video


Choose a video file and what you want to track.

Run Stytra and adjust the tracking parameters. Please see the corresponding :ref:`documentation section<fishtracking>` for hints.

Click the `Track video` button in the toolbar. The progress bar will show the progress of the tracking. When it is done, the program will exit and you will get a tracking output file. It will have the same name as the input video, just with an extension corresponding to the chosen output format.

If you want to batch process multiple videos with the same parameters, running the Stytra pipeline through a script or notebook might be convenient. For this, please refer to the `notebook repository <https://github.com/portugueslab/example_stytra_analysis>`_.

