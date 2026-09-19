#!/bin/bash
sipp -sf loadtest_auth.xml -au loadtest -ap 'LoadTest2026!' 127.0.0.1:5060 -r 10 -l 30 -m 200 -trace_stat -stf resultats_test2_stress.csv
