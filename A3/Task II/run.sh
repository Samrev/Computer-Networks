#!/bin/bash
./waf
./waf --run "scratch/cwnd --appRate=$1 --channelRate=$2"
python3 scratch/plot_graphs.py scratch/data.cwnd


