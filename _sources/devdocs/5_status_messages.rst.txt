Process status messages
=======================

The camera and tracking process can send diagnostic messages to the main process which are displayed in the status bar.
The available types are:

E - errors

W - warnings

I - information

P - persistent (all the other messages disappear in time)

The format is

{type_prefix}:{message_content}

for example::

    E:Camera settings unavailable

