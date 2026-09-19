#!/bin/bash
sipp -sf loadtest_auth.xml -au loadtest -ap 'LoadTest2026!' 127.0.0.1:5060 -r 2 -l 5 -m 20 -trace_stat -stf resultats_test1.csv
