#!/bin/bash
./waf
./waf --run "scratch/cwnd --algorithm=$1"
python3 scratch/plot_graphs.py scratch/data.cwnd


