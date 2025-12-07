#!/bin/bash
set -e

# Install ffmpeg
apt-get update
apt-get install -y ffmpeg

# Install python deps
pip install -r requirements.txt
