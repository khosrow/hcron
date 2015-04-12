==============
What is hcron?
==============

hcron is a periodic command scheduler along the lines of the ubiquitous cron–but with some really useful differences. hcron will appeal especially to those at large sites and system administrators.

================
What Is Special?
================

There are many alternative cron implementations. However, many of the following features are quite unique to hcron:

* hcron's event format is much easier to work with than the table format of cron
* hcron events are managed individually
* hcron events are labelled and organized hierarchically
* hcron events do not get clobbered during system reinstalls
* hcron is network-oriented rather than host-oriented

=====================
How Is It Being Used?
=====================

At Environment Canada, hcron is in 24/7 operational use, with increasing use:

* early deployment: over 1500 event definitions with more than 36000 events scheduled each day
* 2012-08-18: over 1900 event definitions, and more than 75000 events scheduled each day
* 2014-11-27: over 300 users, over 3000 event definitions, and more than 130000 events scheduled each day

==================
A Quick Comparison
==================

crontab entry:

.. code::

  # hello_dolly
  0 11,21 * 2-12/2 * ssh exechost.abc.xyz 'echo "hello dolly" > /tmp/hello_dolly'; mail -s done Mister.Big@mailhost.abc.xyz

hcron event files (called hello_dolly):

.. code::

  as_user=
  host=exechost.abc.xyz
  command=echo "hello dolly" > /tmp/hello_dolly
  notify_email=Mister.Big@mailhost.abc.xyz
  notify_message=done
  when_month=2-12/2
  when_day=*
  when_hour=11,21
  when_minute=0
  when_dow=2

Using hcron means never needing to check the crontab man page to remember the field order. But there is more to hcron than a key=value approach. See the docs_ for more.

.. _docs: https://expl.info/display/HCRON/Home
