#!/bin/bash
./waf
./waf --run "scratch/cwnd"
python3 scratch/plot_graphs.py scratch/data.cwnd


