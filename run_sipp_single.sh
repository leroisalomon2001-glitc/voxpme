#!/bin/bash
sipp -sf loadtest_auth.xml 127.0.0.1:5060 -m 1 -trace_stat -stf resultats_single.csv
