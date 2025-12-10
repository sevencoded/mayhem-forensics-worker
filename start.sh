#!/bin/bash
chmod +x render-build.sh
chmod +x start.sh
chmod +x supervisord.conf

supervisord -c supervisord.conf
